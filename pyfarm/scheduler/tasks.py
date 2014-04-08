# No shebang line, this module is meant to be imported
#
# Copyright 2014 Ambient Entertainment GmbH & Co. KG
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

from math import ceil
from decimal import Decimal
from logging import DEBUG, INFO
from json import dumps

from sqlalchemy import or_, and_, func

import requests

from pyfarm.core.logger import getLogger
from pyfarm.core.enums import AgentState, WorkState, UseAgentAddress
from pyfarm.core.config import read_env
from pyfarm.models.core.cfg import TABLES
from pyfarm.models.project import Project
from pyfarm.models.software import (
    Software, SoftwareVersion, JobSoftwareRequirement,
    JobTypeSoftwareRequirement)
from pyfarm.models.tag import Tag
from pyfarm.models.task import Task, TaskDependencies
from pyfarm.models.job import Job, JobDependencies
from pyfarm.models.jobtype import JobType
from pyfarm.models.agent import (
    Agent, AgentTagAssociation)
from pyfarm.models.user import User, Role
from pyfarm.master.application import db
from pyfarm.master.utility import default_json_encoder

from pyfarm.scheduler.celery_app import celery_app


try:
    range_ = xrange
except NameError:
    range_ = range

logger = getLogger("pf.scheduler.tasks")
# TODO Get logger configuration from pyfarm config
logger.setLevel(DEBUG)


@celery_app.task(ignore_result=True)
def send_tasks_to_agent(agent_id):
    agent = Agent.query.filter(Agent.id == agent_id).first()
    if not agent:
        raise KeyError("agent not found")

    logger.debug("Sending assigned batches to agent %s (id %s)", agent.hostname,
                 agent_id)
    if agent.state in ["offline", "disabled"]:
        raise ValueError("agent not available")

    if agent.use_address == UseAgentAddress.PASSIVE:
        logger.debug("Agent's use address mode is PASSIVE, not sending anything")
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
                                     "frame": task.frame})

        logger.info("Sending a batch of %s tasks for job %s (%s) to agent %s",
                    len(tasks), job.title, job.id, agent.hostname)
        try:
            response = requests.post(agent.api_url(),
                                     data=dumps(message,
                                                default=default_json_encoder),
                                     headers={"Content-Type":"application/json"})

            if response.status_code not in [requests.codes.accepted,
                                            requests.codes.ok,
                                            requests.codes.created]:
                raise ValueError("Unexpected return code on sending batch to "
                                 "agent: %s", response.status_code)

            response.read()
        except requests.exceptions.ConnectionError:
            agent.state = AgentState.OFFLINE
            db.session.add(agent)
            db.session.commit()
            raise


def agents_with_tasks_at_prio(priority):
    query = Agent.query.filter(~Agent.state.in_([AgentState.OFFLINE,
                                                 AgentState.DISABLED]))
    query = query.filter(Agent.tasks.any(Task.priority == priority))
    return query.count()


def satisfies_requirements(agent, job):
    logger.debug("Checking to see if agent %s satisfies the requirements for "
                 "job %s", agent.hostname, job.title)
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
                logger.debug("Software version %r satisfies requirement %r",
                             software_version, requirement)
                satisfied_requirements.append(requirement)
            else:
                logger.debug("Software version %r does not satisfy "
                             "requirement %r", software_version, requirement)

    return len(requirements_to_satisfy) <= len(satisfied_requirements)


