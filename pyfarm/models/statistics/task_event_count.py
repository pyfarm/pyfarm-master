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
TaskEventCount Model
====================

Model describing the number of events that happened for tasks over a time
period
"""

from datetime import datetime

from pyfarm.master.application import db
from pyfarm.master.config import config

from pyfarm.models.core.types import id_column, IDTypeWork


class TaskEventCount(db.Model):
    __bind_key__ = 'statistics'
    __tablename__ = config.get("table_statistics_task_event_count")

    id = id_column(db.Integer)

    time_start = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow)

    time_end = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow)

    # No foreign key reference, because this table is stored in a separate db
    # Code reading it will have to check for referential integrity manually.
    job_queue_id = db.Column(
        db.Integer,
        nullable=True,
        doc="ID of the jobqueue these stats refer to")

    num_new = db.Column(
        db.Integer,
        nullable=False,
        default=0,
        doc="Number of tasks that were newly created during the time period")

    num_deleted = db.Column(
        db.Integer,
        nullable=False,
        default=0,
        doc="Number of tasks that were deleted during the time period")

    num_restarted = db.Column(
        db.Integer,
        nullable=False,
        default=0,
        doc="Number of tasks that were restarted during the time period")

    num_started = db.Column(
        db.Integer,
        nullable=False,
        default=0,
        doc="Number of tasks that work was started on during the time period")

    num_failed = db.Column(
        db.Integer,
        nullable=False,
        default=0,
        doc="Number of tasks that failed during the time period")

    num_done = db.Column(
        db.Integer,
        nullable=False,
        default=0,
        doc="Number of tasks that were finished successfully during the time "
            "period")

    avg_queued = db.Column(
        db.Float,
        nullable=False,
        doc="Average number of queued tasks during the time period")

    avg_running = db.Column(
        db.Float,
        nullable=False,
        doc="Average number of running tasks during the time period")

    avg_done = db.Column(
        db.Float,
        nullable=False,
        doc="Average number of done tasks during the time period")

    avg_failed = db.Column(
        db.Float,
        nullable=False,
        doc="Average number of failed tasks during the time period")
