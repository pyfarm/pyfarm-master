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

from functools import partial
from textwrap import dedent

from sqlalchemy import event
from sqlalchemy.orm import validates

from pyfarm.core.enums import WorkState
from pyfarm.master.application import db
from pyfarm.models.core.types import IDTypeAgent, IDTypeWork
from pyfarm.models.core.functions import work_columns, repr_enum
from pyfarm.models.core.cfg import (
    TABLE_JOB, TABLE_TASK, TABLE_AGENT, TABLE_TASK_DEPENDENCIES, TABLE_PROJECT)
from pyfarm.models.core.mixins import (
    ValidatePriorityMixin, WorkStateChangedMixin, UtilityMixins, ReprMixin,
    ValidateWorkStateMixin)

__all__ = ("Task", )

TaskDependencies = db.Table(
    TABLE_TASK_DEPENDENCIES, db.metadata,
    db.Column("parent_id", IDTypeWork,
              db.ForeignKey("%s.id" % TABLE_TASK), primary_key=True),
    db.Column("child_id", IDTypeWork,
              db.ForeignKey("%s.id" % TABLE_TASK), primary_key=True))


class Task(db.Model, ValidatePriorityMixin, ValidateWorkStateMixin,
           WorkStateChangedMixin, UtilityMixins, ReprMixin):
    """
    Defines a task which a child of a :class:`Job`.  This table represents
    rows which contain the individual work unit(s) for a job.
    """
    __tablename__ = TABLE_TASK
    STATE_ENUM = WorkState
    STATE_DEFAULT = STATE_ENUM.QUEUED
    REPR_COLUMNS = ("id", "state", "frame", "project")
    REPR_CONVERT_COLUMN = {"state": partial(repr_enum, enum=STATE_ENUM)}

    # shared work columns
    id, state, priority, time_submitted, time_started, time_finished = \
        work_columns(STATE_DEFAULT, "job.priority")
    project_id = db.Column(db.Integer, db.ForeignKey("%s.id" % TABLE_PROJECT),
                           doc="stores the project id")
    agent_id = db.Column(IDTypeAgent, db.ForeignKey("%s.id" % TABLE_AGENT),
                         doc="Foreign key which stores :attr:`Job.id`")
    job_id = db.Column(IDTypeWork, db.ForeignKey("%s.id" % TABLE_JOB),
                       doc="Foreign key which stores :attr:`Job.id`")
    hidden = db.Column(db.Boolean, default=False,
                       doc=dedent("""
                       hides the task from queue and web ui"""))
    attempts = db.Column(db.Integer, nullable=False, default=0,
                         doc=dedent("""
                         The number of attempts which have been made on this
                         task. This value is auto incremented when
                         :attr:`state` changes to a value synonymous with a
                         running state."""))
    frame = db.Column(db.Numeric(10, 4), nullable=False,
                      doc="The frame this :class:`Task` will be executing.")

    # relationships
    parents = db.relationship("Task",
                              secondary=TaskDependencies,
                              primaryjoin=id==TaskDependencies.c.parent_id,
                              secondaryjoin=id==TaskDependencies.c.child_id,
                              backref=db.backref("children", lazy="dynamic"))
    project = db.relationship("Project",
                              backref=db.backref("tasks", lazy="dynamic"),
                              doc=dedent("""
                              relationship attribute which retrieves the
                              associated project for the task"""))
    job = db.relationship("Job",
                          backref=db.backref("tasks", lazy="dynamic"),
                          doc=dedent("""
                          relationship attribute which retrieves the
                          associated job for this task"""))

    @staticmethod
    def agentChangedEvent(target, new_value, old_value, initiator):
        """set the state to ASSIGN whenever the agent is changed"""
        if new_value is not None:
            target.state = target.STATE_ENUM.ASSIGN

    @staticmethod
    def incrementAttempts(target, new_value, old_value, initiator):
        target.attempts = target.attempts + 1 if target.attempts else 1

event.listen(Task.agent_id, "set", Task.agentChangedEvent)
event.listen(Task.state, "set", Task.stateChangedEvent)
event.listen(Task.state, "set", Task.incrementAttempts)
