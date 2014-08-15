# No shebang line, this module is meant to be imported
#
# Copyright 2013 Oliver Palmer
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
Task Logs
---------

This module defines an API for managing and querying logs belonging to tasks
"""

try:
    from httplib import OK, NOT_FOUND, CONFLICT, TEMPORARY_REDIRECT, CREATED
except ImportError:  # pragma: no cover
    from http.client import OK, NOT_FOUND, CONFLICT, TEMPORARY_REDIRECT, CREATED

import tempfile
from os import makedirs
from os.path import join, isfile, realpath
from errno import EEXIST

from flask.views import MethodView
from flask import g, redirect, send_file, request

from pyfarm.core.logger import getLogger
from pyfarm.core.config import read_env
from pyfarm.models.tasklog import TaskLog, TaskTaskLogAssociation
from pyfarm.models.task import Task
from pyfarm.master.application import db
from pyfarm.master.utility import jsonify, validate_with_model

logger = getLogger("api.tasklogs")

# TODO a temp directory might not be a good default for putting logs
LOGFILES_DIR = read_env(
    "PYFARM_AGENT_LOGFILES_DIR", join(tempfile.gettempdir(), "task_logs"))

try:
    makedirs(LOGFILES_DIR)
except OSError as e:  # pragma: no cover
    if e.errno != EEXIST:
        raise


class LogsInTaskAttemptsIndexAPI(MethodView):
    def get(self, job_id, task_id, attempt):
        task = Task.query.filter_by(id=task_id, job_id=job_id).first()
        if not task:
            return jsonify(error="Specified task not found"), NOT_FOUND

        association_objects = TaskTaskLogAssociation.query.filter(
            TaskTaskLogAssociation.task == task,
            TaskTaskLogAssociation.attempt == attempt)

        out = []
        for item in association_objects:
            log = item.log
            out.append({"identifier": log.identifier,
                        "created_on": log.created_on,
                        "agent_id": log.agent_id})

        return jsonify(out), OK

    @validate_with_model(TaskLog)
    def post(self, job_id, task_id, attempt):
        task = Task.query.filter_by(id=task_id, job_id=job_id).first()
        if not task:
            return jsonify(error="Specified task not found"), NOT_FOUND

        path = join(LOGFILES_DIR, g.json["identifier"])
        if not realpath(path).startswith(LOGFILES_DIR):
            return jsonify(error="Identifier is not acceptable"), BAD_REQUEST
        task_log = TaskLog.query.filter_by(
            identifier=g.json["identifier"]).first()
        if not task_log:
            task_log = TaskLog(**g.json)

        association = TaskTaskLogAssociation.query.filter_by(
            task=task, log=task_log, attempt=attempt).first()
        if association:
            return (jsonify(
                error="This log is already registered for this task"), CONFLICT)

        association = TaskTaskLogAssociation()
        association.task = task
        association.log = task_log
        association.attempt = attempt

        db.session.add(association)
        db.session.add(task_log)
        db.session.commit()

        logger.info("Registered task log %s with attempt %s for task %s",
                    task_log.identifier, attempt, task.id)

        return jsonify(task_log.to_dict(unpack_relationships=False))


class SingleLogInTaskAttempt(MethodView):
    def get(self, job_id, task_id, attempt, log_identifier):
        task = Task.query.filter_by(id=task_id, job_id=job_id).first()
        if not task:
            return jsonify(error="Specified task not found"), NOT_FOUND

        log = TaskLog.query.filter_by(identifier=log_identifier).first()
        if not log:
            return jsonify(error="Specified log not found"), NOT_FOUND

        association = TaskTaskLogAssociation.query.filter_by(
            task=task,
            log=log,
            attempt=attempt).first()
        if not association:
            return jsonify(error="Specified log not found in task"), NOT_FOUND

        return jsonify(log.to_dict(unpack_relationships=False))


class TaskLogfileAPI(MethodView):
    def get(self, job_id, task_id, attempt, log_identifier):
        task = Task.query.filter_by(id=task_id, job_id=job_id).first()
        if not task:
            return jsonify(error="Specified task not found"), NOT_FOUND

        log = TaskLog.query.filter_by(identifier=log_identifier).first()
        if not log:
            return jsonify(error="Specified log not found"), NOT_FOUND

        association = TaskTaskLogAssociation.query.filter_by(
            task=task,
            log=log,
            attempt=attempt).first()
        if not association:
            return jsonify(error="Specified log not found in task"), NOT_FOUND

        path = join(LOGFILES_DIR, log_identifier)
        if not realpath(path).startswith(LOGFILES_DIR):
            return jsonify(error="Identifier is not acceptable"), BAD_REQUEST

        if isfile(path):
            return send_file(path)
        else:
            agent = log.agent
            if not agent:
                return (jsonify(error="Logfile is not available on master and "
                                      "agent is not known"), NOT_FOUND)
            return redirect(agent.api_url() + "/task_logs/" + log_identifier,
                            TEMPORARY_REDIRECT)

    def put(self, job_id, task_id, attempt, log_identifier):
        task = Task.query.filter_by(id=task_id, job_id=job_id).first()
        if not task:
            return jsonify(error="Specified task not found"), NOT_FOUND

        log = TaskLog.query.filter_by(identifier=log_identifier).first()
        if not log:
            return jsonify(error="Specified log not found"), NOT_FOUND

        association = TaskTaskLogAssociation.query.filter_by(
            task=task,
            log=log,
            attempt=attempt).first()
        if not association:
            return jsonify(error="Specified log not found in task"), NOT_FOUND

        path = join(LOGFILES_DIR, log_identifier)
        if not realpath(path).startswith(LOGFILES_DIR):
            return jsonify(error="Identifier is not acceptable"), BAD_REQUEST

        with open(path, "wb+") as log_file:
            log_file.write(request.data)
        logger.info("Writing task log file for task %s, attempt %s to path %s",
                    task_id, attempt, path)

        return "", CREATED
