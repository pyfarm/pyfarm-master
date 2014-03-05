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
Jobs
--------

This module defines an API for managing and querying jobs
"""

from copy import copy
from decimal import Decimal
from datetime import datetime
from json import loads, dumps

try:
    from httplib import (
        OK, BAD_REQUEST, NOT_FOUND)
except ImportError:  # pragma: no cover
    from http.client import (
        OK, BAD_REQUEST, NOT_FOUND)

from flask.views import MethodView
from flask import g, request, current_app

from pyfarm.core.logger import getLogger
from pyfarm.core.enums import STRING_TYPES
from pyfarm.models.core.cfg import MAX_JOBTYPE_LENGTH
from pyfarm.models.jobtype import JobType, JobTypeVersion
from pyfarm.models.task import Task
from pyfarm.models.job import Job
from pyfarm.master.application import db
from pyfarm.master.utility import jsonify, validate_with_model

logger = getLogger("api.jobs")


def schema():
    """
    Returns the basic schema of :class:`.JobType`

    .. http:get:: /api/v1/jobtypes/schema HTTP/1.1

        **Request**

        .. sourcecode:: http

            GET /api/v1/jobtypes/schema HTTP/1.1
            Accept: application/json

        **Response**

        .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
            "args": "JSONList",
            "attempts": "INTEGER",
            "batch": "INTEGER",
            "by": "NUMERIC(10, 4)",
            "cmd": "VARCHAR(64)",
            "cpus": "INTEGER",
            "data": "JSONDict",
            "end": "NUMERIC(10,4)",
            "environ": "JSONDict",
            "hidden": "BOOLEAN",
            "id": "INTEGER",
            "jobtype": "VARCHAR(64)",
            "jobtype_version": "INTEGER",
            "notes": "TEXT",
            "priority": "INTEGER",
            "project_id": "INTEGER",
            "ram": "INTEGER",
            "ram_max": "INTEGER",
            "ram_warning": "INTEGER",
            "requeue": "INTEGER",
            "start": "NUMERIC(10,4)",
            "state": "WorkStateEnum",
            "time_finished": "DATETIME",
            "time_started": "DATETIME",
            "time_submitted": "DATETIME",
            "user": "VARCHAR(255)"
            }

    :statuscode 200: no error
    """
    schema_dict = Job.to_schema()
    # These two columns are not part of the actual database model, but will be
    # dynamically computed by the api
    schema_dict["start"] = "NUMERIC(10,4)"
    schema_dict["end"] = "NUMERIC(10,4)"
    # In the database, we are storing the jobtype_version_id, but over the wire,
    # we are using the jobtype's name plus version to identify it
    del schema_dict["jobtype_version_id"]
    schema_dict["jobtype"] = "VARCHAR(%s)" % MAX_JOBTYPE_LENGTH
    schema_dict["jobtype_version"] = "INTEGER"
    return jsonify(schema_dict), OK


class JobIndexAPI(MethodView):
    @validate_with_model(Job,
                         type_checks = {"by": lambda x: isinstance(
                             x, (int, float, Decimal))},
                         ignore=["start", "end", "jobtype",
                                 "jobtype_version", "jobtype_version_id"])
    def post(self):
        if "jobtype" not in g.json:
            return jsonify(error="No jobtype specified"), BAD_REQUEST
        if not isinstance(g.json["jobtype"], STRING_TYPES):
            return jsonify(error="jobtype must be of type string"), BAD_REQUEST

        q = JobTypeVersion.query.filter(
                JobTypeVersion.jobtype.has(JobType.name == g.json["jobtype"]))
        del g.json["jobtype"]
        if "jobtype_version" in g.json:
            if not isinstance(g.json["jobtype_version"], int):
                return (jsonify(error="jobtype_version must be of type int"),
                        BAD_REQUEST)
            q = q.filter(JobTypeVersion.version == g.json["jobtype_version"])
            del g.json["jobtype_version"]
        jobtype_version = q.order_by("version desc").first()

        if not jobtype_version:
            return jsonify("Jobtype or version not found"), NOT_FOUND

        if "start" in g.json:
            del g.json["start"]
        if "end" in g.json:
            del g.json["end"]
        job = Job(**g.json)
        job.jobtype_version = jobtype_version

        json = loads(request.data.decode(), parse_float=Decimal)
        if "start" not in json or "end" not in json:
            return jsonify(error="start or end not specified"), BAD_REQUEST
        start = json["start"]
        end = json["end"]
        if (not isinstance(start, (Decimal, int)) or
            not isinstance(end, (Decimal, int))):
            return (jsonify(error="start and end need to be of type decimal or "
                            "int"), BAD_REQUEST)

        if not end >= start:
            return (jsonify(error="end must be larger than or equal to start"),
                    BAD_REQUEST)

        by = json.pop("by", Decimal("1.0"))
        if not isinstance(by, (Decimal, int)):
            return (jsonify(error="\"by\" needs to be of type decimal or int"),
                    BAD_REQUEST)
        job.by = by

        cur_frame = copy(start)
        num_tasks = 0
        while cur_frame <= end:
            task = Task()
            task.job = job
            task.frame = cur_frame
            db.session.add(task)
            cur_frame += by
            num_tasks += 1

        db.session.add(job)
        db.session.commit()
        job_data = job.to_dict()
        job_data["start"] = start
        job_data["end"] = min(cur_frame, end)
        logger.info("Created new job %s", job_data)

        return jsonify(job_data), OK