def get_batch_agent_pair(priority, except_job_ids=None):
    """
    Get a batch of tasks with priority :attr:`priority` and a suitable agent to
    assign the to.
    Returns None if no waiting tasks with exactly priority :attr:`priority` can
    be found or no suitable agents can be found for any waiting tasks at priority
    :attr:`priority`.

    :returns: A tuple of a list of tasks and an agent or None

    :param int priority:
        The priority the assigned tasks must have

    :param list except_job_ids:
        A list of job ids we should not try to assign
    """
    # Try to get an already started job first
    logger.info("Trying to assign one batch of tasks, except jobs %s",
                   except_job_ids)
    job_query = Job.query.filter(or_(Job.state == None,
                                     ~Job.state.in_(
                                         [WorkState.PAUSED,
                                          WorkState.DONE,
                                          WorkState.FAILED])))
    if except_job_ids:
        job_query = job_query.filter(~Job.id.in_(except_job_ids))
    job_query = job_query.filter(Job.tasks.any(Task.state.in_(
        [WorkState.RUNNING, WorkState.DONE, WorkState.FAILED])))
    job_query = job_query.filter(Job.tasks.any(and_(
        or_(Task.state == None,
            ~Task.state.in_([WorkState.DONE, WorkState.FAILED])),
        Task.agent == None,
        Task.priority == priority)))
    job = job_query.first()
    if job:
        logger.info("Trying to assign agents to started job %s", job.title)

    # Only if that didn't produce anything, try to start a queued one
    if not job:
        job_query = Job.query.filter(or_(Job.state == None,
                                         ~Job.state.in_(
                                             [WorkState.PAUSED,
                                              WorkState.DONE,
                                              WorkState.FAILED])))
        # Make sure we don't start jobs with unfulfilled dependencies
        job_query.filter(~Job.parents.any(or_(Job.state == None,
                                              Job.state != WorkState.DONE)))
        if except_job_ids:
            job_query = job_query.filter(~Job.id.in_(except_job_ids))
        job_query = job_query.filter(
            Job.tasks.any(
                and_(or_(Task.state == None,
                         ~Task.state.in_([WorkState.DONE, WorkState.FAILED])),
                     Task.agent == None,
                     Task.priority == priority)))
        job = job_query.order_by("time_submitted asc").first()
        if job:
            logger.debug("Starting job %r (id %s) now", job.title, job.id)
        else:
            logger.debug("Did not find a job with unassigned tasks at "
                         "priority %s", priority)
            return None

    tasks_query = Task.query.filter(Task.job == job,
                                    or_(Task.state == None,
                                        ~Task.state.in_([WorkState.DONE,
                                                         WorkState.FAILED])),
                                    or_(Task.agent == None,
                                        Task.agent.has(Agent.state.in_(
                                            [AgentState.OFFLINE,
                                             AgentState.DISABLED]))),
                                    Task.priority == priority).order_by(
                                        "frame asc")
    batch = []
    for task in tasks_query:
        if (len(batch) < job.batch and
            (not job.jobtype_version.batch_contiguous or
             (len(batch) == 0 or
              batch[-1].frame + job.by == task.frame))):
                 batch.append(task)

    logger.debug("Looking for an agent for a batch of %s tasks from job %s",
                 len(batch), job.title)

    # First look for an agent that has already successfully worked on tasks from
    # the same job in the past
    query = db.session.query(Agent, func.count(
        SoftwareVersion.id).label("num_versions"))
    query = query.filter(Agent.state.in_([AgentState.ONLINE,
                                          AgentState.RUNNING]))
    query = query.filter(Agent.free_ram >= job.ram)
    query = query.filter(~Agent.tasks.any(or_(Task.state == None,
                                      and_(Task.state != WorkState.DONE,
                                           Task.state != WorkState.FAILED))))
    query = query.filter(Agent.tasks.any(and_(Task.state == WorkState.DONE,
                                      Task.job == job)))
    # Order by num_versions so we select agents with the fewest supported
    # software versions first
    query = query.group_by(Agent).order_by("num_versions asc")

    selected_agent = None
    for agent, num_versions in query:
        if not selected_agent and satisfies_requirements(agent, job):
            selected_agent = agent

    if not selected_agent:
        query = db.session.query(Agent, func.count(
            SoftwareVersion.id).label("num_versions"))
        query = query.filter(Agent.state.in_([AgentState.ONLINE,
                                              AgentState.RUNNING]))
        query = query.filter(Agent.free_ram >= job.ram)
        query = query.filter(~Agent.tasks.any(or_(Task.state == None,
                                          and_(Task.state != WorkState.DONE,
                                               Task.state != WorkState.FAILED))))
        query = query.group_by(Agent).order_by("num_versions asc")
        for agent, num_versions in query:
            if not selected_agent and satisfies_requirements(agent, job):
                selected_agent = agent

    if not selected_agent:
        # We did not find any suitable agents for this job, see if we can find
        # some for some other job
        logger.debug("Did not find a suitable agent for job %s, trying to find "
                     "another job", job.title)
        if except_job_ids:
            return get_batch_agent_pair(priority, except_job_ids + [job.id])
        else:
            return get_batch_agent_pair(priority, [job.id])

    return batch, selected_agent


