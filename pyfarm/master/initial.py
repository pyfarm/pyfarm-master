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

from wtforms import Form, TextField, PasswordField, ValidationError
from wtforms.validators import Required
from flask import render_template, request
from pyfarm.master.application import db

# import all tables so we know what should exist and
# what we'll need to create
from pyfarm.models.core.cfg import TABLES
from pyfarm.models.task import TaskModel, TaskDependencies
from pyfarm.models.job import JobModel, JobTagsModel, JobDependencies
from pyfarm.models.jobtype import JobTypeModel
from pyfarm.models.agent import AgentModel, AgentSoftwareModel, AgentTagsModel
from pyfarm.models.users import User, Role


class NewUserForm(Form):
    username = TextField(validators=[Required()])
    email = TextField(validators=[Required()])
    password = PasswordField(validators=[Required()])

    def validate_username(self, field):
        user = User.get(request.form["username"])
        if user is not None:
            raise ValidationError(
                "%s already exists" % request.form["username"])


def setup_page():
    form = NewUserForm(request.form)

    if request.method == "GET":
        # make sure the tables exist
        db.create_all()

        # create the admin role if it does not exist and
        # find any existing administrators
        admin_role = Role.query.filter_by(name="admin").first()
        if admin_role is None:
            admin_role = Role.create("admin")
            admin_users = []
        else:
            admin_users = admin_role.users

        return render_template("pyfarm/setup.html", form=form,
                               admin_role=admin_role, admin_users=admin_users)

    elif request.method == "POST":
        if form.validate():
            admin_role = Role.create("admin")
            user = User.create(
                request.form["username"],
                request.form["password"],
                email=request.form["email"])
            user.roles.append(admin_role)
            db.session.add(user)
            db.session.commit()
            return render_template("pyfarm/setup.html",
                                   finished=True, redirect_seconds=5)

        return render_template("pyfarm/setup.html", form=form)
