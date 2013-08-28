# No shebang line, this module is meant to be imported
#
# Copyright 2013 Oliver Palmer
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

from uuid import UUID
from textwrap import dedent
from sqlalchemy import event
from pyfarm.models.core.app import db
from pyfarm.core.enums import WorkState
from pyfarm.models.core.types import IDType
from pyfarm.models.core.functions import WorkColumns, modelfor, getuuid
from pyfarm.models.core.cfg import TABLE_JOB, TABLE_TASK, TABLE_AGENT
from pyfarm.models.mixins import WorkValidationMixin, StateChangedMixin


class TaskModel(db.Model, WorkValidationMixin, StateChangedMixin):
    """
    Defines a task which a child of a :class:`Job`.  This table represents
    rows which contain the individual work unit(s) for a job.
    """
    __tablename__ = TABLE_TASK
    STATE_ENUM = WorkState
    STATE_DEFAULT = STATE_ENUM.QUEUED

    # shared work columns
    id, state, priority, time_submitted, time_started, time_finished = \
        WorkColumns(STATE_DEFAULT, "job.priority")

    attempts = db.Column(db.Integer, default=0,
                         doc=dedent("""
                         The number attempts which have been made on this
                         task. This value is auto incremented when
                         :attr:`state` changes to a value synonyms with a
                         running state."""))
    frame = db.Column(db.Float, nullable=False,
                      doc=dedent("""
                      The frame the :class:`TaskModel` will be executing."""))

    # relationships
    _agentid = db.Column(IDType, db.ForeignKey("%s.id" % TABLE_AGENT),
                         doc=dedent("""
                         Foreign key which stores :attr:`JobModel.id`"""))
    _jobid = db.Column(IDType, db.ForeignKey("%s.id" % TABLE_JOB),
                       doc=dedent("""
                       Foreign key which stores :attr:`JobModel.id`"""))
    _parenttask = db.Column(IDType, db.ForeignKey("%s.id" % TABLE_TASK),
                            doc=dedent("""
                            The foreign key which stores :attr:`TaskModel.id`
                            """))
    siblings = db.relationship("TaskModel",
                               backref=db.backref("task", remote_side=[id]),
                               doc=dedent("""
                               Relationship to other tasks which have the same
                               parent"""))

    @staticmethod
    def agentChangedEvent(target, new_value, old_value, initiator):
        """set the state to ASSIGN whenever the agent is changed"""
        if new_value is not None:
            target.state = target.STATE_ENUM.ASSIGN


event.listen(TaskModel._agentid, "set", TaskModel.agentChangedEvent)
event.listen(TaskModel.state, "set", TaskModel.stateChangedEvent)


class Task(TaskModel):
    """
    Provides :meth:`__init__` for :class:`TaskModel` so the model can
    be instanced with initial values.
    """
    def __init__(self, job, frame, parent_task=None, state=None,
                 priority=None, attempts=None, agent=None):
        self._jobid = getuuid(job, TABLE_JOB, "jobid", "parent job")
        self._parenttask = getuuid(parent_task, TABLE_TASK, "id", "parent task")
        self._agentid = getuuid(agent, TABLE_AGENT, "id", "agent id")
        self.frame = frame

        if state is not None:
            self.state = state

        if priority is not None:
            self.priority = priority

        if attempts is not None:
            self.attempts = attempts
