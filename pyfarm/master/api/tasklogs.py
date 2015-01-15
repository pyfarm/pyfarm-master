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
    from httplib import (
      OK, NOT_FOUND, CONFLICT, TEMPORARY_REDIRECT, CREATED, BAD_REQUEST,
      INTERNAL_SERVER_ERROR)
except ImportError:  # pragma: no cover
    from http.client import (
      OK, NOT_FOUND, CONFLICT, TEMPORARY_REDIRECT, CREATED, BAD_REQUEST,
      INTERNAL_SERVER_ERROR)

import tempfile
from gzip import GzipFile
from os import makedirs
from os.path import join, realpath
from errno import EEXIST

from flask.views import MethodView
from flask import g, redirect, send_file, request, Response

from pyfarm.core.logger import getLogger
from pyfarm.core.config import read_env
from pyfarm.models.tasklog import TaskLog, TaskTaskLogAssociation
from pyfarm.models.task import Task
from pyfarm.master.application import db
from pyfarm.master.utility import jsonify, validate_with_model, isuuid

logger = getLogger("api.tasklogs")

# TODO a temp directory might not be a good default for putting logs
LOGFILES_DIR = read_env(
    "PYFARM_LOGFILES_DIR", join(tempfile.gettempdir(), "task_logs"))

try:
    makedirs(LOGFILES_DIR)
except OSError as e:  # pragma: no cover
    if e.errno != EEXIST:
        raise


class LogsInTaskAttemptsIndexAPI(MethodView):
    def get(self, job_id, task_id, attempt):
        """
        A ``GET`` to this endpoint will return a list of all known logs that are
        associated with this attempt at running this task

        .. http:get:: /api/v1/jobs/<job_id>/tasks/<task_id>/attempts/<attempt>/logs/ HTTP/1.1

            **Request**

            .. sourcecode:: http

                GET /api/v1/jobs/4/tasks/1300/attempts/5/logs/ HTTP/1.1
                Accept: application/json

            **Response**

            .. sourcecode:: http

                HTTP/1.1 200 OK
                Content-Type: application/json

                [
                    {
                        "agent_id": "3087ada4-290a-45b0-8c1a-21db4cd284fc",
                        "created_on": "2014-09-03T10:58:59.754880",
                        "identifier": "2014-09-03_10-58-59_4_4ee02475335911e4a935c86000cbf5fb.csv"
                    }
                ]

        :statuscode 200: no error
        :statuscode 404: the specified task was not found
        """
        task = Task.query.filter_by(id=task_id, job_id=job_id).first()
        if not task:
            return jsonify(task_id=task_id, job_id=job_id,
                           error="Specified task not found"), NOT_FOUND

        association_objects = TaskTaskLogAssociation.query.filter(
            TaskTaskLogAssociation.task == task,
            TaskTaskLogAssociation.attempt == attempt)

        out = []
        for item in association_objects:
            log = item.log
            out.append({"identifier": log.identifier,
                        "created_on": log.created_on,
                        "agent_id": str(log.agent_id)})

        return jsonify(out), OK

    @validate_with_model(TaskLog, type_checks={"agent_id": isuuid})
    def post(self, job_id, task_id, attempt):
        """
        A ``POST`` to this endpoint will register a new logfile with the given
        attempt at running the given task

        A logfile has an identifier which must be unique in the system.  If two
        tasks get assigned a logfile with the same id, it is considered to be the
        same log.

        .. http:post:: /api/v1/jobs/<job_id>/tasks/<task_id>/attempts/<attempt>/logs/ HTTP/1.1

            **Request**

            .. sourcecode:: http

                POST /api/v1/jobs/4/tasks/1300/attempts/5/logs/ HTTP/1.1
                Content-Type: application/json

                {
                    "identifier": "2014-09-03_10-58-59_4_4ee02475335911e4a935c86000cbf5fb.csv",
                    "agent_id": "2dc2cb5a-35da-41d6-8864-329c0d7d5391"
                }

            **Response**

            .. sourcecode:: http

                HTTP/1.1 201 CREATED
                Content-Type: application/json

                {
                    "identifier": "2014-09-03_10-58-59_4_4ee02475335911e4a935c86000cbf5fb.csv",
                    "agent_id": "2dc2cb5a-35da-41d6-8864-329c0d7d5391",
                    "created_on": "2014-09-03T10:59:05.103005",
                    "id": 148
                }


        :statuscode 201: the association between this task attempt and logfile
                         has been created
        :statuscode 400: there was something wrong with the request (such as
                         invalid columns being included)
        :statuscode 404: the specified task does not exist
        :statuscode 409: the specified log was already registered on the
                         specified task
        """
        task = Task.query.filter_by(id=task_id, job_id=job_id).first()
        if not task:
            return jsonify(task_id=task_id, job_id=job_id,
                           error="Specified task not found"), NOT_FOUND

        path = realpath(join(LOGFILES_DIR, g.json["identifier"]))
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
                log=task_log, attempt=attempt, task_id=task_id,
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

        return jsonify(task_log.to_dict(unpack_relationships=False)), CREATED


