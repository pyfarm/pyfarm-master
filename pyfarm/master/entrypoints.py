# No shebang line, this module is meant to be imported
#
# Copyright 2013 Oliver Palmer
# Copyright 2014, 2015 Ambient Entertainment GmbH & Co. KG
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
Entry Points
============

Contains the code which operates the Python entry point scripts as well as
serving as a central location for the construction of the web application.
"""

from argparse import ArgumentParser
from functools import partial

try:
    from httplib import (
        responses, BAD_REQUEST, UNAUTHORIZED, NOT_FOUND, METHOD_NOT_ALLOWED,
        INTERNAL_SERVER_ERROR, UNSUPPORTED_MEDIA_TYPE)
except ImportError:
    from http.client import (
        responses, BAD_REQUEST, UNAUTHORIZED, NOT_FOUND, METHOD_NOT_ALLOWED,
        INTERNAL_SERVER_ERROR, UNSUPPORTED_MEDIA_TYPE)

from flask import request

from pyfarm.core.config import read_env_bool
from pyfarm.core.logger import getLogger
from pyfarm.master.application import db
from pyfarm.master.utility import error_handler

# Any table that needs to be created by db.create_all() should
# be imported here even if they're not used directly within this
# module.
from pyfarm.models.software import (
    Software, SoftwareVersion, JobSoftwareRequirement,
    JobTypeSoftwareRequirement)
from pyfarm.models.tag import Tag
from pyfarm.models.task import Task
from pyfarm.models.job import Job, JobDependency
from pyfarm.models.jobtype import JobType
from pyfarm.models.agent import Agent, AgentTagAssociation, GPUInAgent
from pyfarm.models.user import User, Role
from pyfarm.models.jobqueue import JobQueue
from pyfarm.models.pathmap import PathMap
from pyfarm.models.tasklog import TaskLog
from pyfarm.models.gpu import GPU

logger = getLogger("master.entrypoints")


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
    unsupported_media_type = partial(
        error_handler, code=UNSUPPORTED_MEDIA_TYPE,
        default=lambda:
        "%r is not a supported media type" % request.mimetype)

    # apply the handlers to the application instance
    app_instance.register_error_handler(BAD_REQUEST, bad_request)
    app_instance.register_error_handler(UNAUTHORIZED, unauthorized)
    app_instance.register_error_handler(NOT_FOUND, not_found)
    app_instance.register_error_handler(METHOD_NOT_ALLOWED, method_not_allowed)
    app_instance.register_error_handler(
        UNSUPPORTED_MEDIA_TYPE, unsupported_media_type)
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


def load_user_interface(app_instance):
    from pyfarm.master.user_interface.agents import (
        agents, single_agent, delete_single_agent, agent_add_software,
        agent_delete_software, restart_single_agent)
    from pyfarm.master.user_interface.jobs import (
        jobs, delete_single_job, rerun_single_job, single_job, pause_single_job,
        unpause_single_job, alter_frames_in_single_job,
        alter_scheduling_parameters_for_job, update_notes_for_job,
        update_tags_in_job, rerun_single_task, add_notified_user_to_job,
        remove_notified_user_from_job, upgrade_job_to_latest_jobtype_version,
        rerun_failed_in_job, alter_autodeletion_for_job, rerun_multiple_jobs,
        rerun_failed_in_multiple_jobs, pause_multiple_jobs,
        unpause_multiple_jobs, delete_multiple_jobs)
    from pyfarm.master.user_interface.jobqueues import (
        jobqueues, jobqueue_create, jobqueue, delete_jobqueue)
    from pyfarm.master.user_interface.jobtypes import (
        jobtypes, jobtype, remove_jobtype_software_requirement,
        add_jobtype_software_requirement, remove_jobtype, create_jobtype)
    from pyfarm.master.user_interface.logs_in_task import logs_in_task
    from pyfarm.master.user_interface.software import (
        software, software_item, update_version_rank, remove_software_version,
        add_software_version, add_software, remove_software)

    app_instance.add_url_rule("/agents/", "agents_index_ui", agents,
                              methods=("GET", ))
    app_instance.add_url_rule("/agents/<uuid:agent_id>/delete",
                              "delete_single_agent_ui", delete_single_agent,
                              methods=("POST", ))
    app_instance.add_url_rule("/agents/<uuid:agent_id>/restart",
                              "restart_single_agent_ui", restart_single_agent,
                              methods=("POST", ))
    app_instance.add_url_rule("/agents/<uuid:agent_id>", "single_agent_ui",
                              single_agent, methods=("GET", ))
    app_instance.add_url_rule("/agents/<uuid:agent_id>/software/add",
                              "single_agent_add_software_ui",
                              agent_add_software, methods=("POST", ))
    app_instance.add_url_rule(
        "/agents/<uuid:agent_id>/software/<int:version_id>/delete",
        "single_agent_remove_software_ui",
        agent_delete_software, methods=("POST", ))

    app_instance.add_url_rule("/jobs/", "jobs_index_ui", jobs,
                              methods=("GET", ))
    app_instance.add_url_rule("/jobs/<int:job_id>/delete",
                              "delete_single_job_ui", delete_single_job,
                              methods=("POST", ))
    app_instance.add_url_rule("/jobs/delete_multiple",
                              "delete_multiple_jobs_ui", delete_multiple_jobs,
                              methods=("POST", ))
    app_instance.add_url_rule("/jobs/<int:job_id>/rerun",
                              "rerun_single_job_ui", rerun_single_job,
                              methods=("POST", ))
    app_instance.add_url_rule("/jobs/rerun_multiple",
                              "rerun_multiple_jobs_ui", rerun_multiple_jobs,
                              methods=("POST", ))
    app_instance.add_url_rule("/jobs/<int:job_id>/rerun_failed_tasks",
                              "rerun_failed_in_job_ui", rerun_failed_in_job,
                              methods=("POST", ))
    app_instance.add_url_rule("/jobs/rerun_failed_multiple",
                              "rerun_failed_multiple_jobs_ui",
                              rerun_failed_in_multiple_jobs,
                              methods=("POST", ))
    app_instance.add_url_rule("/jobs/<int:job_id>/pause",
                              "pause_single_job_ui", pause_single_job,
                              methods=("POST", ))
    app_instance.add_url_rule("/jobs/pause_multiple",
                              "pause_multiple_jobs_ui", pause_multiple_jobs,
                              methods=("POST", ))
    app_instance.add_url_rule("/jobs/<int:job_id>/unpause",
                              "unpause_single_job_ui", unpause_single_job,
                              methods=("POST", ))
    app_instance.add_url_rule("/jobs/unpause_multiple",
                              "unpause_multiple_jobs_ui", unpause_multiple_jobs,
                              methods=("POST", ))
    app_instance.add_url_rule("/jobs/<int:job_id>/alter_frame_selection",
                              "alter_frames_in_job_ui",
                              alter_frames_in_single_job, methods=("POST", ))
    app_instance.add_url_rule("/jobs/<int:job_id>/alter_scheduling_parameters",
                              "alter_scheduling_parameters_in_job_ui",
                              alter_scheduling_parameters_for_job,
                              methods=("POST", ))
    app_instance.add_url_rule("/jobs/<int:job_id>/alter_autodelete_parameters",
                              "alter_autodelete_parameters_in_job_ui",
                              alter_autodeletion_for_job,
                              methods=("POST", ))
    app_instance.add_url_rule("/jobs/<int:job_id>/update_notes",
                              "update_job_notes_ui", update_notes_for_job,
                              methods=("POST", ))
    app_instance.add_url_rule("/jobs/<int:job_id>/update_tags",
                              "update_job_tags_ui", update_tags_in_job,
                              methods=("POST", ))
    app_instance.add_url_rule("/jobs/<int:job_id>/upgrade_jobtype",
                              "upgrade_jobtype_for_job",
                              upgrade_job_to_latest_jobtype_version,
                              methods=("POST", ))
    app_instance.add_url_rule("/jobs/<int:job_id>/tasks/<int:task_id>",
                              "rerun_single_task_ui", rerun_single_task,
                              methods=("POST", ))
    app_instance.add_url_rule("/jobs/<int:job_id>/notified_users/add",
                              "add_notified_user_ui", add_notified_user_to_job,
                              methods=("POST", ))
    app_instance.add_url_rule("/jobs/<int:job_id>/notified_users/<int:user_id>/"
                              "remove", "remove_notified_user_ui",
                              remove_notified_user_from_job, methods=("POST", ))
    app_instance.add_url_rule("/jobs/<int:job_id>",
                              "single_job_ui", single_job, methods=("GET", ))

    app_instance.add_url_rule("/jobs/<int:job_id>/tasks/<int:task_id>/logs/",
                              "logs_in_task_ui", logs_in_task, methods=("GET", ))

    app_instance.add_url_rule("/jobqueues/",
                              "jobqueues_index_ui", jobqueues, methods=("GET", ))
    app_instance.add_url_rule("/jobqueues/create",
                              "jobqueue_create_ui", jobqueue_create,
                              methods=("GET", "POST"))
    app_instance.add_url_rule("/jobqueues/<int:queue_id>",
                              "single_jobqueue_ui", jobqueue,
                              methods=("GET", "POST"))
    app_instance.add_url_rule("/jobqueues/<int:queue_id>/delete",
                              "delete_jobqueue_ui", delete_jobqueue,
                              methods=("POST", ))

    app_instance.add_url_rule("/jobtypes/",
                              "jobtypes_index_ui", jobtypes, methods=("GET", ))
    app_instance.add_url_rule("/jobtypes/<int:jobtype_id>",
                              "single_jobtype_ui", jobtype,
                              methods=("GET", "POST"))
    app_instance.add_url_rule("/jobtypes/<int:jobtype_id>/delete",
                              "remove_single_jobtype_ui", remove_jobtype,
                              methods=("POST", ))
    app_instance.add_url_rule("/jobtypes/<int:jobtype_id>/software_requirements/"
                              "<int:software_id>/delete",
                              "single_jobtype_remove_requirement_ui",
                              remove_jobtype_software_requirement,
                              methods=("POST", ))
    app_instance.add_url_rule("/jobtypes/<int:jobtype_id>/software_requirements/"
                              "add",
                              "single_jobtype_add_requirement_ui",
                              add_jobtype_software_requirement,
                              methods=("POST", ))
    app_instance.add_url_rule("/jobtypes/create", "jobtype_create_ui",
                              create_jobtype, methods=("GET", "POST"))

    app_instance.add_url_rule("/software/",
                              "software_index_ui", software, methods=("GET", ))
    app_instance.add_url_rule("/software/<int:software_id>",
                              "single_software_ui", software_item,
                              methods=("GET", ))
    app_instance.add_url_rule("/software/<int:software_id>/versions/"
                              "<int:version_id>/update_rank",
                              "version_update_rank_ui", update_version_rank,
                              methods=("POST", ))
    app_instance.add_url_rule("/software/<int:software_id>/versions/"
                              "<int:version_id>/remove",
                              "delete_single_version_ui",
                              remove_software_version, methods=("POST", ))
    app_instance.add_url_rule("/software/<int:software_id>/versions/create",
                              "add_single_version_ui",
                              add_software_version, methods=("POST", ))
    app_instance.add_url_rule("/software/create",
                              "add_single_software_ui",
                              add_software, methods=("POST", ))
    app_instance.add_url_rule("/software/<int:software_id>/delete",
                              "delete_single_software_ui",
                              remove_software, methods=("POST", ))


def load_api(app_instance, api_instance):
    """configures flask to serve the api endpoints"""
    from pyfarm.master.api.agents import (
        SingleAgentAPI, AgentIndexAPI, schema as agent_schema, TasksInAgentAPI)
    from pyfarm.master.api.software import (
        schema as software_schema, SoftwareIndexAPI, SingleSoftwareAPI,
        SoftwareVersionsIndexAPI, SingleSoftwareVersionAPI)
    from pyfarm.master.api.tags import (
        schema as tag_schema, TagIndexAPI, SingleTagAPI, AgentsInTagIndexAPI)
    from pyfarm.master.api.jobtypes import (
        schema as jobtypes_schema, JobTypeIndexAPI, SingleJobTypeAPI,
        JobTypeCodeAPI, JobTypeSoftwareRequirementsIndexAPI, VersionedJobTypeAPI,
        JobTypeSoftwareRequirementAPI, JobTypeVersionsIndexAPI)
    from pyfarm.master.api.jobs import (
        schema as job_schema, JobIndexAPI, SingleJobAPI, JobTasksIndexAPI,
        JobSingleTaskAPI, JobNotifiedUsersIndexAPI, JobSingleNotifiedUserAPI)
    from pyfarm.master.api.jobqueues import (
        schema as jobqueues_schema, JobQueueIndexAPI, SingleJobQueueAPI)
    from pyfarm.master.api.agent_updates import AgentUpdatesAPI
    from pyfarm.master.api.pathmaps import (
        schema as pathmap_schema, PathMapIndexAPI, SinglePathMapAPI)
    from pyfarm.master.api.tasklogs import (
        LogsInTaskAttemptsIndexAPI, SingleLogInTaskAttempt, TaskLogfileAPI)

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
    api_instance.add_url_rule(
        "/jobtypes/",
        view_func=JobTypeIndexAPI.as_view("jobtype_index_api"))
    api_instance.add_url_rule(
        "/jobs/",
        view_func=JobIndexAPI.as_view("job_index_api"))
    api_instance.add_url_rule(
        "/jobqueues/",
        view_func=JobQueueIndexAPI.as_view("jobqueue_index_api"))
    api_instance.add_url_rule(
        "/pathmaps/",
        view_func=PathMapIndexAPI.as_view("pathmap_index_api"))

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
    api_instance.add_url_rule(
        "/jobtypes/schema",
        "jobtypes_schema", view_func=jobtypes_schema, methods=("GET", ))
    api_instance.add_url_rule(
        "/jobs/schema",
        "jobs_schema", view_func=job_schema, methods=("GET", ))
    api_instance.add_url_rule(
        "/jobqueues/schema",
        "jobqueues_schema", view_func=jobqueues_schema, methods=("GET", ))
    api_instance.add_url_rule(
        "/pathmaps/schema",
        "pathmap_schema", view_func=pathmap_schema, methods=("GET", ))

    # specific item access
    api_instance.add_url_rule(
        "/tags/<string:tagname>",
        view_func=SingleTagAPI.as_view("single_tag_by_string_api"))
    api_instance.add_url_rule(
        "/tags/<int:tagname>",
        view_func=SingleTagAPI.as_view("single_tag_by_id_api"))
    api_instance.add_url_rule(
        "/agents/<uuid:agent_id>",
        view_func=SingleAgentAPI.as_view("single_agent_api"))
    api_instance.add_url_rule(
        "/software/<int:software_rq>",
        view_func=SingleSoftwareAPI.as_view("single_software_by_id_api"))
    api_instance.add_url_rule(
        "/software/<string:software_rq>",
        view_func=SingleSoftwareAPI.as_view("single_software_by_string_api"))

    api_instance.add_url_rule(
        "/jobtypes/<int:jobtype_name>",
        view_func=SingleJobTypeAPI.as_view("single_jobtype_by_id_api"))
    api_instance.add_url_rule(
        "/jobtypes/<string:jobtype_name>",
        view_func=SingleJobTypeAPI.as_view("single_jobtype_by_string_api"))

    api_instance.add_url_rule(
        "/jobs/<int:job_name>",
        view_func=SingleJobAPI.as_view("single_job_by_id_api"))
    api_instance.add_url_rule(
        "/jobs/<string:job_name>",
        view_func=SingleJobAPI.as_view("single_job_by_string_api"))

    api_instance.add_url_rule(
        "/jobqueues/<int:queue_rq>",
        view_func=SingleJobQueueAPI.as_view("single_jobqueue_by_id_api"))
    api_instance.add_url_rule(
        "/jobqueues/<string:queue_rq>",
        view_func=SingleJobQueueAPI.as_view("single_jobqueue_by_string_api"))

    api_instance.add_url_rule(
        "/pathmaps/<int:pathmap_id>",
        view_func=SinglePathMapAPI.as_view("single_pathmap_by_id_api"))

    # special case for jobype/code
    api_instance.add_url_rule(
        "/jobtypes/<int:jobtype_name>/versions/<int:version>/code",
        view_func=JobTypeCodeAPI.as_view("jobtype_by_id_code_api"))
    api_instance.add_url_rule(
        "/jobtypes/<string:jobtype_name>/versions/<int:version>/code",
        view_func=JobTypeCodeAPI.as_view("jobtype_by_string_code_api"))

    # versioned jobtypes
    api_instance.add_url_rule(
        "/jobtypes/<int:jobtype_name>/versions/<int:version>",
        view_func=VersionedJobTypeAPI.as_view("versioned_jobtype_by_id_api"))
    api_instance.add_url_rule(
        "/jobtypes/<string:jobtype_name>/versions/<int:version>",
        view_func=VersionedJobTypeAPI.as_view("versioned_jobtype_by_string_api"))

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

    # Jobtype versions
    api_instance.add_url_rule("/jobtypes/<int:jobtype_name>/versions/",
        view_func=JobTypeVersionsIndexAPI.as_view("jobtype_by_id_versions_api"))
    api_instance.add_url_rule("/jobtypes/<string:jobtype_name>/versions/",
        view_func=JobTypeVersionsIndexAPI.as_view(
            "jobtype_by_string_versions_api"))

    # Jobtype software requirements
    api_instance.add_url_rule(
        "/jobtypes/<int:jobtype_name>/software_requirements/",
        view_func=JobTypeSoftwareRequirementsIndexAPI.as_view(
            "jobtype_by_id_soft_rq_api"))
    api_instance.add_url_rule(
        "/jobtypes/<string:jobtype_name>/software_requirements/",
        view_func=JobTypeSoftwareRequirementsIndexAPI.as_view(
            "jobtype_by_string_soft_rq_api"))
    api_instance.add_url_rule(
        "/jobtypes/<int:jobtype_name>/software_requirements/<string:software>",
        view_func=JobTypeSoftwareRequirementAPI.as_view(
            "jobtype_by_id_single_soft_rq_api"))
    api_instance.add_url_rule(
        "/jobtypes/<string:jobtype_name>/software_requirements/"
        "<string:software>",
        view_func=JobTypeSoftwareRequirementAPI.as_view(
            "jobtype_by_string_single_soft_rq_api"))

    # Jobtype software requirements for specific versions
    api_instance.add_url_rule(
        "/jobtypes/<int:jobtype_name>/versions/<int:version>"
        "/software_requirements/",
        view_func=JobTypeSoftwareRequirementsIndexAPI.as_view(
            "versioned_jobtype_by_id_soft_rq_api"))
    api_instance.add_url_rule(
        "/jobtypes/<string:jobtype_name>/versions/<int:version>"
        "/software_requirements/",
        view_func=JobTypeSoftwareRequirementsIndexAPI.as_view(
            "versioned_jobtype_by_string_soft_rq_api"))

    # Tasks in jobs
    api_instance.add_url_rule(
        "/jobs/<int:job_name>/tasks/",
        view_func=JobTasksIndexAPI.as_view("job_by_id_tasks_index_api"))
    api_instance.add_url_rule(
        "/jobs/<string:job_name>/tasks/",
        view_func=JobTasksIndexAPI.as_view("job_by_string_tasks_index_api"))
    api_instance.add_url_rule(
        "/jobs/<int:job_name>/tasks/<int:task_id>",
        view_func=JobSingleTaskAPI.as_view("job_by_id_task_api"))
    api_instance.add_url_rule(
        "/jobs/<string:job_name>/tasks/<int:task_id>",
        view_func=JobSingleTaskAPI.as_view("job_by_string_task_api"))

    # Tasks in agents
    api_instance.add_url_rule(
        "/agents/<uuid:agent_id>/tasks/",
        view_func=TasksInAgentAPI.as_view("tasks_in_agent_api"))

    # Agent updates
    api_instance.add_url_rule(
        "/agents/updates/<string:version>",
        view_func=AgentUpdatesAPI.as_view("agent_updates_api"))

    # Notified users in jobs
    api_instance.add_url_rule(
        "/jobs/<int:job_name>/notified_users/",
        view_func=JobNotifiedUsersIndexAPI.as_view(
            "job_by_id_notified_index_api"))
    api_instance.add_url_rule(
        "/jobs/<string:job_name>/notified_users/",
        view_func=JobNotifiedUsersIndexAPI.as_view(
            "job_by_string_notified_index_api"))
    api_instance.add_url_rule(
        "/jobs/<int:job_name>/notified_users/<string:username>",
        view_func=JobSingleNotifiedUserAPI.as_view(
            "job_by_id_single_notified_api"))
    api_instance.add_url_rule(
        "/jobs/<string:job_name>/notified_users/<string:username>",
        view_func=JobSingleNotifiedUserAPI.as_view(
            "job_by_string_single_notified_api"))

    # Task logs
    api_instance.add_url_rule(
        "/jobs/<int:job_id>/tasks/<int:task_id>/attempts/<int:attempt>/logs/",
        view_func=LogsInTaskAttemptsIndexAPI.as_view("job_task_log_index_api"))
    api_instance.add_url_rule(
        "/jobs/<int:job_id>/tasks/<int:task_id>/attempts/<int:attempt>/logs/"
        "<string:log_identifier>",
        view_func=SingleLogInTaskAttempt.as_view("job_task_single_log_api"))
    api_instance.add_url_rule(
        "/jobs/<int:job_id>/tasks/<int:task_id>/attempts/<int:attempt>/logs/"
        "<string:log_identifier>/logfile",
        view_func=TaskLogfileAPI.as_view("task_log_file_api"))

    # register the api blueprint
    app_instance.register_blueprint(api_instance)


def load_master(app, api):
    """loads and attaches all endpoints needed to run the master"""
    load_error_handlers(app)
    load_index(app)
    load_user_interface(app)
    load_authentication(app)
    load_api(app, api)


def tables():  # pragma: no cover
    """
    Small script for basic table management and, eventually, some
    introspection as well.
    """
    parser = ArgumentParser(
        description="Creates PyFarm's tables")
    parser.add_argument(
        "--echo", action="store_true",
        help="If provided then echo the SQL queries being made")
    parser.add_argument(
        "--drop-all", action="store_true",
        help="If provided all tables will be dropped from the database "
             "before they are created.")
    parser.add_argument(
        "--no-create-tables", action="store_true",
        help="If provided then no tables will be created.")
    args = parser.parse_args()

    db.engine.echo = args.echo

    if db.engine.name == "sqlite" and db.engine.url.database == ":memory:":
        logger.info("Nothing to do, in memory sqlite database is being used")
        return

    if args.drop_all:
        db.drop_all()

    if not args.no_create_tables:
        try:
            db.create_all()
        except Exception as e:
            logger.error(
                "Failed to call create_all().  This may be an error or "
                "it may be something that can be ignored: %r", e)
        else:
            logger.info("Tables created or updated")


def run_master():  # pragma: no cover
    """Runs :func:`load_master` then runs the application"""
    from pyfarm.master.application import app, api

    parser = ArgumentParser()
    if app.debug:
        parser.add_argument("--drop-all", "-D", action="store_true",
                            help="drop the existing tables before starting")

    parser.add_argument("--create-all", "-C", action="store_true",
                        help="create all tables before starting")
    parser.add_argument("--confirm-drop")
    parser.add_argument("--allow-agent-loopback-addresses", action="store_true")
    parsed = parser.parse_args()

    if app.debug and parsed.drop_all:
        db.drop_all()

    if parsed.allow_agent_loopback_addresses:
        app.config.update(ALLOW_AGENT_LOOPBACK_ADDRESSES=True)

    if parsed.create_all:
        db.create_all()

    load_setup(app)
    load_master(app, api)

    if read_env_bool("PYFARM_DEV_LISTEN_ON_WILDCARD", False):
        app.run(host='0.0.0.0')
    else:
        app.run()


def create_app():
    """An entry point specifically for uWSGI or similar to use"""
    from pyfarm.master.application import app, api

    if read_env_bool("PYFARM_DEV_APP_DB_DROP_ALL", False):
        db.drop_all()

    if read_env_bool("PYFARM_DEV_APP_DB_CREATE_ALL", False):
        db.create_all()

    load_setup(app)
    load_master(app, api)
    return app


if read_env_bool("PYFARM_APP_INSTANCE", False):
    app = create_app()
