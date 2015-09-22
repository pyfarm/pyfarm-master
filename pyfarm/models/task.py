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
from datetime import datetime

from sqlalchemy import event

from pyfarm.core.logger import getLogger
from pyfarm.core.enums import WorkState, _WorkState
from pyfarm.master.application import db
from pyfarm.master.config import config
from pyfarm.models.core.types import IDTypeAgent, IDTypeWork
from pyfarm.models.core.functions import work_columns, repr_enum
from pyfarm.models.core.mixins import (
    ValidatePriorityMixin, UtilityMixins, ReprMixin, ValidateWorkStateMixin)

__all__ = ("Task", )

logger = getLogger("models.task")


class Task(db.Model, ValidatePriorityMixin, ValidateWorkStateMixin,
           UtilityMixins, ReprMixin):
    """
    Defines a task which a child of a :class:`Job`.  This table represents
    rows which contain the individual work unit(s) for a job.
    """
    __tablename__ = config.get("table_task")
    STATE_ENUM = list(WorkState) + [None]
    STATE_DEFAULT = None
    REPR_COLUMNS = ("id", "state", "frame", "project")
    REPR_CONVERT_COLUMN = {"state": partial(repr_enum, enum=STATE_ENUM)}

    # shared work columns
    id, state, priority, time_submitted, time_started, time_finished = \
        work_columns(STATE_DEFAULT, "job.priority")

    agent_id = db.Column(
        IDTypeAgent,
        db.ForeignKey("%s.id" % config.get("table_agent")),
        doc="Foreign key which stores :attr:`Job.id`")

    job_id = db.Column(
        IDTypeWork, db.ForeignKey("%s.id" % config.get("table_job")),
        nullable=False,
        doc="Foreign key which stores :attr:`Job.id`")

    hidden = db.Column(
        db.Boolean, default=False,
        doc="When True this hides the task from queue and web ui")

    attempts = db.Column(
        db.Integer,
        nullable=False, default=0,
        doc="The number of attempts which have been made on this "
            "task. This value is auto incremented when "
            "``state`` changes to a value synonymous with a "
            "running state.")

    failures = db.Column(
        db.Integer,
        nullable=False, default=0,
        doc="The number of times this task has failed. This value "
            "is auto incremented when :attr:`state` changes to a "
            "value synonymous with a failed state.")

    frame = db.Column(
        db.Numeric(10, 4),
        nullable=False,
        doc="The frame this :class:`Task` will be executing.")

    tile = db.Column(
        db.Integer,
        nullable=True,
        doc="When using tiled rendering, the number of the tile this task "
            "refers to. The jobtype will have to translate that into an "
            "actual image region. This will be NULL if the job doesn't use "
            "tiled rendering.")

    last_error = db.Column(
        db.UnicodeText,
        nullable=True,
        doc="This column may be set when an error is "
            "present.  The agent typically sets this "
            "column when the job type either can't or "
            "won't run a given task.  This column will "
            "be cleared whenever the task's state is "
            "returned to a non-error state.")

    sent_to_agent = db.Column(
        db.Boolean,
        default=False, nullable=False,
        doc="Whether this task was already sent to the assigned agent")

    progress = db.Column(
        db.Float, default=0.0,
        doc="The progress for this task, as a value between "
            "0.0 and 1.0. Used purely for display purposes.")

    #
    # Relationships
    #
    job = db.relationship(
        "Job",
        backref=db.backref("tasks", lazy="dynamic"),
        doc="relationship attribute which retrieves the "
            "associated job for this task")

    def running(self):
        return self.state == WorkState.RUNNING

    def failed(self):
        return self.state == WorkState.FAILED

    @staticmethod
    def increment_attempts(target, new_value, old_value, initiator):
        if new_value is not None and new_value != old_value:
            target.attempts += 1

    @staticmethod
    def log_assign_change(target, new_value, old_value, initiator):
        logger.debug("Agent change for task %s: old %s new: %s",
                     target.id, old_value, new_value)

    @staticmethod
    def update_failures(target, new_value, old_value, initiator):
        if new_value == WorkState.FAILED and new_value != old_value:
            target.failures += 1
            if target not in target.agent.failed_tasks:
                target.agent.failed_tasks.append(target)

    @staticmethod
    def set_progress_on_success(target, new_value, old_value, initiator):
        if new_value == WorkState.DONE:
            target.progress = 1.0

    @staticmethod
    def update_agent_on_success(target, new_value, old_value, initiator):
        if new_value == WorkState.DONE:
            agent = target.agent
            if agent:
                agent.last_success_on = datetime.utcnow()
                db.session.add(agent)

    @staticmethod
    def reset_agent_if_failed_and_retry(
            target, new_value, old_value, initiator):
        # There's nothing else we should do here if
        # we don't have a parent job.  This can happen if you're
        # testing or a job is disconnected from a task.
        if target.job is None:
            return new_value

        if (new_value == WorkState.FAILED and
            target.failures <= target.job.requeue):
            logger.info("Failed task %s will be retried", target.id)
            target.agent_id = None
            return None
        else:
            return new_value

    @staticmethod
    def clear_error_state(target, new_value, old_value, initiator):
        """
        Sets ``last_error`` column to ``None`` if the task's state is 'done'
        """
        if new_value == WorkState.DONE and target.last_error is not None:
            target.last_error = None

    @staticmethod
    def set_times(target, new_value, old_value, initiator):
        """update the datetime objects depending on the new value"""

        if (new_value == _WorkState.RUNNING and
            (old_value not in [_WorkState.RUNNING, _WorkState.PAUSED] or
             target.time_started == None)):
            if not target.job.jobtype_version.no_automatic_start_time:
                target.time_started = datetime.utcnow()
                target.time_finished = None

        elif (new_value in (_WorkState.DONE, _WorkState.FAILED) and
              not target.time_finished):
            target.time_finished = datetime.utcnow()

    @staticmethod
    def reset_finished_time(target, new_value, old_value, initiator):
        if (target.state not in (_WorkState.DONE, _WorkState.FAILED) or
            new_value is None):
            target.time_finished = None
        elif new_value is not None:
            if target.time_finished is not None:
                target.time_finished = max(target.time_finished,
                                           new_value)
            else:
                target.time_finished = max(new_value,
                                           datetime.utcnow())

event.listen(Task.state, "set", Task.clear_error_state)
event.listen(Task.state, "set", Task.set_times)
event.listen(Task.state, "set", Task.update_failures)
event.listen(Task.state, "set", Task.set_progress_on_success)
event.listen(Task.state, "set", Task.update_agent_on_success)
event.listen(Task.agent_id, "set", Task.increment_attempts)
event.listen(Task.agent_id, "set", Task.log_assign_change)
event.listen(Task.state, "set", Task.reset_agent_if_failed_and_retry,
             retval=True)
event.listen(Task.time_started, "set", Task.reset_finished_time)
