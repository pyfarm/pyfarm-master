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
Software
========
Table of software items. Agents can reference this table to show that they
provide a given software. Jobs or jobtypes can depend on a software via the
SoftwareRequirement table
"""

from textwrap import dedent

from sqlalchemy.schema import UniqueConstraint

from pyfarm.master.application import db
from pyfarm.models.core.cfg import (
    TABLE_SOFTWARE, TABLE_SOFTWARE_VERSION, MAX_TAG_LENGTH,
    TABLE_JOB, TABLE_JOB_SOFTWARE_REQ, TABLE_JOB_TYPE, TABLE_JOB_TYPE_VERSION,
    TABLE_JOB_TYPE_SOFTWARE_REQ)
from pyfarm.models.core.types import id_column, IDTypeWork
from pyfarm.models.core.mixins import UtilityMixins

__all__ = ("Software", )


class Software(db.Model, UtilityMixins):
    """
    Model to represent a versioned piece of software that can be present on an
    agent and may be depended on by a job and/or jobtype through the appropriate
    SoftwareRequirement table

    """
    __tablename__ = TABLE_SOFTWARE
    __table_args__ = (
        UniqueConstraint("software"), )

    id = id_column()
    software = db.Column(db.String(MAX_TAG_LENGTH), nullable=False,
                         doc=dedent("""
                         The name of the software"""))

    versions = db.relationship("SoftwareVersion",
                               backref=db.backref("software"),
                               lazy="dynamic",
                               cascade="all, delete-orphan",
                               order_by="asc(SoftwareVersion.rank)",
                               doc="All known versions of this "
                                   "software")


class SoftwareVersion(db.Model, UtilityMixins):
    """
    Model to represent a version for a given software

    """
    __tablename__ = TABLE_SOFTWARE_VERSION
    __table_args__ = (
        UniqueConstraint("software_id", "version"),
        UniqueConstraint("software_id", "rank"))

    id = id_column()
    software_id = db.Column(db.Integer, db.ForeignKey("%s.id" % TABLE_SOFTWARE),
                            nullable=False,
                            doc="The software this version belongs to")
    version = db.Column(db.String(MAX_TAG_LENGTH),
                        default="any", nullable=False,
                        doc=dedent("""
                            The version of the software.  This value does not
                            follow any special formatting rules because the
                            format depends on the 3rd party."""))
    rank = db.Column(db.Integer, nullable=False,
                     doc=dedent("""
                        The rank of this version relative to other versions of
                        the same software. Used to determine whether a version
                        is higher or lower than another."""))


class JobSoftwareRequirement(db.Model, UtilityMixins):
    """
    Model representing a dependency of a job on a software tag, with optional
    version constraints

    """
    __tablename__ = TABLE_JOB_SOFTWARE_REQ
    __table_args__ = (
        UniqueConstraint("software_id", "job_id"), )

    id = id_column()
    software_id = db.Column(db.Integer,
                            db.ForeignKey("%s.id" % TABLE_SOFTWARE),
                            nullable=False,
                            doc="Reference to the required software")
    job_id = db.Column(IDTypeWork, db.ForeignKey("%s.id" % TABLE_JOB),
                       nullable=False,
                       doc="Foreign key to :class:`Job.id`")
    min_version_id = db.Column(db.Integer,
                               db.ForeignKey("%s.id" % TABLE_SOFTWARE_VERSION),
                               nullable=True,
                               doc="Reference to the minimum required version")
    max_version_id = db.Column(db.Integer,
                            db.ForeignKey("%s.id" % TABLE_SOFTWARE_VERSION),
                            nullable=True,
                            doc="Reference to the maximum required version")

    job = db.relationship("Job", backref=db.backref("software_requirements",
                                                    lazy="dynamic",
                                                    cascade=
                                                        "all, delete-orphan"))
    software = db.relationship("Software")
    min_version = db.relationship("SoftwareVersion",
                                  foreign_keys=[min_version_id])
    max_version = db.relationship("SoftwareVersion",
                                  foreign_keys=[max_version_id])


class JobTypeSoftwareRequirement(db.Model, UtilityMixins):
    """
    Model representing a dependency of a job on a software tag, with optional
    version constraints

    """
    __tablename__ = TABLE_JOB_TYPE_SOFTWARE_REQ
    __table_args__ = (
        UniqueConstraint("software_id", "jobtype_version_id"), )

    software_id = db.Column(db.Integer,
                            db.ForeignKey("%s.id" % TABLE_SOFTWARE),
                            primary_key=True,
                            doc="Reference to the required software")
    jobtype_version_id = db.Column(IDTypeWork,
                                   db.ForeignKey("%s.id" %
                                                 TABLE_JOB_TYPE_VERSION),
                                   primary_key=True,
                                   doc="Foreign key to "
                                       ":class:`JobTypeVersion.id`")
    min_version_id = db.Column(db.Integer,
                               db.ForeignKey("%s.id" % TABLE_SOFTWARE_VERSION),
                               nullable=True,
                               doc="Reference to the minimum required version")
    max_version_id = db.Column(db.Integer,
                               db.ForeignKey("%s.id" % TABLE_SOFTWARE_VERSION),
                               nullable=True,
                               doc="Reference to the maximum required version")

    jobtype_version = db.relationship("JobTypeVersion",
                                      backref=db.backref("software_requirements",
                                                         lazy="dynamic",
                                                         cascade=
                                                           "all, delete-orphan"))
    software = db.relationship("Software")
    min_version = db.relationship("SoftwareVersion",
                                  foreign_keys=[min_version_id])
    max_version = db.relationship("SoftwareVersion",
                                  foreign_keys=[max_version_id])
