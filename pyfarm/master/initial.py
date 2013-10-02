# No shebang line, this module is meant to be imported
#
# Copyright 2013 Oliver Palmer
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
Initial Setup
=============

Entry points for the /setup/ target
"""
from flask import render_template
from pyfarm.master.application import db

# import all tables so we know what should exist and
# what we'll need to create
from pyfarm.models.core.cfg import TABLES
from pyfarm.models.task import TaskModel, TaskDependencies
from pyfarm.models.job import JobModel, JobTagsModel, JobDependencies
from pyfarm.models.jobtype import JobTypeModel
from pyfarm.models.agent import AgentModel, AgentSoftwareModel, AgentTagsModel
from pyfarm.models.users import User, Role


def setup_page():
    # make sure the tables exist
    db.create_all()

    # create the admin role if it does not exist and
    # find any existing administrators
    admin = Role.query.filter_by(name="admin").first()
    if admin is None:
        admin = Role.create("admin")
        user = User.create("admin2", "password")
        user.roles.append(admin)
        db.session.add(user)
        db.session.commit()
        admin_users = []
    else:
        admin_users = admin.users

    #User.create("admin", "password", roles=set(["admin"]))

    return render_template("pyfarm/setup.html",
                           admin_exists=admin, admin_users=admin_users)