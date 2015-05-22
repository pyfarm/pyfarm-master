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
Job Models
==========

Models and interface classes related to jobs.

"""

try:
    import pwd
except ImportError:  # pragma: no cover
    pwd = None

from sys import maxsize

from sqlalchemy import event, distinct, or_, and_
from sqlalchemy.orm import validates

from pyfarm.core.logger import getLogger
from pyfarm.core.enums import WorkState, DBWorkState, _WorkState, AgentState
from pyfarm.master.application import db
from pyfarm.master.config import config
from pyfarm.models.core.functions import work_columns
from pyfarm.models.core.types import JSONDict, IDTypeWork

from pyfarm.models.core.mixins import (
    ValidatePriorityMixin, WorkStateChangedMixin, ReprMixin,
    ValidateWorkStateMixin, UtilityMixins)
from pyfarm.models.jobtype import JobType, JobTypeVersion
from pyfarm.models.task import Task

__all__ = ("Job", )

logger = getLogger("models.job")


JobTagAssociation = db.Table(
    config.get("table_job_tag_assoc"),
    db.metadata,
    db.Column(
        "job_id",
        IDTypeWork,
        db.ForeignKey("%s.id" % config.get("table_job")),
        primary_key=True,
        doc="The id of the job associated with this task"),
    db.Column(
        "tag_id",
        db.Integer,
        db.ForeignKey("%s.id" % config.get("table_tag")),
        primary_key=True,
        doc="The id of the tag being associated with the job")
)


JobDependency = db.Table(
    config.get("table_job_dependency"), db.metadata,
    db.Column(
        "parentid",
        IDTypeWork,
        db.ForeignKey("%s.id" % config.get("table_job")),
        primary_key=True,
        doc="The parent job id of the job dependency"),
    db.Column(
        "childid",
        IDTypeWork,
        db.ForeignKey("%s.id" % config.get("table_job")),
        primary_key=True,
        doc="The child job id of the job dependency")
)


class JobNotifiedUser(db.Model):
    """
    Defines the table containing users to be notified of certain
    events pertaining to jobs.
    """
    __tablename__ = config.get("table_job_notified_users")

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("%s.id" % config.get("table_user")),
        primary_key=True,
        doc="The id of the user to be notified")

    job_id = db.Column(
        IDTypeWork,
        db.ForeignKey("%s.id" % config.get("table_job")),
        primary_key=True,
        doc="The id of the associated job")

    on_success = db.Column(
        db.Boolean,
        nullable=False, default=True,
        doc="True if a user should be notified on successful "
            "completion of a job")

    on_failure = db.Column(
        db.Boolean,
        nullable=False, default=True,
        doc="True if a user should be notified of a job's failure")

    on_deletion = db.Column(
        db.Boolean,
        nullable=False, default=False,
        doc="True if a user should be notified on deletion of "
            "a job")

    user = db.relationship(
        "User",
        backref=db.backref("subscribed_jobs", lazy="dynamic"))


class Job(db.Model, ValidatePriorityMixin, ValidateWorkStateMixin,
          WorkStateChangedMixin, ReprMixin, UtilityMixins):
    """
    Defines the attributes and environment for a job.  Individual commands
    are kept track of by :class:`Task`
    """
    __tablename__ = config.get("table_job")
    REPR_COLUMNS = ("id", "state", "project")
    REPR_CONVERT_COLUMN = {"state": repr}
    STATE_ENUM = list(WorkState) + [None]

    # shared work columns
    id, state, priority, time_submitted, time_started, time_finished = \
        work_columns(None, "job.priority")

    jobtype_version_id = db.Column(
        IDTypeWork,
        db.ForeignKey("%s.id" % config.get("table_job_type_version")),
        nullable=False,
        doc="The foreign key which stores :class:`JobTypeVersion.id`")

    job_queue_id = db.Column(
        IDTypeWork,
        db.ForeignKey("%s.id" % config.get("table_job_queue")),
        nullable=True,
        doc="The foreign key which stores :class:`JobQueue.id`")

    job_group_id = db.Column(
        IDTypeWork,
        db.ForeignKey("%s.id" % config.get("table_job_group")),
        nullable=True,
        doc="The foreign key which stores:class:`JobGroup.id`")

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("%s.id" % config.get("table_user")),
        doc="The id of the user who owns this job")

    minimum_agents = db.Column(
        db.Integer,
        nullable=True,
        doc="The scheduler will try to assign at least this number "
            "of agents to this job as long as it can use them, "
            "before any other considerations.")

    maximum_agents = db.Column(
        db.Integer,
        nullable=True,
        doc="The scheduler will never assign more than this number"
            "of agents to this job.")

    weight = db.Column(
        db.Integer,
        nullable=False,
        default=config.get("queue_default_weight"),
        doc="The weight of this job. The scheduler will distribute "
            "available agents between jobs and job queues in the "
            "same queue in proportion to their weights.")

    title = db.Column(
        db.String(config.get("jobtitle_max_length")),
        nullable=False,
        doc="The title of this job")

    notes = db.Column(
        db.Text,
        default="",
        doc="Notes that are provided on submission or added after "
            "the fact. This column is only provided for human "
            "consumption, is not scanned, indexed, or used when "
            "searching")

    output_link = db.Column(
        db.Text,
        nullable=True,
        doc="An optional link to a URI where this job's output can "
            "be viewed.")

    # task data
    by = db.Column(
        db.Numeric(10, 4),
        default=1,
        doc="The number of frames to count by between `start` and "
            "`end`.  This column may also sometimes be referred to "
            "as 'step' by other software.")

    batch = db.Column(
        db.Integer,
        default=config.get("job_default_batch"),
        doc="Number of tasks to run on a single agent at once. Depending "
            "on the capabilities of the software being run this will "
            "either cause a single process to execute on the agent "
            "or multiple processes one after the other.")

    requeue = db.Column(
        db.Integer,
        default=config.get("job_requeue_default"),
        doc="Number of times to requeue failed tasks "
            ""
            ".. csv-table:: **Special Values**"
            "   :header: Value, Result"
            "   :widths: 10, 50"
            ""
            "   0, never requeue failed tasks"
            "  -1, requeue failed tasks indefinitely")

    cpus = db.Column(
        db.Integer,
        default=config.get("job_default_cpus"),
        doc="Number of cpus or threads each task should consume on"
            "each agent.  Depending on the job type being executed "
            "this may result in additional cpu consumption, longer "
            "wait times in the queue (2 cpus means 2 'fewer' cpus on "
            "an agent), or all of the above."
            ""
            ".. csv-table:: **Special Values**"
            "   :header: Value, Result"
            "   :widths: 10, 50"
            ""
            "   0, minimum number of cpu resources not required "
            "   -1, agent cpu is exclusive for a task from this job")

    ram = db.Column(
        db.Integer,
        default=config.get("job_default_ram"),
        doc="Amount of ram a task from this job will require to be "
            "free in order to run.  A task exceeding this value will "
            "not result in any special behavior."
            ""
            ".. csv-table:: **Special Values**"
            "    :header: Value, Result"
            "    :widths: 10, 50"
            ""
            "0, minimum amount of free ram not required"
            "-1, agent ram is exclusive for a task from this job")

    ram_warning = db.Column(
        db.Integer,
        nullable=True,
        doc="Amount of ram used by a task before a warning raised. "
            "A task exceeding this value will not  cause any work "
            "stopping behavior.")

    ram_max = db.Column(
        db.Integer,
        nullable=True,
        doc="Maximum amount of ram a task is allowed to consume on "
            "an agent."
            ""
            ".. warning:: "
            "   If set, the task will be **terminated** if the ram in "
            "   use by the process exceeds this value.")

    hidden = db.Column(
        db.Boolean,
        default=False, nullable=False,
        doc="If True, keep the job hidden from the queue and web "
            "ui.  This is typically set to True if you either want "
            "to save a job for later viewing or if the jobs data "
            "is being populated in a deferred manner.")

    environ = db.Column(
        JSONDict,
        doc="Dictionary containing information about the environment "
            "in which the job will execute. "
            ""
            ".. note::"
            "    Changes made directly to this object are **not** "
            "    applied to the session.")

    data = db.Column(
        JSONDict,
        doc="Json blob containing additional data for a job "
            ""
            ".. note:: "
            "   Changes made directly to this object are **not** "
            "   applied to the session.")

    to_be_deleted = db.Column(
        db.Boolean,
        nullable=False, default=False,
        doc="If true, the master will stop all running tasks for "
            "this job and then delete it.")

    completion_notify_sent = db.Column(
        db.Boolean,
        nullable=False, default=False,
        doc="Whether or not the finish notification mail has already "
            "been sent out.")

    autodelete_time = db.Column(
        db.Integer,
        nullable=True, default=None,
        doc="If not None, this job will be automatically deleted this "
            "number of seconds after it finishes.")

    #
    # Relationships
    #

    queue = db.relationship(
        "JobQueue",
        backref=db.backref("jobs", lazy="dynamic"),
        doc="The queue for this job")

    group = db.relationship(
        "JobGroup",
        backref=db.backref("jobs", lazy="dynamic"),
        doc="The job group this job belongs to")

    user = db.relationship(
        "User",
        backref=db.backref("jobs", lazy="dynamic"),
        doc="The owner of this job")

    # self-referential many-to-many relationship
    parents = db.relationship(
        "Job",
        secondary=JobDependency,
        primaryjoin=id==JobDependency.c.childid,
        secondaryjoin=id==JobDependency.c.parentid,
        backref="children")

    notified_users = db.relationship(
        "JobNotifiedUser",
        lazy="dynamic",
        backref=db.backref("job"),
        cascade="all,delete")

    tasks_queued = db.relationship(
        "Task",
        lazy="dynamic",
        primaryjoin="(Task.state == None) & "
                    "(Task.job_id == Job.id)",
        doc="Relationship between this job and any :class:`Task` "
            "objects which are queued.")

    tasks_running = db.relationship(
        "Task",
        lazy="dynamic",
        primaryjoin="(Task.state == %s) & "
                    "(Task.job_id == Job.id)" % DBWorkState.RUNNING,
        doc="Relationship between this job and any :class:`Task` "
            "objects which are running.")

    tasks_done = db.relationship("Task", lazy="dynamic",
        primaryjoin="(Task.state == %s) & "
                    "(Task.job_id == Job.id)" % DBWorkState.DONE,
        doc="Relationship between this job and any :class:`Task` objects "
            "which are done.")

    tasks_failed = db.relationship("Task", lazy="dynamic",
        primaryjoin="(Task.state == %s) & "
                    "(Task.job_id == Job.id)" % DBWorkState.FAILED,
        doc="Relationship between this job and any :class:`Task` objects "
            "which have failed.")

    # resource relationships
    tags = db.relationship(
        "Tag",
        backref="jobs", lazy="dynamic",
        secondary=JobTagAssociation,
        doc="Relationship between this job and :class:`.Tag` objects")

    def paused(self):
        return self.state == WorkState.PAUSED

    def update_state(self):
        # Import here instead of at the top of the file to avoid a circular
        # import
        from pyfarm.scheduler.tasks import send_job_completion_mail

        num_active_tasks = db.session.query(Task).\
            filter(Task.job == self,
                   or_(Task.state == None, and_(
                            Task.state != WorkState.DONE,
                            Task.state != WorkState.FAILED))).count()
        if num_active_tasks == 0:
            num_failed_tasks = db.session.query(Task).filter(
                Task.job == self,
                Task.state == WorkState.FAILED).count()
            if num_failed_tasks == 0:
                if self.state != _WorkState.DONE:
                    logger.info("Job %r (id %s): state transition %r -> 'done'",
                                self.title, self.id, self.state)
                    self.state = WorkState.DONE
                    send_job_completion_mail.apply_async(args=[self.id, True],
                                                         countdown=5)
            else:
                if self.state != _WorkState.FAILED:
                    logger.info("Job %r (id %s): state transition %r -> "
                                "'failed'",
                                self.title, self.id, self.state)
                    self.state = WorkState.FAILED
                    send_job_completion_mail.apply_async(args=[self.id, False],
                                                         countdown=5)
            db.session.add(self)
        elif self.state != _WorkState.PAUSED:
            num_running_tasks = db.session.query(Task).\
                filter(Task.job == self,
                       Task.agent_id != None,
                       or_(
                            Task.state == WorkState.RUNNING,
                            Task.state == None)).count()
            if num_running_tasks == 0:
                logger.debug("No running tasks in job %s (id %s), setting it "
                             "to queued", self.title, self.id)
                self.state = None
                db.session.add(self)

    # Methods used by the scheduler
    def num_assigned_agents(self):
        # Import here instead of at the top of the file to avoid circular import
        from pyfarm.models.agent import Agent

        # Optimization: Blindly assume that we have no agents assigned if not
        # running
        if self.state != _WorkState.RUNNING:
            return 0

        try:
            return self.assigned_agents_count
        except AttributeError:
            self.assigned_agents_count =\
                db.session.query(distinct(Task.agent_id)).\
                    filter(Task.job == self,
                           Task.agent_id != None,
                           or_(Task.state == None,
                               Task.state == WorkState.RUNNING),
                           Task.agent.has(Agent.state != AgentState.OFFLINE))\
                               .count()

            return self.assigned_agents_count

    def clear_assigned_counts(self):
        try:
            del self.assigned_agents_count
        except AttributeError:
            pass
        if self.queue:
            self.queue.clear_assigned_counts()

    def can_use_more_agents(self):
        # Import here instead of at the top of the file to avoid circular import
        from pyfarm.models.agent import Agent

        unassigned_tasks = Task.query.filter(
            Task.job == self,
            or_(Task.state == None,
                ~Task.state.in_([WorkState.DONE, WorkState.FAILED])),
            or_(Task.agent == None,
                Task.agent.has(Agent.state.in_(
                    [AgentState.OFFLINE, AgentState.DISABLED])))).count()

        return unassigned_tasks > 0

    def get_batch(self):
        # Import here instead of at the top of the file to avoid circular import
        from pyfarm.models.agent import Agent

        tasks_query = Task.query.filter(
            Task.job == self,
            or_(Task.state == None,
                ~Task.state.in_([WorkState.DONE, WorkState.FAILED])),
            or_(Task.agent == None,
                Task.agent.has(Agent.state.in_(
                    [AgentState.OFFLINE, AgentState.DISABLED])))).\
                        order_by("frame asc")

        batch = []
        for task in tasks_query:
            if (len(batch) < self.batch and
                len(batch) < (self.jobtype_version.max_batch or maxsize) and
                (not self.jobtype_version.batch_contiguous or
                 (len(batch) == 0 or
                  batch[-1].frame + self.by == task.frame))):
                batch.append(task)

        return batch

    def alter_frame_range(self, start, end, by):
        # We have to import this down here instead of at the top to break a
        # circular dependency between the modules
        from pyfarm.scheduler.tasks import delete_task

        if end < start:
            raise ValueError("`end` must be greater than or equal to `start`")

        self.by = by

        required_frames = []
        current_frame = start
        while current_frame <= end:
            required_frames.append(current_frame)
            current_frame += by

        existing_tasks = Task.query.filter_by(job=self).all()
        frames_to_create = required_frames
        for task in existing_tasks:
            if task.frame not in required_frames:
                delete_task.delay(task.id)
            else:
                frames_to_create.remove(task.frame)

        for frame in frames_to_create:
            task = Task()
            task.job = self
            task.frame = frame
            task.priority = self.priority
            db.session.add(task)

        if frames_to_create:
            if self.state != WorkState.RUNNING:
                self.state = None

    def rerun(self):
        """
        Makes this job rerun all its task.  Tasks that are currently running are
        left untouched.
        """
        running_tasks = False
        for task in self.tasks:
            if task.state != _WorkState.RUNNING and task.state is not None:
                task.state = None
                task.agent = None
                task.failures = 0
                db.session.add(task)
            elif task.state == _WorkState.RUNNING or task.agent is not None:
                running_tasks = True

        if not running_tasks:
            self.state = None
        else:
            self.state = WorkState.RUNNING
        self.completion_notify_sent = False
        db.session.add(self)

        for child in self.children:
            child.rerun()

    def rerun_failed(self):
        """
        Makes this job rerun all its failed tasks.  Tasks that are done or are
        currently running are left untouched
        """
        running_tasks = False
        for task in self.tasks:
            if task.state == _WorkState.FAILED:
                task.state = None
                task.agent = None
                task.failures = 0
                db.session.add(task)
            elif (task.state == _WorkState.RUNNING or
                  task.state is None and task.agent is not None):
                running_tasks = True

        if not running_tasks:
            self.state = None
        self.completion_notify_sent = False
        db.session.add(self)

        for child in self.children:
            child.rerun_failed()

    @validates("ram", "cpus")
    def validate_resource(self, key, value):
        """
        Validation that ensures that the value provided for either
        :attr:`.ram` or :attr:`.cpus` is a valid value with a given range
        """
        assert isinstance(value, int), "%s must be an integer" % key
        min_value = config.get("agent_min_%s" % key)
        max_value = config.get("agent_max_%s" % key)

        # check the provided input
        if min_value > value or value > max_value:
            msg = "value for `%s` must be between " % key
            msg += "%s and %s" % (min_value, max_value)
            raise ValueError(msg)

        return value

    @validates("progress")
    def validate_progress(self, key, value):
        if value < 0.0 or value > 1.0:
            raise ValueError("Progress must be between 0.0 and 1.0")

event.listen(Job.state, "set", Job.state_changed)
