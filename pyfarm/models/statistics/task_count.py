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
TaskCount Model
====================

Model describing the number of tasks in a given queue in a given state at a
point in time
"""

from datetime import datetime

from pyfarm.master.application import db
from pyfarm.master.config import config

from pyfarm.models.core.types import id_column


class TaskCount(db.Model):
    __bind_key__ = 'statistics'
    __tablename__ = config.get("table_statistics_task_count")

    id = id_column(db.Integer)

    counted_time = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        doc="The point in time at which these counts were done")

    # No foreign key reference, because this table is stored in a separate db
    # Code reading it will have to check for referential integrity manually.
    job_queue_id = db.Column(
        db.Integer,
        nullable=True,
        doc="ID of the jobqueue these stats refer to")

    total_queued = db.Column(
        db.Integer,
        nullable=False,
        doc="Number of queued tasks at `counted_time`")

    total_running = db.Column(
        db.Integer,
        nullable=False,
        doc="Number of running tasks at `counted_time`")

    total_done = db.Column(
        db.Integer,
        nullable=False,
        doc="Number of done tasks at `counted_time`")

    total_failed = db.Column(
        db.Integer,
        nullable=False,
        doc="Number of failed tasks at `counted_time`")
