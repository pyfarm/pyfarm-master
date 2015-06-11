# No shebang line, this module is meant to be imported
#
# Copyright 2014 Ambient Entertainment GmbH & Co. KG
# Copyright 2015 Oliver Palmer
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
from pyfarm.master.config import config
from pyfarm.models.core.mixins import ReprMixin, UtilityMixins
from pyfarm.models.core.types import id_column


class PathMap(db.Model, ReprMixin, UtilityMixins):
    """
    Defines a table which is used for cross-platform
    file path mappings.
    """
    __tablename__ = config.get("table_path_map")

    id = id_column(db.Integer)

    path_linux = db.Column(
        db.String(config.get("max_path_length")),
        nullable=False,
        doc="The path on linux platforms")

    path_windows = db.Column(
        db.String(config.get("max_path_length")),
        nullable=False,
        doc="The path on Windows platforms")

    path_osx = db.Column(
        db.String(config.get("max_path_length")),
        nullable=False,
        doc="The path on Mac OS X platforms")

    tag_id = db.Column(
        db.Integer,
        db.ForeignKey("%s.id" % config.get("table_tag")),
        nullable=True,
        doc="The tag an agent needs to have for this path map "
            "to apply to it. "
            "If this is NULL, this path map applies to all "
            "agents, but is overridden by applying path maps "
            "that do specify a tag.")

    #
    # Relationships
    #
    tag = db.relationship(
        "Tag",
        backref=db.backref("path_maps", lazy="dynamic"),
        doc="Relationship attribute for the tag this path map "
            "applies to.")
