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


from textwrap import dedent
from sys import maxsize

from sqlalchemy import event, distinct, or_, and_
from sqlalchemy.orm import validates
from sqlalchemy.schema import UniqueConstraint

from pyfarm.core.logger import getLogger
from pyfarm.core.config import read_env, read_env_int
from pyfarm.core.enums import WorkState, DBWorkState, _WorkState, AgentState
from pyfarm.master.application import db
from pyfarm.models.core.functions import work_columns
from pyfarm.models.core.types import JSONDict, JSONList, IDTypeWork
from pyfarm.models.core.cfg import (
    TABLE_JOB, TABLE_JOB_TYPE_VERSION, TABLE_TAG,
    TABLE_JOB_TAG_ASSOC, MAX_COMMAND_LENGTH, MAX_USERNAME_LENGTH,
    MAX_JOBTITLE_LENGTH, TABLE_JOB_DEPENDENCY, TABLE_JOB_QUEUE,
    TABLE_USER, TABLE_JOB_NOTIFIED_USER)
from pyfarm.models.core.mixins import (
    ValidatePriorityMixin, WorkStateChangedMixin, ReprMixin,
    ValidateWorkStateMixin, UtilityMixins)
from pyfarm.models.jobtype import JobType, JobTypeVersion
from pyfarm.models.task import Task

__all__ = ("Job", )

logger = getLogger("models.job")


JobTagAssociation = db.Table(
    TABLE_JOB_TAG_ASSOC, db.metadata,
    db.Column("job_id", IDTypeWork,
              db.ForeignKey("%s.id" % TABLE_JOB), primary_key=True),
    db.Column("tag_id", db.Integer,
              db.ForeignKey("%s.id" % TABLE_TAG), primary_key=True))


JobDependency = db.Table(
    TABLE_JOB_DEPENDENCY, db.metadata,
    db.Column("parentid", IDTypeWork,
              db.ForeignKey("%s.id" % TABLE_JOB), primary_key=True),
    db.Column("childid", IDTypeWork,
              db.ForeignKey("%s.id" % TABLE_JOB), primary_key=True))


class JobNotifiedUser(db.Model):
    __tablename__ = TABLE_JOB_NOTIFIED_USER
    user_id = db.Column(db.Integer, db.ForeignKey("%s.id" % TABLE_USER),
                        primary_key=True)
    job_id = db.Column(IDTypeWork, db.ForeignKey("%s.id" % TABLE_JOB),
                       primary_key=True)
    on_success = db.Column(db.Boolean, nullable=False, default=True)
    on_failure = db.Column(db.Boolean, nullable=False, default=True)
    on_deletion = db.Column(db.Boolean, nullable=False, default=False)
    user = db.relationship("User", backref=db.backref("subscribed_jobs",
                                                      lazy="dynamic"))