class SingleLogInTaskAttempt(MethodView):
    def get(self, job_id, task_id, attempt, log_identifier):
        """
        A ``GET`` to this endpoint will return metadata about the specified
        logfile

        .. http:get:: /api/v1/jobs/<job_id>/tasks/<task_id>/attempts/<attempt>/logs/<log_identifier> HTTP/1.1

            **Request**

            .. sourcecode:: http

                GET /api/v1/jobs/4/tasks/1300/attempts/5/logs/2014-09-03_10-58-59_4_4ee02475335911e4a935c86000cbf5fb.csv HTTP/1.1
                Accept: application/json

            **Response**

            .. sourcecode:: http

                HTTP/1.1 200 OK
                Content-Type: application/json

                {
                    "id": 147,
                    "identifier": "2014-09-03_10-58-59_4_4ee02475335911e4a935c86000cbf5fb.csv",
                    "created_on": "2014-09-03T10:58:59.754880",
                    "agent_id": "836ce137-6ad4-443f-abb9-94c4465ff87c"
                }

        :statuscode 200: no error
        :statuscode 404: task or logfile not found
        """
        task = Task.query.filter_by(id=task_id, job_id=job_id).first()
        if not task:
            return jsonify(task_id=task_id, job_id=job_id,
                           error="Specified task not found"), NOT_FOUND

        log = TaskLog.query.filter_by(identifier=log_identifier).first()
        if not log:
            return jsonify(task_id=task_id, job_id=job_id,
                           error="Specified log not found"), NOT_FOUND

        association = TaskTaskLogAssociation.query.filter_by(
            task=task,
            log=log,
            attempt=attempt).first()
        if not association:
            return jsonify(task_id=task.id, log=log.identifier,
                           error="Specified log not found in task"), NOT_FOUND

        return jsonify(log.to_dict(unpack_relationships=False))


