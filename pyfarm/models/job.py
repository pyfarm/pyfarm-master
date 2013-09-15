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

.. include:: ../include/references.rst
"""

try:
    import pwd
except ImportError:  # pragma: no cover
    pwd = None

try:
    import json
except ImportError:  # pragma: no cover
    import simplejson as json

from textwrap import dedent
from sqlalchemy import event
from sqlalchemy.exc import DatabaseError
from sqlalchemy.orm import validates
from sqlalchemy.schema import UniqueConstraint
from pyfarm.core.config import cfg
from pyfarm.models.core.app import db
from pyfarm.core.enums import WorkState
from pyfarm.models.core.functions import WorkColumns
from pyfarm.models.core.types import IDColumn, JSONDict, JSONList, IDTypeWork
from pyfarm.models.core.cfg import (
    TABLE_JOB, TABLE_JOB_TAGS, TABLE_JOB_SOFTWARE,
    MAX_COMMAND_LENGTH, MAX_TAG_LENGTH, MAX_USERNAME_LENGTH)
from pyfarm.models.core.mixins import WorkValidationMixin, StateChangedMixin
from pyfarm.models.jobtype import JobTypeModel  # relationship import


class JobTagsModel(db.Model):
    """
    Model which provides tagging for :class:`.JobModel` objects

    .. note::
        This table enforces two forms of uniqueness.  The :attr:`id` column
        must be unique and the combination of these columns must also be
        unique to limit the frequency of duplicate data:

            * :attr:`jobid`
            * :attr:`tag`

    .. autoattribute:: jobid
    """
    __tablename__ = TABLE_JOB_TAGS
    __table_args__ = (
        UniqueConstraint("jobid", "tag"), )

    id = IDColumn()
    jobid = db.Column(IDTypeWork, db.ForeignKey("%s.id" % TABLE_JOB),
                       nullable=False,
                       doc=dedent("""
                       Foreign key which stores :attr:`JobModel.id`"""))

    tag = db.Column(db.String(MAX_TAG_LENGTH), nullable=False)


class JobSoftwareModel(db.Model):
    """
    Model which allows specific software to be associated with a
    :class:`.JobModel` object.

    .. note::
        This table enforces two forms of uniqueness.  The :attr:`id` column
        must be unique and the combination of these columns must also be
        unique to limit the frequency of duplicate data:

            * :attr:`jobid`
            * :attr:`software`
            * :attr:`version`

    .. autoattribute:: jobid
    """
    __tablename__ = TABLE_JOB_SOFTWARE
    __table_args__ = (
        UniqueConstraint("jobid", "software", "version"), )

    id = IDColumn()
    jobid = db.Column(IDTypeWork, db.ForeignKey("%s.id" % TABLE_JOB),
                       nullable=False,
                       doc=dedent("""
                       The foreign key which stores :attr:`JobModel.id`"""))
    software = db.Column(db.String(MAX_TAG_LENGTH), nullable=False,
                         doc=dedent("""
                         The name of the software required to run a job"""))
    version = db.Column(db.String(MAX_TAG_LENGTH),
                        default="any", nullable=False,
                        doc=dedent("""
                        The version of software required to run the job.  This
                        value does not follow any special formatting rules
                        because the format depends on the 3rd party."""))


class JobModel(db.Model, WorkValidationMixin, StateChangedMixin):
    """
    Defines the attributes and environment for a job.  Individual commands
    are kept track of by |TaskModel|
    """
    __tablename__ = TABLE_JOB
    STATE_ENUM = WorkState

    # shared work columns
    id, state, priority, time_submitted, time_started, time_finished = \
        WorkColumns(STATE_ENUM.QUEUED, "job.priority")
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
                      consumption is not scanned, index, or used when
                      searching"""))

    # task data
    cmd = db.Column(db.String(MAX_COMMAND_LENGTH),
                    doc=dedent("""
                    The platform independent command to run. Each agent will
                    resolve this value for itself when the task begins so a
                    command like `ping` will work on any platform it's
                    assigned to.  The full commend could be provided here,
                    but then the job must be tagged using
                    :class:`.JobSoftwareModel` to limit which agent(s) it will
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
    batch = db.Column(db.Integer, default=lambda: cfg.get("job.batch", 1),
                      doc=dedent("""
                      Number of tasks to run on a single agent at once.
                      Depending on the capabilities of the software being run
                      this will either cause a single process to execute on
                      the agent or multiple processes on after the other.

                      **configured by**: `job.batch`"""))
    requeue = db.Column(db.Integer, default=lambda: cfg.get("job.requeue", 1),
                        doc=dedent("""
                        Number of times to requeue failed tasks

                        .. csv-table:: **Special Values**
                            :header: Value, Result
                            :widths: 10, 50

                            0, never requeue failed tasks
                            -1, requeue failed tasks indefinitely

                        **configured by**: `job.requeue`"""))
    cpus = db.Column(db.Integer, default=lambda: cfg.get("job.cpus", 0),
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
    ram = db.Column(db.Integer, default=lambda: cfg.get("job.ram", 0),
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

    # relationships
    parentid = db.Column(IDTypeWork, db.ForeignKey("%s.id" % TABLE_JOB))
    parent = db.relationship("JobModel", remote_side=[id],
                             doc=dedent("""
                             Relationship to the parent job, if one exists"""))
    
    tasks = db.relationship("TaskModel", backref="job", lazy="dynamic",
                            doc=dedent("""
                            Relationship between this job and and child
                            |TaskModel| objects
                            """))

    tasks_done = db.relationship("TaskModel", lazy="dynamic",
        primaryjoin="(TaskModel.state == %s) & "
                    "(TaskModel.jobid == JobModel.id)" % STATE_ENUM.DONE,
        doc=dedent("""
        Relationship between this job and any |TaskModel| objects which are
        done."""))

    tasks_failed = db.relationship("TaskModel", lazy="dynamic",
        primaryjoin="(TaskModel.state == %s) & "
                    "(TaskModel.jobid == JobModel.id)" % STATE_ENUM.FAILED,
        doc=dedent("""
        Relationship between this job and any |TaskModel| objects which have
        failed."""))

    tasks_queued = db.relationship("TaskModel", lazy="dynamic",
        primaryjoin="(TaskModel.state == %s) & "
                    "(TaskModel.jobid == JobModel.id)" % STATE_ENUM.QUEUED,
        doc=dedent("""
        Relationship between this job and any |TaskModel| objects which
        are queued."""))

    tags = db.relationship("JobTagsModel", backref="job", lazy="dynamic",
                           doc=dedent("""
                           Relationship between this job and
                           :class:`.JobTagsModel` objects"""))
    software = db.relationship("JobSoftwareModel", backref="job",
                               lazy="dynamic",
                               doc=dedent("""
                               Relationship between this job and
                               :class:`.JobSoftwareModel` objects"""))
    jobtype = db.relationship("JobTypeModel", backref="job", lazy="dynamic",
                              doc=dedent("""
                              Relationship between this job and
                              :class:`.JobTypeModel` objects."""))

    @validates("ram", "cpus")
    def validate_resource(self, key, value):
        """
        Validation that ensures that the value provided for either
        :attr:`.ram` or :attr:`.cpus` is a valid value with a given range
        """
        if value is None or value in cfg.get("agent.special_%s" % key, ()):
            return value

        min_value = cfg.get("agent.min_%s" % key)
        max_value = cfg.get("agent.max_%s" % key)

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


event.listen(JobModel.state, "set", JobModel.stateChangedEvent)


def getJobId():
    """
    Creates a new job without any data and inserts it into the
    database.

    :exception ValueError:
        raised if the session is dirty before trying to create
        and commit a job model
    """
    # TODO: we should create a new session instead
    if db.session.dirty:
        raise ValueError("session is dirty, cannot proceed")

    model = JobModel()
    model.state = WorkState.ALLOC
    model.hidden = True

    try:
        db.session.add(model)
        db.session.commit()

    except DatabaseError:
        db.session.rollback()
        raise

    else:
        return model.id