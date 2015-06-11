# No shebang line, this module is meant to be imported
#
# Copyright 2013 Oliver Palmer
# Copyright 2014 Ambient Entertainment GmbH & Co. KG
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
Job Type Models
===============

Models and objects dedicated to handling information which is specific
to an individual job.  See :mod:`pyfarm.models.job` for more the more
general implementation.
"""

from sqlalchemy.orm import validates
from sqlalchemy.schema import UniqueConstraint

from pyfarm.core.logger import getLogger
from pyfarm.master.application import db
from pyfarm.master.config import config
from pyfarm.models.core.mixins import UtilityMixins, ReprMixin
from pyfarm.models.core.types import id_column, IDTypeWork


__all__ = ("JobType", )

logger = getLogger("models.jobtype")


class JobType(db.Model, UtilityMixins, ReprMixin):
    """
    Stores the unique information necessary to execute a task
    """
    __tablename__ = config.get("table_job_type")
    __table_args__ = (UniqueConstraint("name"),)
    REPR_COLUMNS = ("id", "name")

    id = id_column(IDTypeWork)

    name = db.Column(
        db.String(config.get("job_type_max_name_length")),
        nullable=False,
        doc="The name of the job type.  This can be either a human "
            "readable name or the name of the job type class itself.")

    description = db.Column(
        db.Text,
        nullable=True,
        doc="Human readable description of the job type.  This field is not "
            "required and is not directly relied upon anywhere.")

    success_subject = db.Column(
        db.Text,
        nullable=True,
        doc="The subject line to use for notifications in case of "
            "success.  Some substitutions, for example for the job title, "
            "are available.")

    success_body = db.Column(
        db.Text,
        nullable=True,
        doc="The email body to use for notifications in "
            "in case of success.  Some substitutions, for "
            "example for the job title, are available.")

    fail_subject = db.Column(
        db.Text,
        nullable=True,
        doc="The subject line to use for notifications "
            "in case of failure.  Some substitutions, for "
            "example for the job title, are available.")

    fail_body = db.Column(
        db.Text,
        nullable=True,
        doc="The email body to use for notifications in "
            "in case of success.  Some substitutions, for "
            "example for the job title, are available.")

    @validates("name")
    def validate_name(self, key, value):
        if value == "":
            raise ValueError("Name cannot be empty")

        return value


class JobTypeVersion(db.Model, UtilityMixins, ReprMixin):
    """
    Defines a specific jobtype version.
    """
    __tablename__ = config.get("table_job_type_version")
    __table_args__ = (UniqueConstraint("jobtype_id", "version"),)

    REPR_COLUMNS = ("id", "jobtype_id", "version")

    id = id_column(IDTypeWork)

    jobtype_id = db.Column(
        IDTypeWork,
        db.ForeignKey("%s.id" % config.get("table_job_type")),
        nullable=False,
        doc="The jobtype this version belongs to")

    version = db.Column(
        db.Integer,
        nullable=False,
        doc="The version number")

    max_batch = db.Column(
        db.Integer,
        default=config.get("job_type_max_batch"),
        doc="When the queue runs, this is the maximum number of tasks "
            "that the queue can select to assign to a single"
            "agent.  If left empty, no maximum applies")

    batch_contiguous = db.Column(
        db.Boolean,
        default=config.get("job_type_batch_contiguous"),
        doc="If True then the queue will be forced to batch"
            "numerically contiguous tasks only for this job type.  "
            "For example if True it would batch frames 1, 2, 3, 4 "
            "together but not 2, 4, 6, 8.  If this column is False "
            "however the queue will batch non-contiguous tasks too.")

    classname = db.Column(
        db.String(config.get("job_type_max_class_name_length")),
        nullable=True,
        doc="The name of the job class contained within the file being "
            "loaded.  This field may be null but when it's not provided "
            "job type name will be used instead.")

    code = db.Column(
        db.UnicodeText,
        nullable=False,
        doc="The source code of the job type")

    #
    # Relationships
    #
    jobtype = db.relationship(
        "JobType",
        backref=db.backref(
            "versions", lazy="dynamic", cascade="all, delete-orphan"),
        doc="Relationship between this version and the "
            ":class:`JobType` it belongs to""")

    jobs = db.relationship(
        "Job", backref="jobtype_version", lazy="dynamic",
        doc="Relationship between this jobtype version and "
            ":class:`.Job` objects.")

    @validates("max_batch")
    def validate_max_batch(self, key, value):
        if isinstance(value, int) and value < 1:
            raise ValueError("max_batch must be greater than or equal to 1")

        return value

    @validates("version")
    def validate_version(self, key, value):
        if isinstance(value, int) and value < 1:
            raise ValueError("version must be greater than or equal to 1")

        return value
