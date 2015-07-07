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
AgentCount Model
=========

Model describing a the counts for agents in various states at a given point
in time.
"""

from pyfarm.master.application import db
from pyfarm.master.config import config


class AgentCount(db.Model):
    __bind_key__ = 'statistics'
    __tablename__ = config.get("table_statistics_agent_count")

    counted_time = db.Column(
        db.DateTime,
        primary_key=True,
        nullable=False,
        autoincrement=False,
        doc="The point in time at which these counts were done")

    num_online = db.Column(
        db.Integer,
        nullable=False,
        doc="The number of agents that were in state `online` at counted_time")

    num_running = db.Column(
        db.Integer,
        nullable=False,
        doc="The number of agents that were in state `running` at counted_time")

    num_offline = db.Column(
        db.Integer,
        nullable=False,
        doc="The number of agents that were in state `offline` at counted_time")

    num_disabled = db.Column(
        db.Integer,
        nullable=False,
        doc="The number of agents that were in state `disabled` at "
            "counted_time")
