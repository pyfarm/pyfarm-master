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
Celery Application
------------------

Creates the base instance of :class:`.Celery` which is used by components of
PyFarm's master that require interaction with a task queue.  This module also
configures Celery's beat scheduler for other tasks such as agent polling
and task assignment.
"""

from datetime import timedelta

from celery import Celery

from pyfarm.master.config import config

celery_app = Celery(
    "pyfarm.tasks",
    broker=config.get("scheduler_broker"),
    include=["pyfarm.scheduler.tasks", "pyfarm.scheduler.statistics_tasks"])

celery_app.conf.CELERYBEAT_SCHEDULE = {
    "periodically_poll_agents": {
        "task": "pyfarm.scheduler.tasks.poll_agents",
        "schedule": timedelta(**config.get("agent_poll_interval"))
    },
    "periodical_scheduler": {
        "task": "pyfarm.scheduler.tasks.assign_tasks",
        "schedule": timedelta(**config.get("agent_poll_interval"))
    },
    "periodically_clean_task_logs": {
        "task": "pyfarm.scheduler.tasks.clean_up_orphaned_task_logs",
        "schedule": timedelta(**config.get("orphaned_log_cleanup_interval"))
    },
    "periodically_delete_old_jobs": {
        "task": "pyfarm.scheduler.tasks.autodelete_old_jobs",
        "schedule": timedelta(**config.get("autodelete_old_job_interval")),
    },
    "periodically_compress_task_logs": {
        "task": "pyfarm.scheduler.tasks.compress_task_logs",
        "schedule": timedelta(**config.get("compress_log_interval"))
    },
    "periodically_execute_deletions": {
        "task": "pyfarm.scheduler.tasks.delete_to_be_deleted_jobs",
        "schedule": timedelta(**config.get("delete_job_interval")),
    }
}

if config.get("enable_statistics"):
    celery_app.conf.CELERYBEAT_SCHEDULE["periodically_count_agents"] = {
        "task": "pyfarm.scheduler.statistics_tasks.count_agents",
        "schedule": timedelta(**config.get("agent_count_interval"))
        }

if __name__ == '__main__':
    celery_app.start()
