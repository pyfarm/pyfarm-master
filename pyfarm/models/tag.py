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
Tag Model
=========

Table with tags for both jobs and agents
"""

from sqlalchemy.schema import UniqueConstraint

from pyfarm.master.application import db
from pyfarm.master.config import config
from pyfarm.models.core.types import id_column
from pyfarm.models.core.mixins import UtilityMixins
from pyfarm.models.core.types import IDTypeWork

__all__ = ("Tag", )


class Tag(db.Model, UtilityMixins):
    """
    Model which provides tagging for :class:`.Job` and class:`.Agent` objects
    """
    __tablename__ = config.get("table_tag")
    __table_args__ = (UniqueConstraint("tag"), )

    id = id_column()

    tag = db.Column(
        db.String(config.get("max_tag_length")),
        nullable=False, doc="The actual value of the tag")


class JobTagRequirement(db.Model, UtilityMixins):
    """
    Model representing a dependency of a job on a tag

    If a job has a tag requirement, it will only run on agents that have that
    tag.
    """
    __tablename__ = config.get("table_job_tag_req")
    __table_args__ = (UniqueConstraint("tag_id", "job_id"), )

    id = id_column()

    tag_id = db.Column(
        db.Integer,
        db.ForeignKey("%s.id" % config.get("table_tag")),
        nullable=False, doc="Reference to the required tag")

    job_id = db.Column(
        IDTypeWork,
        db.ForeignKey("%s.id" % config.get("table_job")),
        nullable=False, doc="Foreign key to :class:`Job.id`")

    negate = db.Column(
        db.Boolean,
        nullable=False, default=False,
        doc="If true, an agent that has this tag can not work on this job")

    job = db.relationship(
        "Job",
        backref=db.backref(
            "tag_requirements",
            lazy="dynamic",
            cascade="all, delete-orphan"))

    tag = db.relationship("Tag")
