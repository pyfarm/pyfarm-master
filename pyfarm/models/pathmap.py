# No shebang line, this module is meant to be imported
#
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
Path Map Model
==============

Model for path maps, allowing for OS-dependent mapping of path prefixes to other
path prefixes.
"""

from pyfarm.master.application import db
from pyfarm.models.core.mixins import ReprMixin, UtilityMixins
from pyfarm.models.core.types import id_column
from pyfarm.models.core.cfg import (
    TABLE_PATH_MAP, MAX_PATH_LENGTH, TABLE_TAG)

class PathMap(db.Model, ReprMixin, UtilityMixins):
    __tablename__ = TABLE_PATH_MAP
    id = id_column(db.Integer)
    path_linux = db.Column(db.String(MAX_PATH_LENGTH), nullable=False,
                           doc="The path on linux platforms")
    path_windows = db.Column(db.String(MAX_PATH_LENGTH), nullable=False,
                             doc="The path on Windows platforms")
    path_osx = db.Column(db.String(MAX_PATH_LENGTH), nullable=False,
                         doc="The path on Mac OS X platforms")
    tag_id = db.Column(db.Integer,
                       db.ForeignKey("%s.id" % TABLE_TAG),
                       nullable=True,
                       doc="The tag an agent needs to have for this path map "
                           "to apply to it. "
                           "If this is NULL, this path map applies to all "
                           "agents, but is overridden by applying path maps "
                           "that do specify a tag.")
    tag = db.relationship("Tag",
                          backref=db.backref("path_maps", lazy="dynamic"),
                          doc="Relationship attribute for the tag this path map "
                              "applies to.")
