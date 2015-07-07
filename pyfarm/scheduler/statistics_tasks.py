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
-----

This module contains various celery tasks for gathering runtime statistics
about the farm.
"""

from datetime import datetime
from logging import DEBUG

from pyfarm.core.logger import getLogger
from pyfarm.core.enums import AgentState

from pyfarm.models.agent import Agent
from pyfarm.models.statistics.agent_count import AgentCount

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
