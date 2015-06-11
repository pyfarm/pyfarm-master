# No shebang line, this module is meant to be imported
#
# Copyright 2015 Ambient Entertainment GmbH & Co. KG
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
Job Group Model
===============

Model for job groups
"""

from pyfarm.master.application import db
from pyfarm.master.config import config
from pyfarm.models.core.mixins import UtilityMixins
from pyfarm.models.core.types import id_column, IDTypeWork


class JobGroup(db.Model, UtilityMixins):
    """
    Used to group jobs together for better presentation in the UI
    """
    __tablename__ = config.get("table_job_group")

    id = id_column(IDTypeWork)

    title = db.Column(
        db.String(config.get("max_jobgroup_name_length")),
        nullable=False,
        doc="The title of the job group's name")

    main_jobtype_id = db.Column(
        IDTypeWork,
        db.ForeignKey("%s.id" % config.get("table_job_type")),
        nullable=False,
        doc="ID of the jobtype of the main job in this "
            "group. Purely for display and filtering.")

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("%s.id" % config.get("table_user")),
        doc="The id of the user who owns these jobs")

    #
    # Relationships
    #
    main_jobtype = db.relationship(
        "JobType",
        backref=db.backref("jobgroups", lazy="dynamic"),
        doc="The jobtype of the main job in this group")

    user = db.relationship(
        "User",
        backref=db.backref("jobgroups", lazy="dynamic"),
        doc="The user who owns these jobs")
