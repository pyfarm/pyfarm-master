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
Tag
===
Table with tags for both jobs and agents
"""

from textwrap import dedent

from sqlalchemy.schema import UniqueConstraint

from pyfarm.master.application import db
from pyfarm.models.core.cfg import TABLE_TAG, MAX_TAG_LENGTH
from pyfarm.models.core.types import id_column
from pyfarm.models.core.mixins import UtilityMixins

__all__ = ("Tag", )


class Tag(db.Model, UtilityMixins):
    """
    Model which provides tagging for :class:`.Job` and class:`.Agent` objects
    """
    __tablename__ = TABLE_TAG
    __table_args__ = (UniqueConstraint("tag"), )

    id = id_column()

    tag = db.Column(db.String(MAX_TAG_LENGTH), nullable=False,
                    doc=dedent("""The actual value of the tag"""))
