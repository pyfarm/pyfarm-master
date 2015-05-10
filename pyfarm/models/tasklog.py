# No shebang line, this module is meant to be imported
#
# Copyright 2014 Ambient Entertainment GmbH & Co. KG
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
Task Log Models
===============

Model describing a log file for a task or batch of tasks.

A task can be associated with more than one log file, for example because
it needed to be retried and there are logs for every attempt or because the
job type used uses more than one process to execute a batch. A log file can
belong to more than one task if tasks have been batched together for execution.
"""

from datetime import datetime

from sqlalchemy.schema import UniqueConstraint, PrimaryKeyConstraint

from pyfarm.core.enums import WorkState
from pyfarm.models.core.types import WorkStateEnum
from pyfarm.master.application import db
from pyfarm.models.core.mixins import ReprMixin, UtilityMixins
from pyfarm.models.core.types import id_column, IDTypeAgent, IDTypeWork
from pyfarm.models.core.cfg import (
    TABLE_TASK_LOG, TABLE_AGENT, TABLE_TASK, TABLE_TASK_TASK_LOG_ASSOC)

class TaskTaskLogAssociation(db.Model):
    """Stores an association between the task table and a task log"""
    __tablename__ = TABLE_TASK_TASK_LOG_ASSOC
    __table_args__ = (
        PrimaryKeyConstraint("task_log_id", "task_id", "attempt"),)

    task_log_id = db.Column(
        db.Integer,
        db.ForeignKey("%s.id" % TABLE_TASK_LOG, ondelete="CASCADE"),
        doc="The ID of the task log")

    task_id = db.Column(
        IDTypeWork,
        db.ForeignKey("%s.id" % TABLE_TASK, ondelete="CASCADE"),
        doc="The ID of the job a task log is associated with")

    attempt = db.Column(
        db.Integer,
        autoincrement=False,
        doc="The attempt number for the given task log")

    state = db.Column(
        WorkStateEnum,
        nullable=True,
        doc="The state of the work being performed")

    #
    # Relationships
    #
    task = db.relationship(
        "Task",
        backref=db.backref(
            "log_associations",
            lazy="dynamic",
            passive_deletes=True))


class TaskLog(db.Model, UtilityMixins, ReprMixin):
    """Table which represents a single task log entry"""
    __tablename__ = TABLE_TASK_LOG
    __table_args__ = (UniqueConstraint("identifier"),)

    id = id_column(db.Integer)

    identifier = db.Column(
        db.String(255),
        nullable=False,
        doc="The identifier for this log")

    agent_id = db.Column(
        IDTypeAgent,
        db.ForeignKey("%s.id" % TABLE_AGENT),
        nullable=True,
        doc="The agent this log was created on")

    created_on = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        doc="The time when this log was created")

    #
    # Relationships
    #
    agent = db.relationship(
        "Agent",
        backref=db.backref("task_logs", lazy="dynamic"),
        doc="Relationship between an :class:`TaskLog`"
            "and the :class:`pyfarm.models.Agent` it was "
            "created on")

    task_associations = db.relationship(
        TaskTaskLogAssociation,
        backref="log",
        doc="Relationship between tasks and their logs."
    )

    def num_queued_tasks(self):
        return TaskTaskLogAssociation.query.filter_by(
            log=self, state=None).count()

    def num_running_tasks(self):
        return TaskTaskLogAssociation.query.filter_by(
            log=self, state=WorkState.RUNNING).count()

    def num_failed_tasks(self):
        return TaskTaskLogAssociation.query.filter_by(
            log=self, state=WorkState.FAILED).count()

    def num_done_tasks(self):
        return TaskTaskLogAssociation.query.filter_by(
            log=self, state=WorkState.DONE).count()
