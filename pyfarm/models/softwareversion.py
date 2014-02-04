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
SoftwareVersion
===============
Table holding different versions for a given software.
"""

from textwrap import dedent

from sqlalchemy.schema import UniqueConstraint

from pyfarm.master.application import db
from pyfarm.models.core.cfg import (
    TABLE_SOFTWARE_VERSION, TABLE_SOFTWARE, MAX_TAG_LENGTH)
from pyfarm.models.core.types import id_column
from pyfarm.models.core.mixins import UtilityMixins


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
                        the same software. Used to determine whether a version is
                        higher or lower than another."""))

    software = db.relationship("Software", backref="software_versions")
