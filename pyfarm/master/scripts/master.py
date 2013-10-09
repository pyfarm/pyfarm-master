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
Master Script Endpoints
=======================

Contains the functions necessary to run individual components
of PyFarm's master.
"""

from flask import abort
from pyfarm.models.core.cfg import TABLES
from pyfarm.models.task import TaskModel, TaskDependencies
from pyfarm.models.job import JobModel, JobTagsModel, JobDependencies
from pyfarm.models.jobtype import JobTypeModel
from pyfarm.models.agent import (
    AgentModel, AgentSoftwareModel, AgentTagsModel,
    AgentSoftwareDependencies, AgentTagDependencies)
from pyfarm.models.users import User, Role

from pyfarm.master.application import db, app, admin, api
from pyfarm.master.errors import error_400, error_401, error_404, error_500

# when debugging we should create the database tables
if app.debug:
    app.before_first_request_funcs.append(db.create_all)

# register error handlers
app.register_error_handler(400, error_400)
app.register_error_handler(401, error_401)
app.register_error_handler(404, error_404)
app.register_error_handler(500, error_500)

# update abort with the above error handlers
#abort.mapping[400] = error_400
#abort.mapping[401] = error_401
#abort.mapping[404] = error_404
#abort.mapping[500] = error_500


def endpoint_setup(app_instance):
    """configures flask to serve the endpoint used for setting up the system"""
    assert app_instance is app
    from pyfarm.master.initial import setup_page
    app_instance.add_url_rule("/setup/",
                              "setup_page", setup_page, methods=("GET", "POST"))


def endpoint_authentication(app_instance):
    """configures flask to serve the authentication endpoints"""
    assert app_instance is app
    from pyfarm.master.login import login_page, logout_page
    app_instance.add_url_rule("/logout/", "logout_page", logout_page)
    app_instance.add_url_rule(
        "/login/", "login_page", login_page, methods=("GET", "POST"))


def endpoint_index(app_instance):
    """configures flask to serve the main index and favicon"""
    assert app_instance is app
    from pyfarm.master.index import index_page, favicon
    app_instance.add_url_rule("/", "index_page", index_page)
    app_instance.add_url_rule("/favicon.ico", "favicon", favicon)


def endpoint_api(app_instance, api_instance):
    """configures flask to serve the api endpoints"""
    assert app_instance is app
    assert api_instance is api
    from pyfarm.master.api.agents import AgentsIndex

    api_instance.add_url_rule(
        "/agents", view_func=AgentsIndex.as_view("agents_index"))
    app_instance.register_blueprint(api)



def endpoint_admin(admin_instance):
    """serves the administrative interface endpoints"""
    assert admin_instance is admin
    from flask.ext.admin.base import MenuLink
    from pyfarm.master.admin.users import UserView, RoleView
    from pyfarm.master.admin.agents import (
        AgentModelView, AgentSoftwareModelView, AgentTagsModelView)
    from pyfarm.master.admin.work import (
        JobModelView, JobSoftwareModelView, JobTagsModelView, TaskModelView)

    # admin links
    admin_instance.add_link(MenuLink("Preferences", "/preferences"))
    admin_instance.add_link(MenuLink("Log Out", "/logout"))

    # admin database views
    admin_instance.add_view(
        UserView(name="Users - User", endpoint="users/user"))
    admin_instance.add_view(
        RoleView(name="Users - Role", endpoint="users/role"))
    admin_instance.add_view(
        AgentModelView(name="Agents - Host", endpoint="agents/agent"))
    admin_instance.add_view(
        AgentSoftwareModelView(name="Agents - Software", endpoint="agents/software"))
    admin_instance.add_view(
        AgentTagsModelView(name="Agents - Tags", endpoint="agents/tags"))
    admin_instance.add_view(
        JobModelView(name="Jobs - Job", endpoint="jobs/job"))
    admin_instance.add_view(
        TaskModelView(name="Jobs - Task", endpoint="jobs/task"))
    admin_instance.add_view(
        JobSoftwareModelView(name="Jobs - Software", endpoint="jobs/software"))
    admin_instance.add_view(
        JobTagsModelView(name="Jobs - Tags", endpoint="jobs/tags"))


def run_master():
    """runs the application server and all end points except for /setup"""
    endpoint_index(app)
    endpoint_authentication(app)
    endpoint_admin(admin)
    endpoint_api(app, api)
    app.run()


if __name__ == "__main__":
    run_master()