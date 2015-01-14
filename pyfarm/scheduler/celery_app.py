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

from pyfarm.core.config import read_env_int, read_env

celery_app = Celery("pyfarm.tasks",
                    broker=read_env("PYFARM_SCHEDULER_BROKER", "redis://"),
                    include=["pyfarm.scheduler.tasks"])

celery_app.conf.CELERYBEAT_SCHEDULE = {
    "periodically_poll_agents": {
        "task": "pyfarm.scheduler.tasks.poll_agents",
        "schedule": timedelta(
            seconds=read_env_int("PYFARM_AGENTS_POLL_INTERVAL", 30))},
    "periodical_scheduler": {
        "task": "pyfarm.scheduler.tasks.assign_tasks",
        "schedule": timedelta(seconds=read_env_int("PYFARM_SCHEDULER_INTERVAL",
                                                   240))},
    "periodically_clean_task_logs": {
        "task": "pyfarm.scheduler.tasks.clean_up_orphaned_task_logs",
        "schedule": timedelta(seconds=read_env_int("PYFARM_LOG_CLEANUP_INTERVAL",
                                                   3600))},
    "periodically_delete_old_jobs": {
        "task": "pyfarm.scheduler.tasks.autodelete_old_jobs",
        "schedule": timedelta(seconds=read_env_int("PYFARM_AUTODELETE_INTERVAL",
                                                   3600))},
    "periodically_compress_task_logs": {
        "task": "pyfarm.scheduler.tasks.compress_task_logs",
        "schedule": timedelta(
            seconds=read_env_int("PYFARM_LOG_COMPRESS_INTERVAL", 600))}
        }

if __name__ == '__main__':
    celery_app.start()
