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
GPU
---

Model describing a given make and model of graphics card.
Every agent can have zero or more GPUs associated with it.
"""

from sqlalchemy.schema import UniqueConstraint

from pyfarm.master.application import db
from pyfarm.models.core.mixins import ReprMixin, UtilityMixins
from pyfarm.models.core.types import id_column
from pyfarm.models.core.cfg import TABLE_GPU, MAX_GPUNAME_LENGTH

class GPU(db.Model, UtilityMixins, ReprMixin):
    __tablename__ = TABLE_GPU
    __table_args__ = (UniqueConstraint("fullname"),)
    id = id_column(db.Integer)
    fullname = db.Column(db.String(MAX_GPUNAME_LENGTH), nullable=False,
                         doc="The full name of this graphics card model")
