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
Master Script Entry Points
===========================

Contains the functions necessary to run individual components
of PyFarm's master.
"""

from pyfarm.models.core.cfg import TABLES
from pyfarm.models.project import Project
from pyfarm.models.software import Software
from pyfarm.models.tag import Tag
from pyfarm.models.task import Task, TaskDependencies
from pyfarm.models.job import Job, JobDependencies, JobSoftwareDependency
from pyfarm.models.jobtype import JobType
from pyfarm.models.agent import (
    Agent, AgentTagAssociation, AgentSoftwareAssociation)
from pyfarm.models.user import User, Role
from pyfarm.master.application import db


def load_before_first(app_instance, database_instance):
    if app_instance.debug:
        app_instance.before_first_request_funcs.append(
            database_instance.create_all)


def load_error_handlers(app_instance):
    """loads the error handlers onto application instance"""
    from pyfarm.master.errors import error_400, error_401, error_404, error_500
    app_instance.register_error_handler(400, error_400)
    app_instance.register_error_handler(401, error_401)
    app_instance.register_error_handler(404, error_404)
    app_instance.register_error_handler(500, error_500)


def load_setup(app_instance):
    """configures flask to serve the endpoint used for setting up the system"""
    from pyfarm.master.initial import setup_page
    app_instance.add_url_rule("/setup/",
                              "setup_page", setup_page, methods=("GET", "POST"))


def load_authentication(app_instance):
    """configures flask to serve the authentication endpoints"""
    from pyfarm.master.login import login_page, logout_page
    app_instance.add_url_rule("/logout/", "logout_page", logout_page)
    app_instance.add_url_rule(
        "/login/", "login_page", login_page, methods=("GET", "POST"))


def load_index(app_instance):
    """configures flask to serve the main index and favicon"""
    from pyfarm.master.index import index_page, favicon
    app_instance.add_url_rule("/", "index_page", index_page)
    app_instance.add_url_rule("/favicon.ico", "favicon", favicon)


def load_api(app_instance, api_instance):
    """configures flask to serve the api endpoints"""
    from pyfarm.master.api.agents import (
        SingleAgentAPI, AgentIndexAPI, schema as agent_schema)
    from pyfarm.master.api.software import (
        schema as software_schema, SoftwareIndexAPI)
    from pyfarm.master.api.tag import (
        schema as tag_schema, TagIndexAPI)

    # add api methods
    api_instance.add_url_rule(
        "/agents",
        view_func=AgentIndexAPI.as_view("agent_index_api"))
    api_instance.add_url_rule(
        "/agents/schema",
        "agent_schema", view_func=agent_schema, methods=("GET", ))
    api_instance.add_url_rule(
        "/agents/<int:agent_id>",
        view_func=SingleAgentAPI.as_view("single_agent_api"))
    api_instance.add_url_rule(
        "/software/schema",
        "software_schema", view_func=software_schema, methods=("GET", ))
    api_instance.add_url_rule(
        "/software",
        view_func=SoftwareIndexAPI.as_view("software_index_api"))
    api_instance.add_url_rule(
        "/tag/schema",
        "tag_schema", view_func=tag_schema, methods=("GET", ))
    api_instance.add_url_rule(
        "/tags",
        view_func=TagIndexAPI.as_view("tag_index_api"))

    # register the api blueprint
    app_instance.register_blueprint(api_instance)


def load_admin(admin_instance):
    """serves the administrative interface endpoints"""
    from flask.ext.admin.base import MenuLink
    from pyfarm.master.admin.projects import ProjectView
    from pyfarm.master.admin.users import UserView, RoleView
    from pyfarm.master.admin.software import SoftwareView
    from pyfarm.master.admin.tag import TagView
    from pyfarm.master.admin.agents import AgentView
    from pyfarm.master.admin.work import (
        JobView, TaskView)

    # admin links
    admin_instance.add_link(MenuLink("Preferences", "/preferences"))
    admin_instance.add_link(MenuLink("Log Out", "/logout"))

    # admin database views
    admin_instance.add_view(
        UserView(name="Users - User", endpoint="users/user"))
    admin_instance.add_view(
        RoleView(name="Users - Role", endpoint="users/role"))
    admin_instance.add_view(
        TagView(name="Tags", endpoint="tag"))
    admin_instance.add_view(
        SoftwareView(name="Software", endpoint="software"))
    admin_instance.add_view(
        AgentView(name="Agents - Host", endpoint="agents/agent"))
    admin_instance.add_view(
        JobView(name="Jobs - Job", endpoint="jobs/job"))
    admin_instance.add_view(
        TaskView(name="Jobs - Task", endpoint="jobs/task"))
    admin_instance.add_view(
        ProjectView(name="Projects", endpoint="projects"))


def load_master(app, admin, api):
    """loads and attaches all endpoints needed to run the master"""
    load_error_handlers(app)
    load_index(app)
    load_authentication(app)
    load_admin(admin)
    load_api(app, api)


def run_master():  # pragma: no cover
    """Runs :func:`load_master` then runs the application"""
    from argparse import ArgumentParser
    from pyfarm.master.application import app, admin, api

    parser = ArgumentParser()
    if app.debug:
        parser.add_argument("--drop-all", "-D", action="store_true",
                            help="drop the existing tables before starting")

    parser.add_argument("--create-all", "-C", action="store_true",
                        help="create all tables before starting")
    parser.add_argument("--confirm-drop")
    parser.add_argument("--allow-any-agent-address", action="store_true",
                        help="Special flag that will turn off all ip address "
                             "validation in the agent model.  This is provided "
                             "so the master and agent can be run on the "
                             "loopback adapter.")
    parsed = parser.parse_args()

    if app.debug and parsed.drop_all:
        db.drop_all()

    if parsed.create_all:
        db.create_all()

    if parsed.allow_any_agent_address:
        app.config["DEV_ALLOW_ANY_AGENT_ADDRESS"] = True

    load_master(app, admin, api)
    app.run()

if __name__ == "__main__":
    run_master()
