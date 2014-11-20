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
from sys import maxsize

from sqlalchemy import or_, and_, func, distinct, desc, asc

import requests
from requests.exceptions import ConnectionError, RequestException
# Workaround for https://github.com/kennethreitz/requests/issues/2204
from requests.packages.urllib3.exceptions import ProtocolError

from lockfile import LockFile, AlreadyLocked

from pyfarm.core.logger import getLogger
from pyfarm.core.enums import AgentState, WorkState, _WorkState, UseAgentAddress
from pyfarm.core.config import read_env, read_env_int
from pyfarm.models.project import Project
from pyfarm.models.software import (
    Software, SoftwareVersion, JobSoftwareRequirement,
    JobTypeSoftwareRequirement)
from pyfarm.models.tag import Tag
from pyfarm.models.task import Task, TaskDependencies
from pyfarm.models.job import Job, JobDependencies
from pyfarm.models.jobqueue import JobQueue
from pyfarm.models.jobtype import JobType, JobTypeVersion
from pyfarm.models.agent import Agent, AgentTagAssociation
from pyfarm.models.user import User, Role
from pyfarm.master.application import db
from pyfarm.master.utility import default_json_encoder

from pyfarm.scheduler.celery_app import celery_app


try:
    range_ = xrange  # pylint: disable=undefined-variable
except NameError:  # pragma: no cover
    range_ = range

logger = getLogger("pf.scheduler.tasks")
# TODO Get logger configuration from pyfarm config
logger.setLevel(DEBUG)

USERAGENT = "PyFarm/1.0 (master)"
POLL_BUSY_AGENTS_INTERVAL = read_env_int(
    "PYFARM_POLL_BUSY_AGENTS_INTERVAL", 600)
POLL_IDLE_AGENTS_INTERVAL = read_env_int(
    "PYFARM_POLL_IDLE_AGENTS_INTERVAL", 3600)
SCHEDULER_LOCKFILE = read_env(
    "PYFARM_SCHEDULER_LOCKFILE", "/tmp/pyfarm_scheduler_lock")