@celery_app.task(ignore_result=True,
                 rate_limit=read_env("PYFARM_SCHEDULER_RATE_LIMIT", "1/s"))
def assign_tasks():
    """
    Assigns unassigned tasks to agents that can take them, with proportionally
    more agents going to tasks with higher priorities.
    """
    logger.info("Assigning tasks to agents")
    tasks_query = Task.query.filter(
        or_(Task.state == None, ~Task.state.in_([WorkState.DONE,
                                                 WorkState.FAILED])))
    tasks_query = tasks_query.filter(
        or_(Task.agent == None,
            Task.agent.has(Agent.state.in_([AgentState.OFFLINE,
                                            AgentState.DISABLED]))))
    unassigned_tasks = tasks_query.count()
    logger.debug("Got %s unassigned tasks" % unassigned_tasks)
    if not unassigned_tasks:
        logger.info("No unassigned tasks, not assigning anything")
        return

    idle_agents = Agent.query.filter(Agent.state == AgentState.ONLINE,
                                     ~Agent.tasks.any()).count()
    if not idle_agents:
        logger.info("No idle agents, not assigning anything")
        return

    runnable_tasks = Task.query.filter(or_(
        Task.state == None, ~Task.state.in_([WorkState.PAUSED,
                                             WorkState.DONE,
                                             WorkState.FAILED]))).all()

    num_tasks_by_prio = {}
    for task in runnable_tasks:
        num_tasks_by_prio.setdefault(task.priority, 0)
        num_tasks_by_prio[task.priority] += 1

    max_prio = max(num_tasks_by_prio.keys())
    min_prio = min(num_tasks_by_prio.keys())

    # Preexisting assignments
    agent_with_tasks_at_prio = {}
    for priority in range_(min_prio, max_prio + 1):
        agent_with_tasks_at_prio[priority] = agents_with_tasks_at_prio(priority)

    # main scheduler loop
    # This works like a weighted fair queue with every priority forming its own
    # input queue.
    matchables_left = True
    agents_with_new_tasks = []
    while unassigned_tasks and idle_agents and matchables_left:
        for floor in range_(max_prio, min_prio-1, -1):
            assigned = 0
            for current_prio in range_(max_prio, floor-1, -1):
                if agent_with_tasks_at_prio[current_prio] > 0:
                    agent_with_tasks_at_prio[current_prio] -= 1
                    assigned += 1
                else:
                    batch_agent_tuple = get_batch_agent_pair(current_prio)
                    if batch_agent_tuple:
                        batch, agent = batch_agent_tuple
                        for task in batch:
                            task.agent = agent
                            db.session.add(task)
                            logger.info("Assigning task %s (frame %s from job"
                                        " %s) to agent %s (id %s)",
                                        task.id, task.frame, task.job.title,
                                        agent.hostname, agent.id)
                        assigned += 1
                        idle_agents -= 1
                        unassigned_tasks -= len(batch)
                        agents_with_new_tasks.append(agent)
                        db.session.flush()
            if floor == min_prio and assigned == 0:
                logger.info("None of the unassigned tasks are compatible with "
                            "any of the idle agents")
                matchables_left = False

    db.session.commit()

    for agent in agents_with_new_tasks:
        logger.debug("Registering asynchronous task pusher for agent %s",
                     agent.id)
        send_tasks_to_agent.delay(agent.id)
