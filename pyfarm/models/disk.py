# No shebang line, this module is meant to be imported
#
# Copyright 2015 Ambient Entertainment GmbH & Co. KG
# Copyright 2015 Oliver Palmer
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
Disk Model
==========

Model describing a given disk, with size and free space.
"""

from sqlalchemy.schema import UniqueConstraint

from pyfarm.master.application import db
from pyfarm.models.core.types import IDTypeAgent
from pyfarm.models.core.mixins import ReprMixin, UtilityMixins
from pyfarm.models.core.types import id_column
from pyfarm.master.config import config

class AgentDisk(db.Model, UtilityMixins, ReprMixin):
    """
    Stores information about a single disk belonging to an agent, including
    usage information.
    """
    __tablename__ =  config.get("table_agent_disk")

    id = id_column(db.Integer)

    agent_id = db.Column(
        IDTypeAgent,
        db.ForeignKey("%s.id" % config.get("table_agent")),
        nullable=False)

    mountpoint = db.Column(
        db.String(config.get("max_mountpoint_length")),
        nullable=False,
        doc="The mountpoint of this disk on the agent "
            "(Drive letter for Windows agents)")

    size = db.Column(
        db.BigInteger,
        nullable=False,
        doc="The total capacity of this disk in bytes")

    free = db.Column(
        db.BigInteger,
        nullable=False,
        doc="Available space on the disk in bytes.")
