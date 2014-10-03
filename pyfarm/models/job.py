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

from sqlalchemy import event
from sqlalchemy.orm import validates
from sqlalchemy.schema import UniqueConstraint

from pyfarm.core.config import read_env, read_env_int
from pyfarm.core.enums import WorkState, DBWorkState
from pyfarm.master.application import db
from pyfarm.models.core.functions import work_columns
from pyfarm.models.core.types import JSONDict, JSONList, IDTypeWork
from pyfarm.models.core.cfg import (
    TABLE_JOB, TABLE_JOB_TYPE_VERSION, TABLE_TAG,
    TABLE_JOB_TAG_ASSOC, MAX_COMMAND_LENGTH, MAX_USERNAME_LENGTH,
    MAX_JOBTITLE_LENGTH, TABLE_JOB_DEPENDENCIES, TABLE_PROJECT, TABLE_JOB_QUEUE,
    TABLE_USERS_USER, TABLE_JOB_NOTIFIED_USERS)
from pyfarm.models.core.mixins import (
    ValidatePriorityMixin, WorkStateChangedMixin, ReprMixin,
    ValidateWorkStateMixin, UtilityMixins)
from pyfarm.models.jobtype import JobType, JobTypeVersion
from pyfarm.models.task import Task

__all__ = ("Job", )


JobTagAssociation = db.Table(
    TABLE_JOB_TAG_ASSOC, db.metadata,
    db.Column("job_id", IDTypeWork,
              db.ForeignKey("%s.id" % TABLE_JOB), primary_key=True),
    db.Column("tag_id", db.Integer,
              db.ForeignKey("%s.id" % TABLE_TAG), primary_key=True))


JobDependencies = db.Table(
    TABLE_JOB_DEPENDENCIES, db.metadata,
    db.Column("parentid", IDTypeWork,
              db.ForeignKey("%s.id" % TABLE_JOB), primary_key=True),
    db.Column("childid", IDTypeWork,
              db.ForeignKey("%s.id" % TABLE_JOB), primary_key=True))


JobNotifiedUsers = db.Table(
    TABLE_JOB_NOTIFIED_USERS, db.metadata,
    db.Column("user_id", db.Integer,
              db.ForeignKey("%s.id" % TABLE_USERS_USER), primary_key=True),
    db.Column("job_id", IDTypeWork,
              db.ForeignKey("%s.id" % TABLE_JOB), primary_key=True))


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
    project_id = db.Column(db.Integer, db.ForeignKey("%s.id" % TABLE_PROJECT),
                           doc="stores the project id")
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
    user = db.Column(db.String(MAX_USERNAME_LENGTH),
                     doc=dedent("""
                     The user this job should execute as.  The agent
                     process will have to be running as root on platforms
                     that support setting the user id.

                     .. note::
                        The length of this field is limited by the
                        configuration value `job.max_username_length`

                     .. warning::
                        this may not behave as expected on all platforms
                        (windows in particular)"""))
    notes = db.Column(db.Text, default="",
                      doc=dedent("""
                      Notes that are provided on submission or added after
                      the fact. This column is only provided for human
                      consumption, is not scanned, index, or used when
                      searching"""))

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

    project = db.relationship("Project",
                              backref=db.backref("jobs", lazy="dynamic"),
                              doc=dedent("""
                              relationship attribute which retrieves the
                              associated project for the job"""))

    queue = db.relationship("JobQueue",
                            backref=db.backref("jobs", lazy="dynamic"),
                            doc="The queue for this job")

    # self-referential many-to-many relationship
    parents = db.relationship("Job",
                              secondary=JobDependencies,
                              primaryjoin=id==JobDependencies.c.parentid,
                              secondaryjoin=id==JobDependencies.c.childid,
                              backref="children")

    notified_users = db.relationship("User",
                              secondary=JobNotifiedUsers,
                              lazy="dynamic",
                              backref=db.backref("subscribed_jobs",
                                                 lazy="dynamic"))

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
