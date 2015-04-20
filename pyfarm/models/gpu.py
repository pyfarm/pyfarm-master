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
GPU
===

Model describing a given make and model of graphics card.
Every agent can have zero or more GPUs associated with it.
"""

from sqlalchemy.schema import UniqueConstraint

from pyfarm.master.application import db
from pyfarm.master.config import config
from pyfarm.models.core.mixins import ReprMixin, UtilityMixins
from pyfarm.models.core.types import id_column


class GPU(db.Model, UtilityMixins, ReprMixin):
    __tablename__ = config.get("table_gpu")
    __table_args__ = (UniqueConstraint("fullname"),)

    id = id_column(db.Integer)

    fullname = db.Column(
        db.String(config.get("max_gpu_name_length")),
        nullable=False,
        doc="The full name of this graphics card model")