class Job(db.Model, ValidatePriorityMixin, ValidateWorkStateMixin,
          WorkStateChangedMixin, ReprMixin, UtilityMixins):
    """
    Defines the attributes and environment for a job.  Individual commands
    are kept track of by :class:`Task`
    """
    __tablename__ = TABLE_JOB
    REPR_COLUMNS = ("id", "state", "project")
    REPR_CONVERT_COLUMN = {
        "state": repr}
    STATE_ENUM = list(WorkState) + [None]
    MIN_CPUS = read_env_int("PYFARM_QUEUE_MIN_CPUS", 1)
    MAX_CPUS = read_env_int("PYFARM_QUEUE_MAX_CPUS", 256)
    MIN_RAM = read_env_int("PYFARM_QUEUE_MIN_RAM", 16)
    MAX_RAM = read_env_int("PYFARM_QUEUE_MAX_RAM", 262144)
    SPECIAL_RAM = read_env("PYFARM_AGENT_SPECIAL_RAM", [0], eval_literal=True)
    SPECIAL_CPUS = read_env("PYFARM_AGENT_SPECIAL_CPUS", [0], eval_literal=True)

    # quick check of the configured data
    assert MIN_CPUS >= 1, "$PYFARM_QUEUE_MIN_CPUS must be > 0"
    assert MAX_CPUS >= 1, "$PYFARM_QUEUE_MAX_CPUS must be > 0"
    assert MAX_CPUS >= MIN_CPUS, "MIN_CPUS must be <= MAX_CPUS"
    assert MIN_RAM >= 1, "$PYFARM_QUEUE_MIN_RAM must be > 0"
    assert MAX_RAM >= 1, "$PYFARM_QUEUE_MAX_RAM must be > 0"
    assert MAX_RAM >= MIN_RAM, "MIN_RAM must be <= MAX_RAM"


    # shared work columns
    id, state, priority, time_submitted, time_started, time_finished = \
        work_columns(None, "job.priority")
    jobtype_version_id = db.Column(IDTypeWork,
                                    db.ForeignKey("%s.id"
                                        % TABLE_JOB_TYPE_VERSION),
                                    nullable=False,
                                    doc=dedent("""
                                    The foreign key which stores
                                    :class:`JobTypeVersion.id`"""))
    job_queue_id = db.Column(IDTypeWork,
                             db.ForeignKey("%s.id" % TABLE_JOB_QUEUE),
                             nullable=True,
                             doc=dedent("""
                                The foreign key which stores
                                :class:`JobQueue.id`"""))
    user_id = db.Column(db.Integer, db.ForeignKey("%s.id" % TABLE_USER),
                        doc="The id of the user who owns this job")
    minimum_agents = db.Column(db.Integer, nullable=True,
                          doc=dedent("""
                          The scheduler will try to assign at least this number
                          of agents to this job as long as it can use them,
                          before any other considerations."""))
    maximum_agents = db.Column(db.Integer, nullable=True,
                          doc=dedent("""
                          The scheduler will never assign more than this number
                          of agents to this job."""))
    weight = db.Column(db.Integer, nullable=False,
                       default=read_env_int(
                                   "PYFARM_QUEUE_DEFAULT_WEIGHT", 10),
                       doc=dedent("""
                            The weight of this job.
                            The scheduler will distribute available agents
                            between jobs and job queues in the same queue
                            in proportion to their weights.
                            """))
    title = db.Column(db.String(MAX_JOBTITLE_LENGTH), nullable=False,
                      doc="The title of this job")
    notes = db.Column(db.Text, default="",
                      doc=dedent("""
                      Notes that are provided on submission or added after
                      the fact. This column is only provided for human
                      consumption, is not scanned, index, or used when
                      searching"""))

    output_link = db.Column(db.Text, nullable=True,
                            doc="An optional link to a URI where this job's "
                                "output can be viewed.")

    # task data
    by = db.Column(db.Numeric(10, 4), default=1,
                   doc=dedent("""
                   The number of frames to count by between `start` and
                   `end`.  This column may also sometimes be referred to
                   as 'step' by other software."""))
    batch = db.Column(db.Integer,
                      default=read_env_int("PYFARM_QUEUE_DEFAULT_BATCH", 1),
                      doc=dedent("""
                      Number of tasks to run on a single agent at once.
                      Depending on the capabilities of the software being run
                      this will either cause a single process to execute on
                      the agent or multiple processes one after the other.

                      **configured by**: `job.batch`"""))
    requeue = db.Column(db.Integer,
                        default=read_env_int("PYFARM_QUEUE_DEFAULT_REQUEUE", 3),
                        doc=dedent("""
                        Number of times to requeue failed tasks

                        .. csv-table:: **Special Values**
                            :header: Value, Result
                            :widths: 10, 50

                            0, never requeue failed tasks
                            -1, requeue failed tasks indefinitely

                        **configured by**: `job.requeue`"""))
    cpus = db.Column(db.Integer,
                     default=read_env_int("PYFARM_QUEUE_DEFAULT_CPUS", 1),
                     doc=dedent("""
                     Number of cpus or threads each task should consume on
                     each agent.  Depending on the job type being executed
                     this may result in additional cpu consumption, longer
                     wait times in the queue (2 cpus means 2 'fewer' cpus on
                     an agent), or all of the above.

                     .. csv-table:: **Special Values**
                        :header: Value, Result
                        :widths: 10, 50

                        0, minimum number of cpu resources not required
                        -1, agent cpu is exclusive for a task from this job

                     **configured by**: `job.cpus`"""))
    ram = db.Column(db.Integer,
                    default=read_env_int("PYFARM_QUEUE_DEFAULT_RAM", 32),
                    doc=dedent("""
                    Amount of ram a task from this job will require to be
                    free in order to run.  A task exceeding this value will
                    not result in any special behavior.

                    .. csv-table:: **Special Values**
                        :header: Value, Result
                        :widths: 10, 50

                        0, minimum amount of free ram not required
                        -1, agent ram is exclusive for a task from this job

                    **configured by**: `job.ram`"""))
    ram_warning = db.Column(db.Integer, nullable=True,
                            doc=dedent("""
                            Amount of ram used by a task before a warning raised.
                            A task exceeding this value will not  cause any work
                            stopping behavior."""))
    ram_max = db.Column(db.Integer, nullable=True,
                        doc=dedent("""
                        Maximum amount of ram a task is allowed to consume on
                        an agent.

                        .. warning::
                            If set, the task will be **terminated** if the ram in
                            use by the process exceeds this value.
                        """))
    hidden = db.Column(db.Boolean, default=False, nullable=False,
                       doc=dedent("""
                       If True, keep the job hidden from the queue and web
                       ui.  This is typically set to True if you either want
                       to save a job for later viewing or if the jobs data
                       is being populated in a deferred manner."""))
    environ = db.Column(JSONDict,
                        doc=dedent("""
                        Dictionary containing information about the environment
                        in which the job will execute.

                        .. note::
                            Changes made directly to this object are **not**
                            applied to the session."""))
    data = db.Column(JSONDict,
                     doc=dedent("""
                     Json blob containing additional data for a job

                     .. note::
                        Changes made directly to this object are **not**
                        applied to the session."""))

    to_be_deleted = db.Column(db.Boolean, nullable=False, default=False,
                              doc="If true, the master will stop all running "
                                  "tasks for this job and then delete it.")

    autodelete_time = db.Column(db.Integer, nullable=True, default=None,
                                doc="If not None, this job will be "
                                    "automatically deleted this number of "
                                    "seconds after it finishes.")

    queue = db.relationship("JobQueue",
                            backref=db.backref("jobs", lazy="dynamic"),
                            doc="The queue for this job")

    user = db.relationship("User",
                           backref=db.backref("jobs", lazy="dynamic"),
                           doc="The owner of this job")

    # self-referential many-to-many relationship
    parents = db.relationship("Job",
                              secondary=JobDependency,
                              primaryjoin=id==JobDependency.c.childid,
                              secondaryjoin=id==JobDependency.c.parentid,
                              backref="children")

    notified_users = db.relationship("JobNotifiedUser", lazy="dynamic",
                                     backref=db.backref("job"),
                                     cascade="all,delete")

    tasks_queued = db.relationship("Task", lazy="dynamic",
        primaryjoin="(Task.state == None) & "
                    "(Task.job_id == Job.id)",
        doc=dedent("""
        Relationship between this job and any :class:`Task` objects which are
        queued."""))

    tasks_running = db.relationship("Task", lazy="dynamic",
        primaryjoin="(Task.state == %s) & "
                    "(Task.job_id == Job.id)" % DBWorkState.RUNNING,
        doc=dedent("""
        Relationship between this job and any :class:`Task` objects which are
        running."""))

    tasks_done = db.relationship("Task", lazy="dynamic",
        primaryjoin="(Task.state == %s) & "
                    "(Task.job_id == Job.id)" % DBWorkState.DONE,
        doc=dedent("""
        Relationship between this job and any :class:`Task` objects which are
        done."""))

    tasks_failed = db.relationship("Task", lazy="dynamic",
        primaryjoin="(Task.state == %s) & "
                    "(Task.job_id == Job.id)" % DBWorkState.FAILED,
        doc=dedent("""
        Relationship between this job and any :class:`Task` objects which have
        failed."""))

    # resource relationships
    tags = db.relationship("Tag", backref="jobs", lazy="dynamic",
                           secondary=JobTagAssociation,
                           doc=dedent("""
                           Relationship between this job and
                           :class:`.Tag` objects"""))

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
                    logger.info("Job %r: state transition %r -> 'done'",
                                self.title, self.state)
                    self.state = WorkState.DONE
                    send_job_completion_mail.apply_async(args=[self.id, True],
                                                         countdown=5)
            else:
                if self.state != _WorkState.FAILED:
                    logger.info("Job %r: state transition %r -> 'failed'",
                                self.title, self.state)
                    self.state = WorkState.FAILED
                    send_job_completion_mail.apply_async(args=[self.id, False],
                                                         countdown=5)
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

    @validates("ram", "cpus")
    def validate_resource(self, key, value):
        """
        Validation that ensures that the value provided for either
        :attr:`.ram` or :attr:`.cpus` is a valid value with a given range
        """
        key_upper = key.upper()
        special = getattr(self, "SPECIAL_%s" % key_upper)

        if value is None or value in special:
            return value

        min_value = getattr(self, "MIN_%s" % key_upper)
        max_value = getattr(self, "MAX_%s" % key_upper)

        # quick sanity check of the incoming config
        assert isinstance(min_value, int), "db.min_%s must be an integer" % key
        assert isinstance(max_value, int), "db.max_%s must be an integer" % key
        assert min_value >= 1, "db.min_%s must be > 0" % key
        assert max_value >= 1, "db.max_%s must be > 0" % key

        # check the provided input
        if min_value > value or value > max_value:
            msg = "value for `%s` must be between " % key
            msg += "%s and %s" % (min_value, max_value)
            raise ValueError(msg)

        return value

event.listen(Job.state, "set", Job.state_changed)
