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
Software Models
===============

Table of software items. Agents can reference this table to show that they
provide a given software. Jobs or jobtypes can depend on a software via the
SoftwareRequirement table
"""

from sqlalchemy.schema import UniqueConstraint

from pyfarm.master.config import config
from pyfarm.master.application import db
from pyfarm.models.core.types import id_column, IDTypeWork
from pyfarm.models.core.mixins import UtilityMixins

__all__ = ("Software", )


class Software(db.Model, UtilityMixins):
    """
    Model to represent a versioned piece of software that can be present on an
    agent and may be depended on by a job and/or jobtype through the appropriate
    SoftwareRequirement table
    """
    __tablename__ = config.get("table_software")
    __table_args__ = (
        UniqueConstraint("software"), )

    id = id_column()

    software = db.Column(
        db.String(config.get("max_tag_length")),
        nullable=False, doc="The name of the software")

    #
    # Relationships
    #
    versions = db.relationship(
        "SoftwareVersion",
        backref=db.backref("software"),
        lazy="dynamic", order_by="asc(SoftwareVersion.rank)",
        cascade="all, delete-orphan",
        doc="All known versions of this software")


class SoftwareVersion(db.Model, UtilityMixins):
    """
    Model to represent a version for a given software
    """
    __tablename__ = config.get("table_software_version")
    __table_args__ = (
        UniqueConstraint("software_id", "version"),
        UniqueConstraint("software_id", "rank"))

    id = id_column()

    software_id = db.Column(
        db.Integer,
        db.ForeignKey("%s.id" % config.get("table_software")),
        nullable=False, doc="The software this version belongs to")

    version = db.Column(
        db.String(config.get("max_tag_length")),
        default="any", nullable=False,
        doc="The version of the software.  This value does not "
            "follow any special formatting rules because the "
            "format depends on the 3rd party.")

    rank = db.Column(
        db.Integer,
        nullable=False,
        doc="The rank of this version relative to other versions of "
            "the same software. Used to determine whether a version "
            "is higher or lower than another.")

    default = db.Column(
        db.Boolean,
        default=False, nullable=False,
        doc="If true, this software version will be registered"
            "on new nodes by default.")

    discovery_code = db.Column(
        db.UnicodeText,
        nullable=True,
        doc="Python code to discover if this software version is installed "
            "on a node")

    discovery_function_name = db.Column(
        db.String(config.get("max_discovery_function_name_length")),
        nullable=True,
        doc="The name of a function in `discovery_code` to call when "
            "checking for the presence of this software version on an agent.\n"
            "The function should return either a boolean (true if present, "
            "false if not) or a tuple of a boolean and a dict of named "
            "parameters describing this installation.")


class JobSoftwareRequirement(db.Model, UtilityMixins):
    """
    Model representing a dependency of a job on a software tag, with optional
    version constraints
    """
    __tablename__ = config.get("table_job_software_req")
    __table_args__ = (
        UniqueConstraint("software_id", "job_id"), )

    id = id_column()

    software_id = db.Column(
        db.Integer,
        db.ForeignKey("%s.id" % config.get("table_software")),
        nullable=False, doc="Reference to the required software")

    job_id = db.Column(
        IDTypeWork,
        db.ForeignKey("%s.id" % config.get("table_job")),
        nullable=False, doc="Foreign key to :class:`Job.id`")

    min_version_id = db.Column(
        db.Integer,
        db.ForeignKey("%s.id" % config.get("table_software_version")),
        nullable=True, doc="Reference to the minimum required version")

    max_version_id = db.Column(
        db.Integer,
        db.ForeignKey("%s.id" % config.get("table_software_version")),
        nullable=True, doc="Reference to the maximum required version")

    #
    # Relationships
    #
    job = db.relationship(
        "Job",
        backref=db.backref(
            "software_requirements",
            lazy="dynamic",
            cascade="all, delete-orphan"))

    software = db.relationship("Software")

    min_version = db.relationship(
        "SoftwareVersion", foreign_keys=[min_version_id])

    max_version = db.relationship(
        "SoftwareVersion", foreign_keys=[max_version_id])


class JobTypeSoftwareRequirement(db.Model, UtilityMixins):
    """
    Model representing a dependency of a job on a software tag, with optional
    version constraints
    """
    __tablename__ = config.get("table_job_type_software_req")
    __table_args__ = (
        UniqueConstraint("software_id", "jobtype_version_id"), )

    software_id = db.Column(
        db.Integer,
        db.ForeignKey("%s.id" % config.get("table_software")),
        primary_key=True,
        doc="Reference to the required software")

    jobtype_version_id = db.Column(
        IDTypeWork,
        db.ForeignKey("%s.id" % config.get("table_job_type_version")),
        primary_key=True,
        doc="Foreign key to :class:`JobTypeVersion.id`")

    min_version_id = db.Column(
        db.Integer,
        db.ForeignKey("%s.id" % config.get("table_software_version")),
        nullable=True, doc="Reference to the minimum required version")

    max_version_id = db.Column(
        db.Integer,
        db.ForeignKey("%s.id" % config.get("table_software_version")),
        nullable=True, doc="Reference to the maximum required version")

    #
    # Relationships
    #
    jobtype_version = db.relationship(
        "JobTypeVersion",
        backref=db.backref(
            "software_requirements",
            lazy="dynamic",
            cascade="all, delete-orphan"))

    software = db.relationship("Software")

    min_version = db.relationship(
        "SoftwareVersion", foreign_keys=[min_version_id])

    max_version = db.relationship(
        "SoftwareVersion", foreign_keys=[max_version_id])
