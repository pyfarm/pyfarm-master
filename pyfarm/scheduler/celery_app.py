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

from datetime import timedelta
from pyfarm.core.config import read_env_int

from celery import Celery

celery_app = Celery('pyfarm.tasks',
                    broker='redis://',
                    include=['pyfarm.scheduler.tasks'])

celery_app.conf.CELERYBEAT_SCHEDULE = {
    "periodically_poll_agents": {
        "task": "pyfarm.scheduler.tasks.poll_agents",
        "schedule": timedelta(
            seconds=read_env_int("AGENTS_POLL_INTERVAL", 30))},
    "periodical_scheduler": {
        "task": "pyfarm.scheduler.tasks.assign_tasks",
        "schedule": timedelta(seconds=read_env_int("SCHEDULER_INTERVAL", 30))}}

if __name__ == '__main__':
    celery_app.start()
