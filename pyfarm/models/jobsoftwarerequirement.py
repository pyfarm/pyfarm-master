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
JobSoftwareRequirement
======================
Table of software requirements for a job
"""

from textwrap import dedent

from sqlalchemy.schema import UniqueConstraint

from pyfarm.master.application import db
from pyfarm.models.core.cfg import (
    TABLE_JOB_SOFTWARE_REQ, TABLE_SOFTWARE, TABLE_SOFTWARE_VERSION, TABLE_JOB,
    MAX_TAG_LENGTH)
from pyfarm.models.core.types import id_column, IDTypeWork
from pyfarm.models.core.mixins import UtilityMixins
from pyfarm.models.job import Job


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
                            doc=dedent("""
                                Reference to the required software"""))
    job_id = db.Column(IDTypeWork, db.ForeignKey("%s.id" % TABLE_JOB),
                       nullable=False,
                       doc=dedent("""
                            Foreign key to :class:`Job.id`"""))
    min_version = db.Column(db.Integer,
                            db.ForeignKey("%s.id" % TABLE_SOFTWARE_VERSION),
                            nullable=True,
                            doc=dedent("""
                                Reference to the minimum required version"""))
    max_version = db.Column(db.Integer,
                            db.ForeignKey("%s.id" % TABLE_SOFTWARE_VERSION),
                            nullable=True,
                            doc=dedent("""
                                Reference to the maximum required version"""))

    job = db.relationship("Job", backref="software_requirements")
    software = db.relationship("Software")