class TaskLogfileAPI(MethodView):
    def get(self, job_id, task_id, attempt, log_identifier):
        """
        A ``GET`` to this endpoint will return the actual logfile or a redirect
        to it.

        .. http:get:: /api/v1/jobs/<job_id>/tasks/<task_id>/attempts/<attempt>/logs/<log_identifier>/logfile HTTP/1.1

            **Request**

            .. sourcecode:: http

                GET /api/v1/jobs/4/tasks/1300/attempts/5/logs/2014-09-03_10-58-59_4_4ee02475335911e4a935c86000cbf5fb.csv/logfile HTTP/1.1
                Accept: text/csv

            **Response**

            .. sourcecode:: http

                HTTP/1.1 200 OK
                Content-Type: text/csv

                <Content of the logfile>

        :statuscode 200: no error
        :statuscode 307: The logfile can be found in another location at this
                         point in time. Independent future requests for the same
                         logfile should continue using the original URL
        :statuscode 400: the specified logfile identifier is not acceptable
        :statuscode 404: task or logfile not found
        """
        task = Task.query.filter_by(id=task_id, job_id=job_id).first()
        if not task:
            return jsonify(task_id=task_id, log=log_identifier,
                           error="Specified task not found"), NOT_FOUND

        log = TaskLog.query.filter_by(identifier=log_identifier).first()
        if not log:
            return jsonify(task_id=task_id, log=log_identifier,
                           error="Specified log not found"), NOT_FOUND

        association = TaskTaskLogAssociation.query.filter_by(
            task=task,
            log=log,
            attempt=attempt).first()
        if not association:
            return jsonify(task_id=task.id, log=log.identifier,
                           error="Specified log not found in task"), NOT_FOUND

        path = realpath(join(LOGFILES_DIR, log_identifier))
        if not realpath(path).startswith(LOGFILES_DIR):
            return jsonify(error="Identifier is not acceptable"), BAD_REQUEST

        try:
            logfile = open(path, "rb")
            return send_file(logfile)
        except IOError:
            try:
                compressed_logfile = GzipFile("%s.gz" % path, "rb")
                def logfile_generator():
                    eof = False
                    while not eof:
                        out = compressed_logfile.read(4096) # 4096 == mempage
                        eof = len(out) == 0
                        yield out
                return Response(logfile_generator(), mimetype="text/csv")
            except IOError:
                agent = log.agent
                if not agent:
                    return (jsonify(
                        path=path, log=log_identifier,
                        error="Logfile is not available on master and agent "
                              "is not known"), NOT_FOUND)
                return redirect(agent.api_url() + "/task_logs/" +
                                log_identifier, TEMPORARY_REDIRECT)

    def put(self, job_id, task_id, attempt, log_identifier):
        """
        A ``PUT`` to this endpoint will upload the request's body as the
        specified logfile

        .. http:put:: /api/v1/jobs/<job_id>/tasks/<task_id>/attempts/<attempt>/logs/<log_identifier>/logfile HTTP/1.1

            **Request**

            .. sourcecode:: http

                PUT /api/v1/jobs/4/tasks/1300/attempts/5/logs/2014-09-03_10-58-59_4_4ee02475335911e4a935c86000cbf5fb.csv/logfile HTTP/1.1

                <content of the logfile>

            **Response**

            .. sourcecode:: http

                HTTP/1.1 201 CREATED

        :statuscode 201: lofile was uploaded
        :statuscode 400: the specified logfile identifier is not acceptable
        :statuscode 404: task or logfile not found
        """
        task = Task.query.filter_by(id=task_id, job_id=job_id).first()
        if not task:
            return jsonify(task_id=task_id, log=log_identifier,
                           error="Specified task not found"), NOT_FOUND

        log = TaskLog.query.filter_by(identifier=log_identifier).first()
        if not log:
            return jsonify(task_id=task_id, log=log_identifier,
                           error="Specified log not found"), NOT_FOUND

        association = TaskTaskLogAssociation.query.filter_by(
            task=task,
            log=log,
            attempt=attempt).first()
        if not association:
            return jsonify(task_id=task_id, log=log.identifier,
                           error="Specified log not found in task"), NOT_FOUND

        path = realpath(join(LOGFILES_DIR, log_identifier))
        if not realpath(path).startswith(LOGFILES_DIR):
            return jsonify(error="Identifier is not acceptable"), BAD_REQUEST

        logger.info("Writing task log file for task %s, attempt %s to path %s",
                    task_id, attempt, path)

        try:
            with open(path, "wb+") as log_file:
                log_file.write(request.data)
        except (IOError, OSError) as e:
            logger.error("Could not write task log file: %s (%s)", e.errno,
                         e.strerror)
            return (jsonify(error="Could not write file %s to disk: %s"
                                  % (path, e)),
                    INTERNAL_SERVER_ERROR)

        return "", CREATED
