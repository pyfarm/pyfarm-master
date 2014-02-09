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

from pyfarm.core.config import read_env, read_env_int
from pyfarm.core.enums import WorkState, DBWorkState
from pyfarm.master.application import db
from pyfarm.models.core.functions import work_columns
from pyfarm.models.core.types import JSONDict, JSONList, IDTypeWork
from pyfarm.models.core.cfg import (
    TABLE_JOB, TABLE_JOB_TYPE, TABLE_TAG,
    TABLE_JOB_TAG_ASSOC, MAX_COMMAND_LENGTH, MAX_USERNAME_LENGTH,
    TABLE_JOB_DEPENDENCIES, TABLE_PROJECT)
from pyfarm.models.core.mixins import (
    ValidatePriorityMixin, WorkStateChangedMixin, ReprMixin,
    ValidateWorkStateMixin)
from pyfarm.models.jobtype import JobType  # required for a relationship

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


class Job(db.Model, ValidatePriorityMixin, ValidateWorkStateMixin,
          WorkStateChangedMixin, ReprMixin):
    """
    Defines the attributes and environment for a job.  Individual commands
    are kept track of by :class:`Task`
    """
    __tablename__ = TABLE_JOB
    REPR_COLUMNS = ("id", "state", "project")
    REPR_CONVERT_COLUMN = {
        "state": repr}
    STATE_ENUM = WorkState
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
        work_columns(WorkState.QUEUED, "job.priority")
    project_id = db.Column(db.Integer, db.ForeignKey("%s.id" % TABLE_PROJECT),
                           doc="stores the project id")
    job_type_id = db.Column(IDTypeWork, db.ForeignKey("%s.id" % TABLE_JOB_TYPE),
                            nullable=False,
                            doc=dedent("""
                            The foreign key which stores :class:`JobType.id`"""))
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
    cmd = db.Column(db.String(MAX_COMMAND_LENGTH),
                    doc=dedent("""
                    The platform independent command to run. Each agent will
                    resolve this value for itself when the task begins so a
                    command like `ping` will work on any platform it's
                    assigned to.  The full command could be provided here,
                    but then the job must be tagged using
                    :class:`.JobSoftware` to limit which agent(s) it will
                    run on."""))
    start = db.Column(db.Float,
                      doc=dedent("""
                      The first frame of the job to run.  This value may
                      be a float so subframes can be processed."""))
    end = db.Column(db.Float,
                      doc=dedent("""
                      The last frame of the job to run.  This value may
                      be a float so subframes can be processed."""))
    by = db.Column(db.Float, default=1,
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
                      the agent or multiple processes on after the other.

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
    ram_warning = db.Column(db.Integer, default=-1,
                            doc=dedent("""
                            Amount of ram used by a task before a warning
                            raised.  A task exceeding this value will not
                            cause any work stopping behavior.

                            .. csv-table:: **Special Values**
                                :header: Value, Result
                                :widths: 10, 50

                                -1, not set"""))
    ram_max = db.Column(db.Integer, default=-1,
                        doc=dedent("""
                        Maximum amount of ram a task is allowed to consume on
                        an agent.

                        .. warning::
                            The task will be **terminated** if the ram in use
                            by the process exceeds this value.

                        .. csv-table:: **Special Values**
                            :header: Value, Result
                            :widths: 10, 50

                            -1, not set
                        """))
    attempts = db.Column(db.Integer,
                         doc=dedent("""
                         The number attempts which have been made on this
                         task. This value is auto incremented when
                         :attr:`state` changes to a value synonyms with a
                         running state."""))
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
    args = db.Column(JSONList,
                     doc=dedent("""
                     List containing the command line arguments.

                     .. note::
                        Changes made directly to this object are **not**
                        applied to the session."""))
    data = db.Column(JSONDict,
                     doc=dedent("""
                     Json blob containing additional data for a job

                     .. note::
                        Changes made directly to this object are **not**
                        applied to the session."""))

    project = db.relationship("Project",
                              backref=db.backref("jobs", lazy="dynamic"),
                              doc=dedent("""
                              relationship attribute which retrieves the
                              associated project for the job"""))

    # self-referential many-to-many relationship
    parents = db.relationship("Job",
                              secondary=JobDependencies,
                              primaryjoin=id==JobDependencies.c.parentid,
                              secondaryjoin=id==JobDependencies.c.childid,
                              backref="children")

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

    tasks_queued = db.relationship("Task", lazy="dynamic",
        primaryjoin="(Task.state == %s) & "
                    "(Task.job_id == Job.id)" % DBWorkState.QUEUED,
        doc=dedent("""
        Relationship between this job and any :class:`Task` objects which
        are queued."""))

    # resource relationships
    tags = db.relationship("Tag", backref="jobs", lazy="dynamic",
                           secondary=JobTagAssociation,
                           doc=dedent("""
                           Relationship between this job and
                           :class:`.Tag` objects"""))

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

event.listen(Job.state, "set", Job.stateChangedEvent)
