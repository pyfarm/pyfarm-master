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


def run_master():
    from flask.ext.admin.base import MenuLink
    from pyfarm.master.admin.users import UserView, RoleView
    from pyfarm.master.admin.agent import (
        AgentModelView, AgentSoftwareModelView, AgentTagsModelView)
    from pyfarm.master.admin.work import (
        JobModelView, JobSoftwareModelView, JobTagsModelView, TaskModelView)
    from pyfarm.master.application import app, admin, db
    from pyfarm.master.login import login_page, logout_page
    from pyfarm.master.initial import setup_page
    from pyfarm.master.index import index_page, favicon
    from pyfarm.master.errors import error_404, error_401, error_500

    # when debugging we should create the database
    # tables
    if app.debug:
        from pyfarm.models.core.cfg import TABLES
        from pyfarm.models.task import TaskModel, TaskDependencies
        from pyfarm.models.job import JobModel, JobTagsModel, JobDependencies
        from pyfarm.models.jobtype import JobTypeModel
        from pyfarm.models.agent import (
            AgentModel, AgentSoftwareModel, AgentTagsModel,
            AgentSoftwareDependencies, AgentTagDependencies)
        from pyfarm.models.users import User, Role
        app.before_first_request_funcs.append(db.create_all)

    # register error handlers
    app.register_error_handler(404, error_404)
    app.register_error_handler(401, error_401)
    app.register_error_handler(500, error_500)

    # routes
    app.add_url_rule(
        "/", "index_page", index_page)
    app.add_url_rule(
        "/favicon.ico", "favicon", favicon)
    app.add_url_rule(
        "/login/", "login_page", login_page, methods=("GET", "POST"))
    app.add_url_rule(
        "/logout/", "logout_page", logout_page)
    app.add_url_rule(
        "/setup/", "setup_page", setup_page, methods=("GET", "POST"))

    # admin links
    admin.add_link(MenuLink("Preferences", "/preferences"))
    admin.add_link(MenuLink("Log Out", "/logout"))

    # admin database views
    admin.add_view(UserView(
        name="Users - User", endpoint="users/user"))
    admin.add_view(RoleView(
        name="Users - Role", endpoint="users/role"))
    admin.add_view(AgentModelView(
        name="Agents - Host", endpoint="agents/agent"))
    admin.add_view(AgentSoftwareModelView(
        name="Agents - Software", endpoint="agents/software"))
    admin.add_view(AgentTagsModelView(
        name="Agents - Tags", endpoint="agents/tags"))
    admin.add_view(JobModelView(
        name="Jobs - Job", endpoint="jobs/job"))
    admin.add_view(TaskModelView(
        name="Jobs - Task", endpoint="jobs/task"))
    admin.add_view(JobSoftwareModelView(
        name="Jobs - Software", endpoint="jobs/software"))
    admin.add_view(JobTagsModelView(
        name="Jobs - Tags", endpoint="jobs/tags"))

    app.run()


if __name__ == "__main__":
    run_master()
