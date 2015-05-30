# No shebang line, this module is meant to be imported
#
# Copyright 2014 Ambient Entertainment GmbH & Co. KG
# Copyright 2014 Oliver Palmer
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Tasks
-----

This module is responsible for finding and allocating tasks on agents.
"""

from datetime import timedelta, datetime
from logging import DEBUG
from json import dumps
from smtplib import SMTP
from email.mime.text import MIMEText
from time import time, sleep
from os.path import isfile, join
from os import remove, listdir
from errno import ENOENT
from gzip import GzipFile
from uuid import UUID

from sqlalchemy import or_, desc
from sqlalchemy.exc import InvalidRequestError

import requests
from requests.exceptions import ConnectionError, Timeout
# Workaround for https://github.com/kennethreitz/requests/issues/2204
from requests.packages.urllib3.exceptions import ProtocolError

from jinja2 import Template

from lockfile import LockFile, AlreadyLocked

from pyfarm.core.logger import getLogger
from pyfarm.core.enums import (
    AgentState, _AgentState, WorkState, _WorkState, UseAgentAddress)
from pyfarm.models.software import (
    Software, SoftwareVersion, JobSoftwareRequirement,
    JobTypeSoftwareRequirement)
from pyfarm.models.tag import Tag
from pyfarm.models.task import Task
from pyfarm.models.tasklog import TaskLog, TaskTaskLogAssociation
from pyfarm.models.job import Job, JobNotifiedUser
from pyfarm.models.jobqueue import JobQueue
from pyfarm.models.jobtype import JobType, JobTypeVersion
from pyfarm.models.gpu import GPU
from pyfarm.models.agent import Agent, AgentTagAssociation
from pyfarm.models.user import User, Role
from pyfarm.models.jobgroup import JobGroup
from pyfarm.master.application import db
from pyfarm.master.utility import default_json_encoder
from pyfarm.master.config import config

from pyfarm.scheduler.celery_app import celery_app


try:
    range_ = xrange  # pylint: disable=undefined-variable
except NameError:  # pragma: no cover
    range_ = range

logger = getLogger("pf.scheduler.tasks")
# TODO Get logger configuration from pyfarm config
logger.setLevel(DEBUG)

USERAGENT = config.get("master_user_agent")
POLL_BUSY_AGENTS_INTERVAL = timedelta(**config.get("poll_busy_agents_interval"))
POLL_IDLE_AGENTS_INTERVAL = timedelta(**config.get("poll_idle_agents_interval"))
POLL_OFFLINE_AGENTS_INTERVAL = \
    timedelta(**config.get("poll_offline_agents_interval"))
SCHEDULER_LOCKFILE_BASE = config.get("scheduler_lockfile_base")
LOGFILES_DIR = config.get("task_logs_dir")
TRANSACTION_RETRIES = config.get("transaction_retries")
AGENT_REQUEST_TIMEOUT = config.get("agent_request_timeout")
BASE_URL = config.get("base_url")

# Email settings
SMTP_SERVER = config.get("smtp_server")
SMTP_PORT = config.get("smtp_port")
SMTP_USER, SMTP_PASSWORD = config.get("smtp_login")
FROM_ADDRESS = config.get("from_email")
DEFAULT_SUCCESS_SUBJECT = Template(config.get("success_subject"))
DEFAULT_SUCCESS_BODY = Template(config.get("success_body"))
DEFAULT_FAIL_SUBJECT = Template(config.get("failed_subject"))
DEFAULT_FAIL_BODY = Template(config.get("failed_body"))
DEFAULT_DELETE_SUBJECT = config.get("deleted_subject")
DEFAULT_DELETE_BODY = config.get("deleted_body")
OUR_FARM_NAME = config.get("farm_name")

def send_email(to, message):
    """
    Configures and instance of :class:`SMTP` and sends a message to the
    given address.
    """
    smtp = SMTP(SMTP_SERVER, port=SMTP_PORT)

    # Password could be blank in some cases
    if SMTP_USER is not None:
        smtp.login(SMTP_USER, SMTP_PASSWORD)

    try:
        smtp.sendmail(FROM_ADDRESS, to, message)
    finally:
        smtp.quit()


@celery_app.task(ignore_result=True, bind=True)
def send_tasks_to_agent(self, agent_id):
    db.session.rollback()
    agent = Agent.query.filter(Agent.id == agent_id).first()
    if not agent:
        raise KeyError("agent not found")

    logger.debug("Sending assigned batches to agent %s (id %s)", agent.hostname,
                 agent_id)
    if agent.state in ["offline", "disabled"]:
        raise ValueError("agent not available")

    if agent.use_address == UseAgentAddress.PASSIVE:
        logger.debug(
            "Agent's use address mode is PASSIVE, not sending anything")
        return

    tasks_query = Task.query.filter(
        Task.agent == agent, or_(
            Task.state == None,
            ~Task.state.in_(
                [WorkState.DONE, WorkState.FAILED]))).order_by("frame asc")

    tasks_in_jobs = {}
    for task in tasks_query:
        job_tasks = tasks_in_jobs.setdefault(task.job_id, [])
        job_tasks.append(task)

    if not tasks_in_jobs:
        logger.debug("No tasks for agent %s (id %s)", agent.hostname,
                     agent.id)
        return

    for job_id, tasks in tasks_in_jobs.items():
        job = Job.query.filter_by(id=job_id).first()
        message = {"job": {"id": job.id,
                           "title": job.title,
                           "data": job.data if job.data else {},
                           "environ": job.environ if job.environ else {},
                           "by": job.by,
                           "batch": job.batch,
                           "ram": job.ram,
                           "ram_warning": job.ram_warning,
                           "ram_max": job.ram_max,
                           "cpus": job.cpus,
                           "notified_users": [],
                           "priority": job.priority,
                           "notes": job.notes,
                           "tags": []
                           },
                   "jobtype": {"name": job.jobtype_version.jobtype.name,
                               "version": job.jobtype_version.version},
                   "tasks": []}

        if job.user:
            message["job"]["user"] = job.user.username

        for notified_user in job.notified_users:
            message["job"]["notified_users"].append(
                {"username": notified_user.user.username,
                 "on_success": notified_user.on_success,
                 "on_failure": notified_user.on_failure,
                 "on_deletion": notified_user.on_deletion})

        for tag in job.tags:
            message["job"]["tags"].append(tag.tag)

        for task in tasks:
            message["tasks"].append({"id": task.id,
                                     "frame": task.frame,
                                     "attempt": task.attempts})

        logger.info("Sending a batch of %s tasks for job %s (%s) to agent %s",
                    len(tasks), job.title, job.id, agent.hostname)
        try:
            response = requests.post(agent.api_url() + "/assign",
                                     data=dumps(message,
                                                default=default_json_encoder),
                                     headers={
                                         "Content-Type": "application/json",
                                         "User-Agent": USERAGENT},
                                     timeout=AGENT_REQUEST_TIMEOUT)

            logger.debug("Return code after sending batch to agent: %s",
                         response.status_code)
            if response.status_code == requests.codes.service_unavailable:
                if self.request.retries < self.max_retries:
                    logger.warning(
                        "Agent %s, (id %s), answered SERVICE_UNAVAILABLE, "
                        "retrying the request later", agent.hostname, agent.id)
                    self.retry(exc=ValueError("Got return code "
                                              "SERVICE_UNAVAILABLE"))
                else:
                    logger.error(
                        "Agent %s, (id %s), answered SERVICE_UNAVAILABLE, "
                        "marking it as offline", agent.hostname, agent.id)
                    agent.state = AgentState.OFFLINE
                    db.session.add(agent)
                    for task in tasks:
                        task.agent = None
                        task.attempts -= 1
                        db.session.add(task)
                    db.session.commit()
            elif response.status_code == requests.codes.bad_request:
                logger.error("Agent %s, (id %s), answered BAD_REQUEST, "
                             "removing assignment", agent.hostname, agent.id)
                for task in tasks:
                    task.agent = None
                    task.attempts -= 1
                    db.session.add(task)
                db.session.commit()
            elif response.status_code == requests.codes.conflict:
                logger.error("Agent %s, (id %s), answered CONFLICT, removing "
                             "conflicting assignments", agent.hostname,
                             agent.id)
                response_data = response.json()
                if "rejected_task_ids" in response_data:
                    for task_id in response_data["rejected_task_ids"]:
                        task = Task.query.filter_by(id=task_id).first()
                        if task:
                            logger.error("Removing assignment for task %s "
                                         "(Frame %s from job %s) from agent %s "
                                         "(id %s)", task_id, task.frame,
                                         task.job.title, agent.hostname,
                                         agent.id)
                            task.agent = None
                            task.attempts -= 1
                            db.session.add(task)
                    db.session.commit()
                else:
                    logger.error("CONFLICT response from agent %s (id %s) did "
                                 "not contain a list of rejected task ids. "
                                 "Please update the agent to 0.8.4 or higher.",
                                 agent.hostname, agent.id)
            elif response.status_code not in [requests.codes.accepted,
                                              requests.codes.ok,
                                              requests.codes.created]:
                raise ValueError("Unexpected return code on sending batch to "
                                 "agent: %s", response.status_code)
            else:
                for task in tasks:
                    task.sent_to_agent = True
                    db.session.add(task)
                db.session.commit()

        except (ConnectionError, Timeout) as e:
            if self.request.retries < self.max_retries:
                logger.warning("Caught %s trying to contact agent "
                               "%s (id %s), retry %s of %s: %s",
                               type(e).__name__,
                               agent.hostname,
                               agent.id,
                               self.request.retries,
                               self.max_retries,
                               e)
                self.retry(exc=e)
            else:
                logger.error("Could not contact agent %s, (id %s), marking as "
                             "offline", agent.hostname, agent.id)
                agent.state = AgentState.OFFLINE
                db.session.add(agent)
                db.session.commit()
                raise


@celery_app.task(ignore_result=True, bind=True)
def restart_agent(self, agent_id):
    db.session.rollback()
    agent = Agent.query.filter(Agent.id == agent_id).first()
    if not agent:
        raise KeyError("agent not found")

    if agent.state in ["offline", "disabled"]:
        raise ValueError("agent not available")

    if agent.use_address == UseAgentAddress.PASSIVE:
        logger.debug("Agent's use address mode is PASSIVE, cannot restart")
        return

    if not agent.restart_requested:
        logger.error("Agent %s (id %s) is not marked for restart, not "
                     "restarting it", agent.hostname, agent.id)
        raise ValueError("agent not marked for restart")

    logger.info("Restarting agent %s (id %s)", agent.hostname, agent.id)
    try:
        response = requests.post(agent.api_url() + "/restart",
                                    data=dumps({}),
                                    headers={
                                        "User-Agent": USERAGENT},
                                    timeout=AGENT_REQUEST_TIMEOUT)

        logger.debug("Return code after sending restart to agent: %s",
                        response.status_code)
        if response.status_code not in [requests.codes.accepted,
                                        requests.codes.ok]:
            raise ValueError("Unexpected return code on sending restart to "
                             "agent %s: %s", agent.hostname,
                             response.status_code)
        else:
            agent.restart_requested = False
            db.session.add(agent)
            db.session.commit()

    except (ConnectionError, Timeout) as e:
        if self.request.retries < self.max_retries:
            logger.warning("Caught %s trying to restart agent %s (id %s), "
                            "retry %s of %s: %s",
                            type(e).__name__,
                            agent.hostname,
                            agent.id,
                            self.request.retries,
                            self.max_retries,
                            e)
            self.retry(exc=e)
        else:
            logger.error("Could not contact agent %s, (id %s), marking as "
                         "offline", agent.hostname, agent.id)
            agent.state = AgentState.OFFLINE
            db.session.add(agent)
            db.session.commit()
            raise


@celery_app.task(ignore_result=True)
def assign_tasks():
    db.session.rollback()
    idle_agents = Agent.query.filter(or_(Agent.state == AgentState.ONLINE,
                                         Agent.state == AgentState.RUNNING),
                                     ~Agent.tasks.any(
                                        or_(
                                        Task.state == None,
                                        ~Task.state.in_(
                                            [WorkState.DONE,
                                             WorkState.FAILED]))))

    for agent in idle_agents:
        assign_tasks_to_agent.delay(agent.id)


@celery_app.task(ignore_result=True)
def assign_tasks_to_agent(agent_id):
    agent_lockfile_name = SCHEDULER_LOCKFILE_BASE + "-" + str(agent_id)
    agent_lock = LockFile(agent_lockfile_name)

    try:
        agent_lock.acquire(timeout=-1)
        with agent_lock:
            with open(agent_lockfile_name, "w") as lockfile:
                lockfile.write(str(time()))

            db.session.rollback()

            agent = Agent.query.filter_by(id=agent_id).first()
            if not agent:
                raise ValueError("No agent with id %s" % agent_id)
            if agent.state == _AgentState.OFFLINE:
                raise ValueError("Agent %s (id %s) is offline" %
                                 (agent.hostname, agent_id))

            task_count = Task.query.filter(Task.agent == agent,
                                        or_(Task.state == None,
                                            Task.state == WorkState.RUNNING)).\
                                                order_by(Task.job_id,
                                                         Task.frame).\
                                                    count()
            if task_count > 0:
                logger.debug("Agent %s already has %s tasks assigned, not "
                             "assigning any more", agent.hostname, task_count)
                return

            queue = JobQueue()
            job = queue.get_job_for_agent(agent)
            db.session.commit()

            if job:
                job_lockfile_name = SCHEDULER_LOCKFILE_BASE + "-job-" +\
                    str(job.id)
                job_lock = LockFile(job_lockfile_name)
                try:
                    job_lock.acquire(timeout=-1)
                    with job_lock:
                        with open(job_lockfile_name, "w") as lockfile:
                             lockfile.write(str(time()))

                        batch = job.get_batch()
                        for task in batch:
                            task.agent = agent
                            task.sent_to_agent = False
                            task.time_started = None
                            logger.info("Assigned agent %s (id %s) to task %s "
                                        "(frame %s) from job %s (id %s)",
                                        agent.hostname, agent.id, task.id,
                                        task.frame, job.title, job.id)
                            db.session.add(task)

                        if job.state != _WorkState.RUNNING:
                            job.state = WorkState.RUNNING
                            db.session.add(job)
                        job.clear_assigned_counts()
                        db.session.commit()

                        send_tasks_to_agent.delay(agent.id)
                except AlreadyLocked:
                    logger.debug("The lockfile for job %s is locked", job.id)
                    try:
                        with open(job_lockfile_name, "r") as lockfile:
                            locktime = float(lockfile.read())
                            if locktime < time() - 60:
                                logger.error("The old lock on job %s was held "
                                             "for more than 60 seconds. "
                                             "Breaking the lock.", job.id)
                                job_lock.break_lock()
                            assign_tasks_to_agent.apply_async(args=[agent_id],
                                                              countdown=1)
                    except (IOError, OSError, ValueError) as e:
                        logger.warning("Could not read a time value from the "
                                       "lockfile for job %s. Waiting 1 second "
                                       "before trying again. Error: %s",
                                       job.id, e)
                        sleep(1)
                    try:
                        with open(job_lockfile_name, "r") as lockfile:
                            locktime = float(lockfile.read())
                            if locktime < time() - 60:
                                logger.error("The old lock on job %s was held "
                                             "for more than 60 seconds. "
                                             "Breaking the lock.", job.id)
                                agent_lock.break_lock()
                            assign_tasks_to_agent.apply_async(args=[agent_id],
                                                              countdown=1)
                    except(IOError, OSError, ValueError):
                        logger.error("Could not read a time value from the "
                                     "lockfile even after waiting 1s. Breaking "
                                     "the lock.")
                        agent_lock.break_lock()
                        assign_tasks_to_agent.delay(agent_id)
            else:
                logger.debug("Did not find a job for agent %s", agent.hostname)

    except AlreadyLocked:
        logger.debug("The scheduler lockfile is locked, the scheduler seems to "
                     "already be running for agent %s", agent_id)
        try:
            with open(agent_lockfile_name, "r") as lockfile:
                locktime = float(lockfile.read())
                if locktime < time() - 60:
                    logger.error("The old lock was held for more than 60 "
                                 "seconds. Breaking the lock.")
                    agent_lock.break_lock()
        except (IOError, OSError, ValueError) as e:
            # It is possible that we tried to read the file in the narrow window
            # between lock acquisition and actually writing the time
            logger.warning("Could not read a time value from the scheduler "
                           "lockfile. Waiting 1 second before trying again. "
                           "Error: %s", e)
            sleep(1)
        try:
            with open(agent_lockfile_name, "r") as lockfile:
                locktime = float(lockfile.read())
                if locktime < time() - 60:
                    logger.error("The old lock was held for more than 60 "
                                 "seconds. Breaking the lock.")
                    agent_lock.break_lock()
        except(IOError, OSError, ValueError):
            # If we still cannot read a time value from the file after 1s,
            # there was something wrong with the process holding the lock
            logger.error("Could not read a time value from the scheduler "
                         "lockfile even after waiting 1s. Breaking the lock")
            agent_lock.break_lock()


@celery_app.task(ignore_results=True, bind=True)
def poll_agent(self, agent_id):
    db.session.rollback()
    agent = Agent.query.filter(Agent.id == agent_id).first()

    running_tasks_count = Task.query.filter(
        Task.agent == agent,
        or_(Task.state == None,
            Task.state == WorkState.RUNNING)).count()

    if (running_tasks_count > 0 and
        agent.last_heard_from is not None and
        agent.last_heard_from + POLL_BUSY_AGENTS_INTERVAL >
            datetime.utcnow() and
        not agent.state == _AgentState.OFFLINE):
        return
    elif (running_tasks_count == 0 and
          agent.last_heard_from is not None and
          agent.last_heard_from + POLL_IDLE_AGENTS_INTERVAL >
            datetime.utcnow() and
          not agent.state == _AgentState.OFFLINE):
        return

    try:
        logger.info("Polling agent %s", agent.hostname)
        status_response = requests.get(
            agent.api_url() + "/status",
            headers={"User-Agent": USERAGENT},
            timeout=AGENT_REQUEST_TIMEOUT)

        if status_response.status_code != requests.codes.ok:
            raise ValueError(
                "Unexpected return code on checking status of agent "
                "%s (id %s): %s" % (
                    agent.hostname, agent.id, status_response.status_code))
        status_json = status_response.json()

        if UUID(status_json["agent_id"]) != agent_id:
            logger.error("Wrong agent reached under %s. Expected id %s, got %s",
                         agent.api_url(), agent_id, status_json["agent_id"])
            raise ValueError("Wrong agent_id on polling. Expected: %s. Got %s" %
                             (agent_id, status_json["agent_id"]))

        if ("farm_name" in status_json and
            status_json["farm_name"] != OUR_FARM_NAME):
            agent.last_polled = datetime.utcnow()
            db.session.add(agent)
            db.session.commit()
            raise ValueError(
                "Wrong farm_name from agent %s (id %s): %s. (Expected: %s) " %
                    (agent.hostname, agent.id, status_json["farm_name"],
                     OUR_FARM_NAME))

        agent.state = status_json["state"]
        agent.free_ram = status_json["free_ram"]

        tasks_response = requests.get(
            agent.api_url() + "/tasks/",
            headers={"User-Agent": USERAGENT},
            timeout=AGENT_REQUEST_TIMEOUT)

        if tasks_response.status_code != requests.codes.ok:
            raise ValueError(
                "Unexpected return code on checking tasks in agent "
                "%s (id %s): %s" % (
                    agent.hostname, agent.id, tasks_response.status_code))
        tasks_json = tasks_response.json()
    # Catching ProtocolError here is a work around for
    # https://github.com/kennethreitz/requests/issues/2204
    except (ConnectionError, Timeout, ProtocolError) as e:
        if self.request.retries < self.max_retries:
            logger.warning("Caught %s trying to contact agent "
                           "%s (id %s), retry %s of %s: %s",
                           type(e).__name__,
                           agent.hostname,
                           agent.id,
                           self.request.retries,
                           self.max_retries,
                           e)
            agent.last_polled = datetime.utcnow()
            db.session.add(agent)
            db.session.commit()
            self.retry(exc=e)
        else:
            logger.error("Could not contact agent %s, (id %s), marking as "
                         "offline", agent.hostname, agent.id)
            agent.state = AgentState.OFFLINE
            agent.last_polled = datetime.utcnow()
            db.session.add(agent)
            db.session.commit()

    else:
        present_task_ids = [x["id"] for x in tasks_json]
        assigned_task_ids = db.session.query(Task.id).filter(
            Task.agent == agent,
            or_(Task.state == None,
                Task.state == WorkState.RUNNING)).all()
        assigned_task_ids = [x[0] for x in assigned_task_ids]

        if set(assigned_task_ids) - set(present_task_ids):
            logger.debug("Agent %s does not have all the tasks it is supposed "
                         "to have. Registering task pusher", agent.hostname)
            send_tasks_to_agent.delay(agent_id)

        superfluous_tasks = set(present_task_ids) - set(assigned_task_ids)
        if superfluous_tasks:
            for task_id in superfluous_tasks:
                task = Task.query.filter_by(id=task_id).first()
                if task:
                    if task.agent_id != agent_id:
                        logger.warning("Task %s belongs to agent %s (id %s), "
                                       "but has been found running on %s "
                                       "(id %s), stopping it.", task_id,
                                       task.agent.hostname, task.agent_id,
                                       agent.hostname, agent_id)
                        stop_task.delay(task_id, agent_id,
                                        dissociate_agent=False)
                else:
                    logger.warning("Superfluous task %s not found in db",
                                   task_id)

        agent.last_heard_from = datetime.utcnow()
        db.session.add(agent)
        db.session.commit()


@celery_app.task(ignore_results=True)
def poll_agents():
    db.session.rollback()
    idle_agents_to_poll_query = Agent.query.filter(
        Agent.state != AgentState.OFFLINE,
        or_(Agent.last_heard_from == None,
            Agent.last_heard_from +
                POLL_IDLE_AGENTS_INTERVAL < datetime.utcnow()),
        ~Agent.tasks.any(or_(Task.state == None,
                             Task.state == WorkState.RUNNING)),
        Agent.use_address != UseAgentAddress.PASSIVE)

    for agent in idle_agents_to_poll_query:
        logger.debug("Polling idle agent %s", agent.hostname)
        poll_agent.delay(agent.id)

    busy_agents_to_poll_query = Agent.query.filter(
        Agent.state != AgentState.OFFLINE,
        or_(Agent.last_heard_from == None,
            Agent.last_heard_from +
                POLL_BUSY_AGENTS_INTERVAL < datetime.utcnow()),
        Agent.tasks.any(or_(Task.state == None,
                            Task.state == WorkState.RUNNING)),
        Agent.use_address != UseAgentAddress.PASSIVE)

    for agent in busy_agents_to_poll_query:
        logger.debug("Polling busy agent %s", agent.hostname)
        poll_agent.delay(agent.id)

    offline_agents_to_poll_query = Agent.query.filter(
        Agent.state == AgentState.OFFLINE,
        or_(Agent.last_polled == None,
            Agent.last_polled + POLL_OFFLINE_AGENTS_INTERVAL
                < datetime.utcnow()),
        Agent.use_address != UseAgentAddress.PASSIVE)

    for agent in offline_agents_to_poll_query:
        logger.debug("Polling offline agent %s", agent.hostname)
        poll_agent.delay(agent.id)


@celery_app.task(ignore_results=True)
def send_job_completion_mail(job_id, successful=True):
    if not SMTP_SERVER:
        return

    job_lockfile_name = SCHEDULER_LOCKFILE_BASE + "-job-" + str(job_id)
    job_lock = LockFile(job_lockfile_name)

    try:
        job_lock.acquire(timeout=-1)
        with job_lock:
            with open(job_lockfile_name, "w") as lockfile:
                lockfile.write(str(time()))

            db.session.rollback()
            job = Job.query.filter_by(id=job_id).one()
            if job.completion_notify_sent:
                return

            job.url = BASE_URL
            if job.url[-1] != "/":
                job.url += "/"
            job.url+= "jobs/%s" % job.id

            failed_tasks = Task.query.filter(Task.job == job,
                                             Task.state == WorkState.FAILED)
            failed_logs = []
            for task in failed_tasks:
                last_log_assoc = TaskTaskLogAssociation.query.filter_by(
                    task=task).order_by(desc(
                        TaskTaskLogAssociation.attempt)).limit(1).first()
                if last_log_assoc:
                    log = last_log_assoc.log
                    log.url = BASE_URL
                    if log.url[-1] != "/":
                        log.url += "/"
                    log.url += ("api/v1/jobs/%s/tasks/%s/attempts/%s/"
                                "logs/%s/logfile" %
                                (job.id, task.id, last_log_assoc.attempt,
                                 log.identifier))
                    failed_logs.append(log)

            notified_users_query = JobNotifiedUser.query.filter_by(job=job)
            if successful:
                notified_users_query = notified_users_query.filter_by(
                    on_success=True)
            else:
                notified_users_query = notified_users_query.filter_by(
                    on_failure=True)
            notified_users = notified_users_query.all()
            if not notified_users:
                return

            body_template = None
            subject_template = None
            if successful:
                if job.jobtype_version.jobtype.success_body:
                    body_template = Template(
                        job.jobtype_version.jobtype.success_body)
                else:
                    body_template = DEFAULT_SUCCESS_BODY
                if job.jobtype_version.jobtype.success_subject:
                    subject_template = Template(
                        job.jobtype_version.jobtype.success_subject)
                else:
                    subject_template = DEFAULT_SUCCESS_SUBJECT
            else:
                if job.jobtype_version.jobtype.fail_body:
                    body_template = Template(
                        job.jobtype_version.jobtype.fail_body)
                else:
                    body_template = DEFAULT_FAIL_BODY
                if job.jobtype_version.jobtype.fail_subject:
                    subject_template = Template(
                        job.jobtype_version.jobtype.fail_subject)
                else:
                    subject_template = DEFAULT_FAIL_SUBJECT

            message = MIMEText(
                body_template.render(job=job, failed_logs=failed_logs))
            message["Subject"] = subject_template.render(job=job)
            message["From"] = FROM_ADDRESS

            to = [x.user.email for x in notified_users if x.user.email]
            message["To"] = ",".join(to)

            if to:
                send_email(to, message.as_string())
                logger.info("Job completion mail for job %s (id %s) sent to %s",
                            job.title, job.id, to)

            job.completion_notify_sent = True
            db.session.add(job)
            db.session.commit()

    except AlreadyLocked:
        logger.debug("The job lockfile is locked, something is already working "
                     " on job %s", job_id)
        try:
            with open(job_lockfile_name, "r") as lockfile:
                locktime = float(lockfile.read())
                if locktime < time() - 60:
                    logger.error("The old lock was held for more than 60 "
                                 "seconds. Breaking the lock.")
                    job_lock.break_lock()
        except (IOError, OSError, ValueError) as e:
            # It is possible that we tried to read the file in the narrow window
            # between lock acquisition and actually writing the time
            logger.warning("Could not read a time value from the scheduler "
                           "lockfile. Waiting 1 second before trying again. "
                           "Error: %s", e)
            sleep(1)
        try:
            with open(job_lockfile_name, "r") as lockfile:
                locktime = float(lockfile.read())
                if locktime < time() - 60:
                    logger.error("The old lock was held for more than 60 "
                                 "seconds. Breaking the lock.")
                    job_lock.break_lock()
        except(IOError, OSError, ValueError):
            # If we still cannot read a time value from the file after 1s,
            # there was something wrong with the process holding the lock
            logger.error("Could not read a time value from the scheduler "
                         "lockfile even after waiting 1s. Breaking the lock")
            job_lock.break_lock()


@celery_app.task(ignore_results=True)
def send_job_deletion_mail(job_id, jobtype_name, job_title, to):
    logger.debug("In send_job_deletion_mail(), job_id: %s, jobtype_name: %s, "
                 "job_title: %s, to: %s", job_id, jobtype_name, job_title, to)
    message_text = DEFAULT_DELETE_SUBJECT.format(
        job_title=job_title,
        jobtype_name=jobtype_name,
        job_id=job_id
    )

    message = MIMEText(message_text)
    message["Subject"] = DEFAULT_DELETE_SUBJECT.format(job_title=job_title)
    message["From"] = FROM_ADDRESS
    message["To"] = ",".join(to)

    if to:
        send_email(to, message.as_string())
        logger.info("Job deletion mail for job %s (id %s) sent to %s",
                    job_title, job_id, to)


@celery_app.task(ignore_results=True, bind=True)
def update_agent(self, agent_id):
    db.session.rollback()
    agent = Agent.query.filter_by(id=agent_id).one()
    if agent.version == agent.upgrade_to:
        return True

    try:
        response = requests.post(agent.api_url() + "/update",
                                 dumps({"version": agent.upgrade_to}),
                                 headers={"User-Agent": USERAGENT},
                                 timeout=AGENT_REQUEST_TIMEOUT)

        logger.debug("Return code after sending update request for %s "
                     "to agent: %s", agent.upgrade_to, response.status_code)
        if response.status_code not in [requests.codes.accepted,
                                        requests.codes.ok]:
            raise ValueError("Unexpected return code on sending update request "
                             "for %s to agent %s: %s", agent.upgrade_to,
                             agent.hostname, response.status_code)
    except (ConnectionError, Timeout) as e:
        if self.request.retries < self.max_retries:
            logger.warning("Caught %s trying to contact agent "
                            "%s (id %s), retry %s of %s: %s",
                            type(e).__name__,
                            agent.hostname,
                            agent.id,
                            self.request.retries,
                            self.max_retries,
                            e)
            self.retry(exc=e)
        else:
            logger.error("Could not contact agent %s, (id %s), marking as "
                         "offline", agent.hostname, agent.id)
            agent.state = AgentState.OFFLINE
            db.session.add(agent)
            db.session.commit()
            raise

@celery_app.task(ignore_results=True, bind=True)
def delete_task(self, task_id):
    db.session.rollback()

    job_id = None
    task = None
    agent = None
    job = None
    job_group = None

    retries = TRANSACTION_RETRIES
    deleted = False
    while not deleted and retries > 0:
        try:
            task = Task.query.filter_by(id=task_id).one()
            job = task.job
            job_id = task.job_id
            agent = task.agent
            job_group = job.group

            logger.info("Deleting task %s (job %s - \"%s\")",task.id, job.id,
                        job.title)
            db.session.delete(task)
            db.session.commit()
            deleted = True
        except InvalidRequestError:
            if retries > 0:
                logger.debug("Caught an InvalidRequestError trying to delete "
                             "task %s, retrying transaction", task_id)
                retries -= 1
                db.session.rollback()
            else:
                logger.error("While trying to delete task %s, caught an "
                             "InvalidRequestError %s times, giving up",
                             task_id, TRANSACTION_RETRIES)
                raise

    job.update_state()
    db.session.commit()

    retries = TRANSACTION_RETRIES
    done = False
    job_deleted = False
    while not done and retries > 0:
        try:
            job = Job.query.filter_by(id=job_id).one()
            if job.to_be_deleted:
                num_remaining_tasks = Task.query.filter_by(job=job).count()
                if num_remaining_tasks == 0:
                    logger.info("Job %s (%s) is marked for deletion and has no "
                                "tasks left, deleting it from the database now.",
                                job.id, job.title)
                    notified_users = JobNotifiedUser.query.filter(
                        JobNotifiedUser.job == job,
                        JobNotifiedUser.on_deletion == True).all()
                    to = [x.user.email for x in notified_users if
                          x.user.email]
                    send_job_deletion_mail.delay(
                        job.id, job.jobtype_version.jobtype.name,
                        job.title, to)
                    db.session.delete(job)
                    job_deleted = True
                db.session.commit()
            done = True

        except InvalidRequestError:
            if retries > 0:
                logger.debug("Caught an InvalidRequestError trying to delete "
                             "job %s, retrying transaction", job_id)
                retries -= 1
                db.session.rollback()
            else:
                logger.error("While trying to delete job %s, caught an "
                             "InvalidRequestError %s times, giving up",
                             job_id, TRANSACTION_RETRIES)
                raise

    if job_deleted and job_group:
        if job_group.jobs.count() == 0:
            logger.info("Job group %s (id %s) has no jobs left, deleting",
                        job_group.name, job_group.id)
            db.session.delete(job_group)
            db.session.commit()

    if (agent is not None and
        task.state not in [WorkState.DONE, WorkState.FAILED]):
        try:
            response = requests.delete("%s/tasks/%s" %
                                            (agent.api_url(), task.id),
                                       headers={"User-Agent": USERAGENT},
                                       timeout=AGENT_REQUEST_TIMEOUT)

            logger.info("Deleting task %s (job %s - %r) from agent %s (id %s)",
                        task.id, job.id, job.title, agent.hostname, agent.id)
            if response.status_code not in [requests.codes.accepted,
                                            requests.codes.ok,
                                            requests.codes.no_content,
                                            requests.codes.not_found]:
                raise ValueError("Unexpected return code on deleting task %s on "
                                 "agent %s: %s",
                                 task.id, agent.id, response.status_code)
        # Catching ProtocolError here is a work around for
        # https://github.com/kennethreitz/requests/issues/2204
        except (ConnectionError, ProtocolError, Timeout) as e:
            if self.request.retries < self.max_retries:
                logger.warning("Caught %s while trying to delete task %s "
                               "from agent %s (id %s): %s",
                               type(e).__name__,
                               task.id,
                               agent.hostname,
                               agent.id,
                               e)


@celery_app.task(ignore_results=True, bind=True)
def stop_task(self, task_id, agent_id=None, dissociate_agent=True):
    db.session.rollback()
    task = Task.query.filter_by(id=task_id).one()
    job = task.job

    if ((task.agent is not None and
         task.state not in [WorkState.DONE, WorkState.FAILED]) or
        agent_id is not None):
        if agent_id is not None:
            agent = Agent.query.filter_by(id=agent_id).one()
        else:
            agent = task.agent
        try:
            response = requests.delete("%s/tasks/%s" %
                                            (agent.api_url(), task.id),
                                       headers={"User-Agent": USERAGENT},
                                       timeout=AGENT_REQUEST_TIMEOUT)

            logger.info("Stopping task %s (job %s - \"%s\") on agent %s (id %s)",
                        task.id, job.id, job.title, agent.hostname, agent.id)
            if response.status_code not in [requests.codes.accepted,
                                            requests.codes.ok,
                                            requests.codes.no_content,
                                            requests.codes.not_found]:
                raise ValueError("Unexpected return code on stopping task %s on "
                                 "agent %s: %s",
                                 task.id, agent.id, response.status_code)
            elif dissociate_agent:
                task.agent = None
                task.state = None
                db.session.add(task)
        # Catching ProtocolError here is a work around for
        # https://github.com/kennethreitz/requests/issues/2204
        except (ConnectionError, ProtocolError, Timeout) as e:
            if self.request.retries < self.max_retries:
                logger.warning("Caught %s while trying to delete task %s "
                               "from agent %s (id %s), retry %s of %s: %s",
                               type(e).__name__,
                               task.id,
                               agent.hostname,
                               agent.id,
                               self.request.retries,
                               self.max_retries,
                               e)
                self.retry(exc=e)

    db.session.commit()


@celery_app.task(ignore_results=True)
def delete_to_be_deleted_jobs():
    db.session.rollback()

    jobs_to_delete_query = Job.query.filter(Job.to_be_deleted == True)

    job_ids_to_delete = []
    for job in jobs_to_delete_query:
        delete_job.delay(job.id)

    db.session.commit()


@celery_app.task(ignore_results=True)
def delete_job(job_id):
    db.session.rollback()
    job = Job.query.filter_by(id=job_id).one()
    if not job.to_be_deleted:
        logger.warning("Not deleting job %s, it is not marked for deletion.",
                       job.id)
        return

    job_group = job.group

    tasks_query = Task.query.filter_by(job=job)
    async_deletes = 0
    for task in tasks_query:
        if task.agent and task.state not in [_WorkState.DONE, _WorkState.FAILED]:
            delete_task.delay(task.id)
            async_deletes += 1
        else:
            db.session.delete(task)

    if async_deletes == 0:
        logger.info("Job %s (%s) is marked for deletion and has no tasks "
                    "that require asynchronous deletion. Deleting it now.",
                    job.id, job.title)
        # Notify users about deletion
        notified_users = JobNotifiedUser.query.filter(
            JobNotifiedUser.job == job,
            JobNotifiedUser.on_deletion == True).all()
        to = [x.user.email for x in notified_users if x.user.email]
        send_job_deletion_mail.delay(job.id, job.jobtype_version.jobtype.name,
                                     job.title, to)
        db.session.delete(job)

    db.session.commit()

    if async_deletes == 0 and job_group:
        if job_group.jobs.count() == 0:
            logger.info("Job group %s (id %s) has no jobs left, deleting",
                        job_group.name, job_group.id)
            db.session.delete(job_group)
            db.session.commit()

@celery_app.task(ignore_results=True)
def clean_up_orphaned_task_logs():
    db.session.rollback()

    orphaned_task_logs = TaskLog.query.filter(
        ~TaskLog.task_associations.any()).all()
    for log in orphaned_task_logs:
        logger.info("Removing orphaned task log %s" % log.identifier)
        db.session.delete(log)
    db.session.commit()

    try:
        tasklog_files = [f for f in listdir(LOGFILES_DIR)\
                         if isfile(join(LOGFILES_DIR, f))]

        for filepath in tasklog_files:
            uncompressed_name = filepath
            if filepath.endswith(".gz"):
                uncompressed_name = filepath[0:-3]
            referencing_count = TaskLog.query.filter(
                or_(TaskLog.identifier == filepath,
                    TaskLog.identifier == uncompressed_name)).count()
            if not referencing_count:
                logger.info("Deleting log file %s", join(LOGFILES_DIR, filepath))
                try:
                    remove(join(LOGFILES_DIR, filepath))
                except OSError as e:
                    if e.errno != ENOENT:
                        raise
    except OSError as e:
        if e.errno != ENOENT:
            raise
        logger.warning("Log directory %r does not exist", LOGFILES_DIR)


@celery_app.task(ignore_results=True)
def autodelete_old_jobs():
    db.session.rollback()

    finished_jobs_query = Job.query.filter(
        Job.state != None,
        Job.state == WorkState.DONE,
        Job.time_finished != None,
        Job.autodelete_time != None)

    job_ids_to_delete = []
    for job in finished_jobs_query:
        # I haven't figured out yet how to do this test as part of the filter
        if (job.time_finished + timedelta(seconds=job.autodelete_time) <
            datetime.utcnow()):
            logger.info("Deleting job %s (id %s). It was finished on %s UTC, "
                        "which is more than %s ago", job.title, job.id,
                        job.time_finished,
                        timedelta(seconds=job.autodelete_time))
            job.to_be_deleted = True
            db.session.add(job)
            job_ids_to_delete.append(job.id)

    db.session.commit()

    for job_id in job_ids_to_delete:
        delete_job.delay(job_id)


@celery_app.task(ignore_results=True)
def compress_task_logs():
    db.session.rollback()

    try:
        uncompressed_tasklogs = [f for f in listdir(LOGFILES_DIR)\
                                 if (isfile(join(LOGFILES_DIR, f)) and
                                     not f.endswith(".gz"))]

        for tasklog in uncompressed_tasklogs:
            compress_task_log.delay(tasklog)
    except OSError as e:
        if e.errno != ENOENT:
            raise
        logger.warning("Log directory %r does not exist", LOGFILES_DIR)


@celery_app.task(ignore_results=True)
def compress_task_log(tasklog_name):
    db.session.rollback()

    try:
        path = join(LOGFILES_DIR, tasklog_name)
        with open(path, "rb") as logfile:
            logger.debug("Compressing tasklog file %s", path)
            compressed_logfile = GzipFile("%s.gz" % path, "wb")
            compressed_logfile.write(logfile.read())
        try:
            remove(join(LOGFILES_DIR, path))
        except OSError as e:
            if e.errno != ENOENT:
                raise
    except IOError as e:
        logger.error("Could not compress tasklog file %s: %s: %s",
                     tasklog_name, type(e).__name__, e)
        raise


@celery_app.task(ignore_results=True)
def cache_jobqueue_path(jobqueue_id):
    db.session.rollback()

    jobqueue = JobQueue.query.filter_by(id=jobqueue_id).one()
    jobqueue.fullpath = jobqueue.path()

    db.session.add(jobqueue)
    db.session.commit()
