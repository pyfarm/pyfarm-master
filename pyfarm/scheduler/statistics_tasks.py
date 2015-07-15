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
from pyfarm.core.enums import AgentState

from pyfarm.models.agent import Agent
from pyfarm.models.jobqueue import JobQueue
from pyfarm.models.statistics.agent_count import AgentCount
from pyfarm.models.statistics.task_event_count import TaskEventCount

from pyfarm.master.config import config
from pyfarm.master.application import db

from pyfarm.scheduler.celery_app import celery_app

logger = getLogger("pf.scheduler.statistics_tasks")
# TODO Get logger configuration from pyfarm config
logger.setLevel(DEBUG)


@celery_app.task(ignore_result=True, bind=True)
def count_agents(self):
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

@celery_app.task(ignore_result=True, bind=True)
def consolidate_task_events(self):
    logger.debug("Consolidating task events now")

    queues_query = JobQueue.query

    for job_queue in queues_query:
        consolidate_task_events_for_queue.delay(job_queue.id)
    consolidate_task_events_for_queue.delay(None)

@celery_app.task(ignore_result=True, bind=True)
def consolidate_task_events_for_queue(self, job_queue_id):
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

        if (last_count and
            last_count.time_end > consolidation_count.time_start and
            last_count.time_end < consolidation_count.time_end and
            last_count.time_end < event_count.time_end):
            old_period = last_count.time_end - consolidation_count.time_start
            new_period = (
                min(event_count.time_end, consolidation_count.time_end) -
                last_count.time_end)
        else:
            old_period = timedelta()
            new_period = (
                min(event_count.time_end, consolidation_count.time_end) -
                consolidation_count.time_start)

        new_period_part = new_period / (old_period + new_period)
        old_period_part = old_period / (old_period + new_period)

        consolidation_count.avg_queued = (
            event_count.avg_queued * new_period_part +
            consolidation_count.avg_queued * old_period_part)
        consolidation_count.avg_running = (
            event_count.avg_running * new_period_part +
            consolidation_count.avg_running * old_period_part)
        consolidation_count.avg_done = (
            event_count.avg_done * new_period_part +
            consolidation_count.avg_done * old_period_part)
        consolidation_count.avg_failed = (
            event_count.avg_failed * new_period_part +
            consolidation_count.avg_failed * old_period_part)

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
                    num_done=0,
                    avg_queued=0.0,
                    avg_running=0.0,
                    avg_done=0.0,
                    avg_failed=0.0)
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
                        num_done=0,
                        avg_queued=open_consolidation_count.avg_queued,
                        avg_running=open_consolidation_count.avg_running,
                        avg_done=open_consolidation_count.avg_done,
                        avg_failed=open_consolidation_count.avg_failed)
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

    db.session.commit()
