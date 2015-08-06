# No shebang line, this module is meant to be imported
#
# Copyright 2015 Ambient Entertainment GmbH & Co. KG
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
Tasks For Statistics
--------------------

This module contains various celery tasks for gathering runtime statistics
about the farm.
"""

from datetime import datetime, timedelta
from logging import DEBUG

from pyfarm.core.logger import getLogger
from pyfarm.core.enums import AgentState, WorkState

from pyfarm.models.agent import Agent
from pyfarm.models.jobqueue import JobQueue
from pyfarm.models.task import Task
from pyfarm.models.job import Job
from pyfarm.models.statistics.agent_count import AgentCount
from pyfarm.models.statistics.task_event_count import TaskEventCount
from pyfarm.models.statistics.task_count import TaskCount

from pyfarm.master.config import config
from pyfarm.master.application import db

from pyfarm.scheduler.celery_app import celery_app

logger = getLogger("pf.scheduler.statistics_tasks")
# TODO Get logger configuration from pyfarm config
logger.setLevel(DEBUG)


@celery_app.task(ignore_result=True)
def count_agents():
    logger.debug("Counting known agents now")
    num_online = Agent.query.filter_by(state=AgentState.ONLINE).count()
    num_offline = Agent.query.filter_by(state=AgentState.OFFLINE).count()
    num_running = Agent.query.filter_by(state=AgentState.RUNNING).count()
    num_disabled = Agent.query.filter_by(state=AgentState.DISABLED).count()

    agent_count = AgentCount(counted_time=datetime.utcnow(),
                             num_online=num_online,
                             num_offline=num_offline,
                             num_running=num_running,
                             num_disabled=num_disabled)
    logger.info("Counted agents at %s: Online: %s, Offline: %s, Running: %s, "
                "Disabled: %s",
                agent_count.counted_time,
                agent_count.num_online,
                agent_count.num_offline,
                agent_count.num_running,
                agent_count.num_disabled)

    db.session.add(agent_count)
    db.session.commit()

@celery_app.task(ignore_result=True)
def consolidate_task_events():
    logger.debug("Consolidating task events now")

    queues_query = JobQueue.query

    for job_queue in queues_query:
        consolidate_task_events_for_queue.delay(job_queue.id)
    consolidate_task_events_for_queue.delay(None)

@celery_app.task(ignore_result=True)
def count_tasks():
    logger.debug("Counting tasks in all queues now")

    job_queues_query = JobQueue.query

    for job_queue in job_queues_query:
        task_count = TaskCount(job_queue_id=job_queue.id)
        task_count.total_queued = Task.query.filter(
            Task.job.has(Job.job_queue_id == job_queue.id),
            Task.state == None).count()
        task_count.total_running = Task.query.filter(
            Task.job.has(Job.job_queue_id == job_queue.id),
            Task.state == WorkState.RUNNING).count()
        task_count.total_done = Task.query.filter(
            Task.job.has(Job.job_queue_id == job_queue.id),
            Task.state == WorkState.DONE).count()
        task_count.total_failed = Task.query.filter(
            Task.job.has(Job.job_queue_id == job_queue.id),
            Task.state == WorkState.FAILED).count()

        db.session.add(task_count)

    db.session.commit()

@celery_app.task(ignore_result=True)
def consolidate_task_events_for_queue(job_queue_id):
    logger.debug("Consolidating task events for queue %s now", job_queue_id)

    consolidate_interval = timedelta(**config.get(
        "task_event_count_consolidate_interval"))

    def add_task_count(consolidation_count, event_count, last_count):
        consolidation_count.num_new += event_count.num_new
        consolidation_count.num_deleted += event_count.num_deleted
        consolidation_count.num_restarted += event_count.num_restarted
        consolidation_count.num_started += event_count.num_started
        consolidation_count.num_failed += event_count.num_failed
        consolidation_count.num_done += event_count.num_done

    event_counts_query = TaskEventCount.query.filter_by(
        job_queue_id=job_queue_id).order_by(TaskEventCount.time_start)

    last_count = None
    open_consolidation_count = None
    for event_count in event_counts_query:
        # If current count is not consolidated yet
        if event_count.time_end - event_count.time_start < consolidate_interval:
            if not open_consolidation_count:
                open_consolidation_count = TaskEventCount(
                    job_queue_id=job_queue_id,
                    num_new=0,
                    num_deleted=0,
                    num_restarted=0,
                    num_started=0,
                    num_failed=0,
                    num_done=0)
                open_consolidation_count.time_start = event_count.time_start
                open_consolidation_count.time_end = (event_count.time_start +
                                                     consolidate_interval)
                add_task_count(open_consolidation_count, event_count,
                               last_count)
                db.session.delete(event_count)
            else:
                # We know the event count does not fall into the period of the
                # next already existing consolidated count, because we sorted
                # the query by time_start, so the other consolidated count
                # would have come up before this unconsolidated one.
                while (event_count.time_start >
                       open_consolidation_count.time_end):
                    db.session.add(open_consolidation_count)
                    new_consolidation_count = TaskEventCount(
                        job_queue_id=job_queue_id,
                        num_new=0,
                        num_deleted=0,
                        num_restarted=0,
                        num_started=0,
                        num_failed=0,
                        num_done=0)
                    new_consolidation_count.time_start = (
                        open_consolidation_count.time_end)
                    new_consolidation_count.time_end = (
                        new_consolidation_count.time_start +
                        consolidate_interval)
                    open_consolidation_count = new_consolidation_count
                add_task_count(open_consolidation_count, event_count,
                               last_count)
                db.session.delete(event_count)
        else:
            if not open_consolidation_count:
                open_consolidation_count = event_count
            else:
                if event_count.time_start < open_consolidation_count.time_end:
                    add_task_count(open_consolidation_count, event_count,
                               last_count)
                    db.session.delete(event_count)
                else:
                    db.session.add(open_consolidation_count)
                    open_consolidation_count = event_count

    if open_consolidation_count:
        db.session.add(open_consolidation_count)

    db.session.commit()