@celery_app.task(ignore_result=True, bind=True)
def send_tasks_to_agent(self, agent_id):
    db.session.commit()
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
                           "by": job.by},
                   "jobtype": {"name": job.jobtype_version.jobtype.name,
                               "version": job.jobtype_version.version},
                   "tasks": []}

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
                                         "User-Agent": USERAGENT})

            logger.debug("Return code after sending batch to agent: %s",
                         response.status_code)
            if response.status_code == requests.codes.service_unavailable:
                logger.error("Agent %s, (id %s), answered SERVICE_UNAVAILABLE, "
                             "marking it as offline", agent.hostname, agent.id)
                agent.state = AgentState.OFFLINE
                db.session.add(agent)
                for task in tasks:
                    task.agent = None
                    task.attempts -= 1
                    db.session.add(task)
                db.session.commit()
            elif response.status_code not in [requests.codes.accepted,
                                              requests.codes.ok,
                                              requests.codes.created]:
                raise ValueError("Unexpected return code on sending batch to "
                                 "agent: %s", response.status_code)

        except ConnectionError as e:
            if self.request.retries < self.max_retries:
                logger.warning("Caught ConnectionError trying to contact agent "
                               "%s (id %s), retry %s of %s: %s",
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


def satisfies_requirements(agent, job):
    if job.ram > agent.ram or job.cpus > agent.cpus:
        return False

    requirements_to_satisfy = (list(job.software_requirements) +
                               list(job.jobtype_version.software_requirements))

    satisfied_requirements = []
    for software_version in agent.software_versions:
        for requirement in requirements_to_satisfy:
            if (software_version.software == requirement.software and
                (requirement.min_version == None or
                 requirement.min_version.rank <= software_version.rank) and
                (requirement.max_version == None or
                 requirement.max_version.rank >= software_version.rank)):
                satisfied_requirements.append(requirement)

    return len(requirements_to_satisfy) <= len(satisfied_requirements)

def satisfies_jobtype_requirements(agent, jobtype_version):
    requirements_to_satisfy = set(jobtype_version.software_requirements)

    satisfied_requirements = []
    for software_version in agent.software_versions:
        for requirement in requirements_to_satisfy:
            if (software_version.software == requirement.software and
                (requirement.min_version == None or
                 requirement.min_version.rank <= software_version.rank) and
                (requirement.max_version == None or
                 requirement.max_version.rank >= software_version.rank)):
                satisfied_requirements.append(requirement)

    return len(requirements_to_satisfy) <= len(satisfied_requirements)

def read_queue_tree(queue):
    # Agents already assigned to this queue before the weight scheduler runs
    queue.preassigned_agents = 0
    queue.can_use_more_agents = True
    queue.total_assigned_agents = 0

    child_queues_query = JobQueue.query.filter_by(parent_jobqueue_id=queue.id)

    queue.branches = []
    for child_queue in child_queues_query:
        child_queue = read_queue_tree(child_queue)
        queue.total_assigned_agents += child_queue.total_assigned_agents
        queue.branches.append(child_queue)

    agent_count_query = db.session.query(
        Task.job_id, func.count(distinct(Task.agent_id)).label('num_agents')).\
            filter(or_(Task.state == None, Task.state == WorkState.RUNNING)).\
                group_by(Task.job_id).subquery()

    child_jobs_query = db.session.query(Job,
                                        func.coalesce(
                                            agent_count_query.c.num_agents,
                                            0).label('num_agents')).\
        outerjoin(agent_count_query, Job.id == agent_count_query.c.job_id).\
        filter(Job.job_queue_id == queue.id,
               Job.state == WorkState.RUNNING,
               Job.to_be_deleted == False)

    for tuple in child_jobs_query:
        num_assigned_agents = tuple[1]
        job = tuple[0]
        job.total_assigned_agents = num_assigned_agents
        job.can_use_more_agents = True
        queue.total_assigned_agents += num_assigned_agents
        queue.branches.append(job)

    return queue


def assign_agents_to_job(job, max_agents, available_agents):
    assigned_agents = set()
    for parent in job.parents:
        if parent.state != _WorkState.DONE:
            return assigned_agents

    agents_needed = True
    while max_agents > 0 and agents_needed and available_agents:
        selected_agent = None
        for agent in available_agents:
            if satisfies_requirements(agent, job):
                prev = Task.query.filter(Task.job == job,
                                         Task.agent == agent,
                                         Task.state == WorkState.DONE).count()
                # If this agent has successfully worked on this job in the past
                if prev > 0:
                    selected_agent = agent
                    break
                # Otherwise, take this agent if we don't already have one, but
                # keep looking
                else:
                    if not selected_agent:
                        selected_agent = agent


        if not selected_agent:
            agents_needed = False
        else:
            tasks_query = Task.query.filter(
                Task.job == job,
                or_(Task.state == None,
                    ~Task.state.in_([WorkState.DONE,
                                     WorkState.FAILED])),
                or_(Task.agent == None,
                    Task.agent.has(Agent.state.in_(
                        [AgentState.OFFLINE,
                         AgentState.DISABLED])))).order_by("frame asc")
            batch = []
            for task in tasks_query:
                if (len(batch) < job.batch and
                    len(batch) < (job.jobtype_version.max_batch or maxsize) and
                    (not job.jobtype_version.batch_contiguous or
                     (len(batch) == 0 or
                      batch[-1].frame + job.by == task.frame))):
                    batch.append(task)

            if not batch:
                agents_needed = False
            else:
                for task in batch:
                    task.agent = selected_agent
                    db.session.add(task)
                    logger.info("Assigned agent %s (id %s) to task %s "
                        "(frame %s) from job %s (id %s)",
                        selected_agent.hostname,
                        selected_agent.id,
                        task.id,
                        task.frame,
                        job.title,
                        job.id)
                assigned_agents.add(selected_agent)
                available_agents.remove(selected_agent)
                db.session.add(selected_agent)
                if job.state != _WorkState.RUNNING:
                    job.state = WorkState.RUNNING
                    db.session.add(job)
                # This is necessary because otherwise, the next query will still
                # see the tasks as unassigned.
                db.session.flush()
                max_agents -= 1
                job.total_assigned_agents += 1

    if not assigned_agents:
        job.can_use_more_agents = False

    return assigned_agents

def assign_agents_by_weight(objects, max_agents,
                            suitable_agents_by_jobtype_version):
    logger.debug("Assigning agents by weight between %s objects" % len(objects))
    max_weight = 1
    min_weight = 1
    objects_at_weights = {}
    for i in objects:
        i.preassigned_agents = i.total_assigned_agents
        max_weight = max(max_weight, i.weight)
        min_weight = min(min_weight, i.weight)
        if i.weight in objects_at_weights:
            objects_at_weights[i.weight] += [i]
        else:
            objects_at_weights[i.weight] = [i]

    assigned_agents = set()
    agents_needed = True
    while max_agents > 0 and agents_needed:
        assigned_this_round = 0
        for floor in range_(max_weight, min_weight-1, -1):
            for current_weight in range_(max_weight, floor-1, -1):
                if current_weight in objects_at_weights:
                    for i in objects_at_weights[current_weight]:
                        if max_agents > 0 and i.can_use_more_agents:
                            assigned = set()
                            if i.preassigned_agents > 0:
                                i.preassigned_agents -= 1
                                assigned_this_round += 1
                            elif (isinstance(i, Job) and
                                  (not i.maximum_agents or
                                       i.maximum_agents >
                                           i.total_assigned_agents)):
                                assigned = assign_agents_to_job(
                                    i, 1,
                                    suitable_agents_by_jobtype_version[
                                        i.jobtype_version_id])
                            elif (not i.maximum_agents or
                                      i.maximum_agents >
                                          i.total_assigned_agents):
                                assigned = assign_agents_to_queue(
                                    i, 1, suitable_agents_by_jobtype_version)
                            assigned_this_round += len(assigned)
                            max_agents -= len(assigned)
                            assigned_agents.update(assigned)
                            i.total_assigned_agents += len(assigned)
        if assigned_this_round == 0:
            agents_needed = False

    return assigned_agents


# TODO Make this a method of JobQueue and Job called assign_agents
def assign_agents_to_queue(queue, max_agents,
                           suitable_agents_by_jobtype_version):
    """
    Distribute up to max_agents among the jobs and subqueues of queue.
    Returns the list of agents that have been assigned new tasks.
    """
    assigned_agents = set()

    # Before anything else, make sure minima are satisfied
    minima_satisfied = False
    while max_agents > 0 and not minima_satisfied:
        unsatisfied_minima = 0
        for branch in queue.branches:
            if (branch.minimum_agents and
                branch.minimum_agents > branch.total_assigned_agents and
                branch.can_use_more_agents):
                if isinstance(branch, Job):
                    assigned = assign_agents_to_job(
                        branch, 1,
                        suitable_agents_by_jobtype_version[
                            branch.jobtype_version_id])
                else:
                    assigned = assign_agents_to_queue(
                        branch, 1, suitable_agents_by_jobtype_version)
                max_agents -= len(assigned)
                assigned_agents.update(assigned)
                queue.total_assigned_agents += len(assigned)
                if (branch.minimum_agents > branch.total_assigned_agents and
                    branch.can_use_more_agents):
                    unsatisfied_minima += 1
        minima_satisfied = unsatisfied_minima == 0

    # Early return if we have used up the available agents at this point
    if max_agents <= 0:
        return assigned_agents

    objects_by_priority = {}
    for branch in queue.branches:
        if branch.priority not in objects_by_priority:
            objects_by_priority[branch.priority] = [branch]
        else:
            objects_by_priority[branch.priority] += [branch]
    available_priorities = sorted(objects_by_priority.keys(), reverse=True)

    for priority in available_priorities:
        objects = objects_by_priority[priority]
        agents_needed = True
        while max_agents > 0 and agents_needed:
            # Not started jobs don't get anything as long running ones or
            # subqueues still need agents
            running_jobs = [x for x in objects if isinstance(x, Job) and
                            x.state == WorkState.RUNNING]
            subqueues = [x for x in objects if isinstance(x, JobQueue) and
                         x.can_use_more_agents]
            assigned = assign_agents_by_weight(
                running_jobs + subqueues, max_agents,
                suitable_agents_by_jobtype_version)
            max_agents -= len(assigned)
            assigned_agents.update(assigned)
            assigned_this_round = assigned
            queue.total_assigned_agents += len(assigned)



            if not assigned_this_round:
                agents_needed = False

    if not assigned_agents:
        # Running jobs and subqueues in this queue did not use up all
        # available agents, start a queued job
        if max_agents > 0:
            logger.debug("Ran out of running jobs for queue %s, trying to "
                "start one", queue.path())
            queued_jobs_query = Job.query.filter(
                Job.state == None,
                ~Job.parents.any(or_(Job.state == None,
                                        and_(Job.state != None,
                                            Job.state != WorkState.DONE))))
            if queue.id:
                queued_jobs_query = queued_jobs_query.filter(
                    Job.queue == queue)
            else:
                queued_jobs_query = queued_jobs_query.filter(
                    Job.queue == None)
            queud_jobs_query = queued_jobs_query.order_by(
                                                    asc(Job.time_submitted))
            jobs_started = 0
            queued_jobs_iterator = iter(queued_jobs_query)
            logger.debug("Looking for a job to start")
            try:
                while jobs_started == 0:
                    job = next(queued_jobs_iterator)
                    job.total_assigned_agents = 0
                    job.can_use_more_agents = True
                    assigned = assign_agents_to_job(
                        job, 1,
                        suitable_agents_by_jobtype_version[
                            job.jobtype_version_id])
                    max_agents -= len(assigned)
                    assigned_agents.update(assigned)
                    assigned_this_round.update(assigned)
                    queue.total_assigned_agents += len(assigned)
                    if assigned:
                        queue.branches.append(job)
                        jobs_started += 1
            except StopIteration:
                pass
            logger.debug("Finished looking for a job to start")

    if not assigned_agents:
        queue.can_use_more_agents = False

    return assigned_agents


@celery_app.task(ignore_result=True)
def assign_tasks():
    """
    Descends the tree of job queues recursively to assign agents to the jobs
    registered with those queues
    """
    lock = LockFile(SCHEDULER_LOCKFILE)
    try:
        lock.acquire(timeout=-1)
        with lock:
            with open(SCHEDULER_LOCKFILE, "w") as file:
                file.write(str(time()))

            db.session.commit()
            logger.info("Assigning tasks to agents")
            idle_agents = Agent.query.filter(Agent.state == AgentState.ONLINE,
                                            ~Agent.tasks.any(
                                                or_(
                                                Task.state == None,
                                                ~Task.state.in_(
                                                    [WorkState.DONE,
                                                    WorkState.FAILED])))).all()
            if not idle_agents:
                logger.info("No idle agents, not assigning anything")
                return

            jobtype_versions_query = JobTypeVersion.query.filter(
                JobTypeVersion.jobs.any(or_(
                    Job.state == None, )))
            suitable_agents_by_jobtype_version = {}
            for jobtype_version in jobtype_versions_query:
                suitable_agents = []
                for agent in idle_agents:
                    if satisfies_jobtype_requirements(agent, jobtype_version):
                        suitable_agents.append(agent)
                suitable_agents_by_jobtype_version[jobtype_version.id] =\
                    suitable_agents

            tree_root = read_queue_tree(JobQueue())
            agents_with_new_tasks = assign_agents_to_queue(
                tree_root,
                len(idle_agents),
                suitable_agents_by_jobtype_version)

            for agent in agents_with_new_tasks:
                db.session.add(agent)
            db.session.commit()

            logger.debug("Finished assigning tasks to agents")

            for agent in agents_with_new_tasks:
                logger.debug("Registering asynchronous task pusher for agent %s",
                            agent.id)
                send_tasks_to_agent.delay(agent.id)

    except AlreadyLocked:
        logger.debug("The scheduler lockfile is locked, the scheduler seems to "
                     "already be running")
        try:
            with open(SCHEDULER_LOCKFILE, "r") as file:
                locktime = float(file.read())
                if locktime < time() - 60:
                    logger.error("The old lock was held for more than 60 "
                                 "seconds. Breaking the lock.")
                    lock.break_lock()
        except (IOError, ValueError) as e:
            # It is possible that we tried to read the file in the narrow window
            # between lock acquisition and actually writing the time
            logger.warning("Could not read a time value from the scheduler "
                           "lockfile. Waiting 60 seconds before trying again. "
                           "Error: %s", e)
            sleep(1)
            try:
                with open(SCHEDULER_LOCKFILE, "r") as file:
                    locktime = float(file.read())
                    if locktime < time() - 60:
                         logger.error("The old lock was held for more than 60 "
                                      "seconds. Breaking the lock.")
                         lock.break_lock()
            except(IOError, ValueError):
                # If we still cannot read a time value from the file after 1s,
                # there was something wrong with the process holding the lock
                logger.error("Could not read a time value from the scheduler "
                             "lockfile even after waiting 1s. Breaking the lock")
                lock.break_lock()


@celery_app.task(ignore_results=True, bind=True)
def poll_agent(self, agent_id):
    db.session.commit()
    agent = Agent.query.filter(Agent.id == agent_id).first()

    running_tasks_count = Task.query.filter(
        Task.agent == agent,
        or_(Task.state == None,
            Task.state == WorkState.RUNNING)).count()

    if (running_tasks_count > 0 and
        agent.last_heard_from is not None and
        agent.last_heard_from + timedelta(seconds=POLL_BUSY_AGENTS_INTERVAL) >
            datetime.utcnow()):
        return
    elif (running_tasks_count == 0 and
          agent.last_heard_from is not None and
          agent.last_heard_from + timedelta(seconds=POLL_IDLE_AGENTS_INTERVAL) >
            datetime.utcnow()):
        return

    try:
        response = requests.get(
            agent.api_url() + "/tasks/",
            headers={"User-Agent": USERAGENT})

        if response.status_code != requests.codes.ok:
            raise ValueError(
                "Unexpected return code on checking tasks in agent "
                "%s (id %s): %s" % (
                    agent.hostname, agent.id, response.status_code))
        json_data = response.json()
    # Catching ProtocolError here is a work around for
    # https://github.com/kennethreitz/requests/issues/2204
    except (ConnectionError, ProtocolError) as e:
        if self.request.retries < self.max_retries:
            logger.warning("Caught ConnectionError trying to contact agent "
                           "%s (id %s), retry %s of %s: %s",
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

    else:
        present_task_ids = [x["id"] for x in json_data]
        assigned_task_ids = db.session.query(Task.id).filter(
            Task.agent == agent,
            or_(Task.state == None,
                Task.state == WorkState.RUNNING))

        if set(present_task_ids) - set(assigned_task_ids):
            send_tasks_to_agent.delay(agent_id)

        agent.last_heard_from = datetime.utcnow()
        db.session.add(agent)
        db.session.commit()


@celery_app.task(ignore_results=True)
def poll_agents():
    db.session.commit()
    idle_agents_to_poll_query = Agent.query.filter(
        or_(Agent.last_heard_from == None,
            Agent.last_heard_from +
                timedelta(
                    seconds=POLL_IDLE_AGENTS_INTERVAL) < datetime.utcnow()),
        ~Agent.tasks.any(or_(Task.state == None,
                             Task.state == WorkState.RUNNING)),
        Agent.use_address != UseAgentAddress.PASSIVE)

    for agent in idle_agents_to_poll_query:
        poll_agent.delay(agent.id)

    busy_agents_to_poll_query = Agent.query.filter(
        or_(Agent.last_heard_from == None,
            Agent.last_heard_from +
                timedelta(
                    seconds=POLL_BUSY_AGENTS_INTERVAL) < datetime.utcnow()),
        Agent.tasks.any(or_(Task.state == None,
                            Task.state == WorkState.RUNNING)),
        Agent.use_address != UseAgentAddress.PASSIVE)

    for agent in busy_agents_to_poll_query:
        poll_agent.delay(agent.id)


@celery_app.task(ignore_results=True)
def send_job_completion_mail(job_id, successful=True):
    db.session.commit()
    job = Job.query.filter_by(id=job_id).one()
    message = MIMEText("Job %s (id %s) has completed %s on %s.\n\n"
                       "Sincerely,\n\tThe PyFarm render manager" %
                            (job.title,
                             job_id,
                             "successfully" if successful else "unsuccessfully",
                             job.time_finished))

    message["Subject"] = ("Job %s completed %ssuccessfully" %
                            (job.title, "" if successful else "un"))
    message["From"] = read_env("PYFARM_FROM_ADDRESS", "pyfarm@localhost")

    to = [x.email for x in job.notified_users if x.email]

    if to:
        smtp = SMTP(read_env("PYFARM_MAIL_SERVER", "localhost"))
        smtp.sendmail(read_env("PYFARM_FROM_ADDRESS",
                               "pyfarm@localhost"), to, message.as_string())
        smtp.quit()

        logger.info("Job completion mail for job %s (id %s) sent to %s",
                    job.title, job.id, to)

@celery_app.task(ignore_results=True, bind=True)
def update_agent(self, agent_id):
    db.session.commit()
    agent = Agent.query.filter_by(id=agent_id).one()
    if agent.version == agent.upgrade_to:
        return True

    try:
        response = requests.post(agent.api_url() + "/update",
                                 dumps({"version": agent.upgrade_to}),
                                 headers={"User-Agent": USERAGENT})

        logger.debug("Return code after sending update request for %s "
                     "to agent: %s", agent.upgrade_to, response.status_code)
        if response.status_code not in [requests.codes.accepted,
                                        requests.codes.ok]:
            raise ValueError("Unexpected return code on sending update request "
                             "for %s to agent %s: %s", agent.upgrade_to,
                             agent.hostname, response.status_code)
    except ConnectionError as e:
        if self.request.retries < self.max_retries:
            logger.warning("Caught ConnectionError trying to contact agent "
                            "%s (id %s), retry %s of %s: %s",
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
    db.session.commit()
    task = Task.query.filter_by(id=task_id).one()
    job = task.job

    if task.agent is None or task.state in [WorkState.DONE, WorkState.FAILED]:
        logger.info("Deleting task %s (job %s - \"%s\")",
                    task.id, job.id, job.title)
        db.session.delete(task)
        db.session.flush()
    else:
        agent = task.agent
        try:
            response = requests.delete("%s/tasks/%s" %
                                            (agent.api_url(), task.id),
                                       headers={"User-Agent": USERAGENT})

            logger.info("Deleting task %s (job %s - \"%s\") from agent %s (id %s)",
                        task.id, job.id, job.title, agent.hostname, agent.id)
            if response.status_code not in [requests.codes.accepted,
                                            requests.codes.ok,
                                            requests.codes.no_content,
                                            requests.codes.not_found]:
                raise ValueError("Unexpected return code on deleting task %s on "
                                 "agent %s: %s",
                                 task.id, agent.id, response.status_code)
            else:
                db.session.delete(task)
                db.session.flush()
        # Catching ProtocolError here is a work around for
        # https://github.com/kennethreitz/requests/issues/2204
        except (ConnectionError, ProtocolError) as e:
            if self.request.retries < self.max_retries:
                logger.warning("Caught ConnectionError trying to delete task %s "
                               "from agent %s (id %s), retry %s of %s: %s",
                               task.id,
                               agent.hostname,
                               agent.id,
                               self.request.retries,
                               self.max_retries,
                               e)
                self.retry(exc=e)
            else:
                logger.error("Could not contact agent %s, (id %s), for stopping "
                             "task %s, just deleting it locally",
                             agent.hostname, agent.id, task.id)
                db.session.delete(task)
                db.session.flush()

    if job.to_be_deleted:
        num_remaining_tasks = Task.query.filter_by(job=job).count()
        if num_remaining_tasks == 0:
            logger.info("Job %s (%s) is marked for deletion and has no tasks "
                        "left, deleting it from the database now.",
                        job.id, job.title)
            db.session.delete(job)

    db.session.commit()


@celery_app.task(ignore_results=True, bind=True)
def stop_task(self, task_id):
    db.session.commit()
    task = Task.query.filter_by(id=task_id).one()
    job = task.job

    if (task.agent is not None and
        task.state not in [WorkState.DONE, WorkState.FAILED]):
        agent = task.agent
        try:
            response = requests.delete("%s/tasks/%s" %
                                            (agent.api_url(), task.id),
                                       headers={"User-Agent": USERAGENT})

            logger.info("Stopping task %s (job %s - \"%s\") on agent %s (id %s)",
                        task.id, job.id, job.title, agent.hostname, agent.id)
            if response.status_code not in [requests.codes.accepted,
                                            requests.codes.ok,
                                            requests.codes.no_content,
                                            requests.codes.not_found]:
                raise ValueError("Unexpected return code on stopping task %s on "
                                 "agent %s: %s",
                                 task.id, agent.id, response.status_code)
            else:
                task.agent = None
                task.state = None
                db.session.add(task)
        # Catching ProtocolError here is a work around for
        # https://github.com/kennethreitz/requests/issues/2204
        except (ConnectionError, ProtocolError) as e:
            if self.request.retries < self.max_retries:
                logger.warning("Caught ConnectionError trying to delete task %s "
                               "from agent %s (id %s), retry %s of %s: %s",
                               task.id,
                               agent.hostname,
                               agent.id,
                               self.request.retries,
                               self.max_retries,
                               e)
                self.retry(exc=e)

    db.session.commit()

@celery_app.task(ignore_results=True)
def delete_job(job_id):
    db.session.commit()
    job = Job.query.filter_by(id=job_id).one()
    if not job.to_be_deleted:
        logger.warning("Not deleting job %s, it is not marked for deletion.",
                       job.id)
        return

    tasks_query = Task.query.filter_by(job=job)
    for task in tasks_query:
        delete_task.delay(task.id)
