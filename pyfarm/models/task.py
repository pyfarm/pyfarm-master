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

"""
Task Models
===========

Models and interface classes related to tasks
"""

from textwrap import dedent

from sqlalchemy import event
from pyfarm.core.enums import WorkState
from pyfarm.master.application import db
from pyfarm.models.core.types import IDTypeAgent, IDTypeWork
from pyfarm.models.core.functions import WorkColumns
from pyfarm.models.core.cfg import (
    TABLE_JOB, TABLE_TASK, TABLE_AGENT, TABLE_TASK_DEPENDENCIES)
from pyfarm.models.core.mixins import WorkValidationMixin, StateChangedMixin

TaskDependencies = db.Table(
    TABLE_TASK_DEPENDENCIES, db.metadata,
    db.Column("parentid", IDTypeWork,
              db.ForeignKey("%s.id" % TABLE_TASK), primary_key=True),
    db.Column("childid", IDTypeWork,
              db.ForeignKey("%s.id" % TABLE_TASK), primary_key=True))


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

    hidden = db.Column(db.Boolean, default=False,
                       doc=dedent("""
                       hides the task from queue and web ui"""))
    attempts = db.Column(db.Integer,
                         doc=dedent("""
                         The number attempts which have been made on this
                         task. This value is auto incremented when
                         :attr:`state` changes to a value synonyms with a
                         running state."""))
    frame = db.Column(db.Float, nullable=False,
                      doc=dedent("""
                      The frame the :class:`TaskModel` will be executing."""))

    # relationships
    agentid = db.Column(IDTypeAgent, db.ForeignKey("%s.id" % TABLE_AGENT),
                        doc=dedent("""
                        Foreign key which stores :attr:`JobModel.id`"""))
    jobid = db.Column(IDTypeWork, db.ForeignKey("%s.id" % TABLE_JOB),
                      doc=dedent("""
                      Foreign key which stores :attr:`JobModel.id`"""))

    parents = db.relationship("TaskModel",
                              secondary=TaskDependencies,
                              primaryjoin=id==TaskDependencies.c.parentid,
                              secondaryjoin=id==TaskDependencies.c.childid,
                              backref="children")

    @staticmethod
    def agentChangedEvent(target, new_value, old_value, initiator):
        """set the state to ASSIGN whenever the agent is changed"""
        if new_value is not None:
            target.state = target.STATE_ENUM.ASSIGN


event.listen(TaskModel.agentid, "set", TaskModel.agentChangedEvent)
event.listen(TaskModel.state, "set", TaskModel.stateChangedEvent)
