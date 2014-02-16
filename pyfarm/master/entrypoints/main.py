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
==========================

Contains the functions necessary to run individual components
of PyFarm's master.
"""

from functools import partial

try:
    from httplib import (
        responses, BAD_REQUEST, UNAUTHORIZED, NOT_FOUND, METHOD_NOT_ALLOWED,
        INTERNAL_SERVER_ERROR)
except ImportError:
    from http.client import (
        responses, BAD_REQUEST, UNAUTHORIZED, NOT_FOUND, METHOD_NOT_ALLOWED,
        INTERNAL_SERVER_ERROR)

from flask import request

from pyfarm.models.core.cfg import TABLES
from pyfarm.models.project import Project
from pyfarm.models.software import (
    Software, SoftwareVersion, JobSoftwareRequirement,
    JobTypeSoftwareRequirement)
from pyfarm.models.tag import Tag
from pyfarm.models.task import Task, TaskDependencies
from pyfarm.models.job import Job, JobDependencies
from pyfarm.models.jobtype import JobType
from pyfarm.models.agent import (
    Agent, AgentTagAssociation)
from pyfarm.models.user import User, Role
from pyfarm.master.application import db
from pyfarm.master.utility import error_handler


def load_before_first(app_instance, database_instance):
    if app_instance.debug:
        app_instance.before_first_request_funcs.append(
            database_instance.create_all)


def load_error_handlers(app_instance):
    """loads the error handlers onto application instance"""
    # create the handlers
    bad_request = partial(
        error_handler, code=BAD_REQUEST,
        default=lambda: "bad request to %s" % request.url)
    unauthorized = partial(
        error_handler, code=BAD_REQUEST,
        default=lambda: "unauthorized request to %s" % request.url)
    not_found = partial(
        error_handler, code=NOT_FOUND,
        default=lambda: "%s was not found" % request.url)
    method_not_allowed = partial(
        error_handler, code=METHOD_NOT_ALLOWED,
        default=lambda:
        "%s does not allow %s requests" % (request.url, request.method))
    internal_server_error = partial(
        error_handler, code=INTERNAL_SERVER_ERROR,
        default=lambda:
        "unhandled error while accessing %s" % request.url)

    # apply the handlers to the application instance
    app_instance.register_error_handler(BAD_REQUEST, bad_request)
    app_instance.register_error_handler(UNAUTHORIZED, unauthorized)
    app_instance.register_error_handler(NOT_FOUND, not_found)
    app_instance.register_error_handler(METHOD_NOT_ALLOWED, method_not_allowed)
    app_instance.register_error_handler(
        INTERNAL_SERVER_ERROR, internal_server_error)


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
        schema as software_schema, SoftwareIndexAPI, SingleSoftwareAPI,
        SoftwareVersionsIndexAPI, SingleSoftwareVersionAPI)
    from pyfarm.master.api.tags import (
        schema as tag_schema, TagIndexAPI, SingleTagAPI, AgentsInTagIndexAPI)

    # top level types
    api_instance.add_url_rule(
        "/agents/",
        view_func=AgentIndexAPI.as_view("agent_index_api"))
    api_instance.add_url_rule(
        "/software/",
        view_func=SoftwareIndexAPI.as_view("software_index_api"))
    api_instance.add_url_rule(
        "/tags/",
        view_func=TagIndexAPI.as_view("tag_index_api"))

    # schemas
    api_instance.add_url_rule(
        "/agents/schema",
        "agent_schema", view_func=agent_schema, methods=("GET", ))
    api_instance.add_url_rule(
        "/software/schema",
        "software_schema", view_func=software_schema, methods=("GET", ))
    api_instance.add_url_rule(
        "/tags/schema",
        "tags_schema", view_func=tag_schema, methods=("GET", ))

    # specific item access
    api_instance.add_url_rule(
        "/tags/<string:tagname>",
        view_func=SingleTagAPI.as_view("single_tag_by_string_api"))
    api_instance.add_url_rule(
        "/tags/<int:tagname>",
        view_func=SingleTagAPI.as_view("single_tag_by_id_api"))
    api_instance.add_url_rule(
        "/agents/<int:agent_id>",
        view_func=SingleAgentAPI.as_view("single_agent_api"))
    api_instance.add_url_rule(
        "/software/<int:software_rq>",
        view_func=SingleSoftwareAPI.as_view("single_software_by_id_api"))
    api_instance.add_url_rule(
        "/software/<string:software_rq>",
        view_func=SingleSoftwareAPI.as_view("single_software_by_string_api"))

    # subitems
    api_instance.add_url_rule(
        "/tags/<string:tagname>/agents/",
        view_func=AgentsInTagIndexAPI.as_view(
            "agents_in_tag_by_string_index_api"))
    api_instance.add_url_rule(
        "/tags/<int:tagname>/agents/",
        view_func=AgentsInTagIndexAPI.as_view("agents_in_tag_by_id_index_api"))

    api_instance.add_url_rule(
        "/software/<string:software_rq>/versions/",
        view_func=SoftwareVersionsIndexAPI.as_view(
            "software_by_string_versions_index_api"))
    api_instance.add_url_rule(
        "/software/<int:software_rq>/versions/",
        view_func=SoftwareVersionsIndexAPI.as_view(
            "software_by_id_versions_index_api"))
    api_instance.add_url_rule(
        "/software/<string:software_rq>/versions/<string:version_name>",
        view_func=SingleSoftwareVersionAPI.as_view(
            "software_by_string_version_by_string_index_api"))
    api_instance.add_url_rule(
        "/software/<string:software_rq>/versions/<int:version_name>",
        view_func=SingleSoftwareVersionAPI.as_view(
            "software_by_string_version_by_id_index_api"))
    api_instance.add_url_rule(
        "/software/<int:software_rq>/versions/<string:version_name>",
        view_func=SingleSoftwareVersionAPI.as_view(
            "software_by_id_version_by_string_index_api"))
    api_instance.add_url_rule(
        "/software/<int:software_rq>/versions/<int:version_name>",
        view_func=SingleSoftwareVersionAPI.as_view(
            "software_by_id_version_by_id_index_api"))

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

    load_setup(app)
    load_master(app, admin, api)
    app.run()

if __name__ == "__main__":
    run_master()
