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
        OK, BAD_REQUEST, NOT_FOUND, INTERNAL_SERVER_ERROR)
except ImportError:  # pragma: no cover
    from http.client import (
        OK, BAD_REQUEST, NOT_FOUND, INTERNAL_SERVER_ERROR)

from flask.views import MethodView
from flask import g, request, current_app

from pyfarm.core.logger import getLogger
from pyfarm.core.enums import STRING_TYPES
from pyfarm.models.core.cfg import MAX_JOBTYPE_LENGTH
from pyfarm.models.jobtype import JobType, JobTypeVersion
from pyfarm.models.task import Task
from pyfarm.models.job import Job
from pyfarm.models.software import (
    Software, SoftwareVersion, JobSoftwareRequirement)
from pyfarm.master.application import db
from pyfarm.master.utility import jsonify, validate_with_model

logger = getLogger("api.jobs")


class ObjectNotFound(Exception):
    pass


def parse_requirements(requirements_list):
    """
    Takes a list dicts specifying a software and optional min- and max-versions
    and returns a list of :class:`JobRequirement` objects.

    Raises TypeError if the input was not as expected or ObjectNotFound if a
    referenced software of or version was not found.

    :param list requirements_list:
        A list of of dicts specifying a software and optionally min_version
        and/or max_version.
    """
    if not isinstance(requirements_list, list):
        raise TypeError("software_requirements must be a list")

    out = []
    for req in requirements_list:
        if not isinstance(req, dict):
            raise TypeError("Every software_requirement must be a dict")

        requirement = JobSoftwareRequirement()
        software_name = req.pop("software", None)
        if not software_name:
            raise TypeError("Software requirement does not specify a software.")
        software = Software.query.filter_by(software=software_name).first()
        if not software:
            raise ObjectNotFound("Software %s not found" % software_name)
        requirement.software = software

        min_version_str = req.pop("min_version", None)
        if min_version_str:
            min_version = SoftwareVersion.query.filter(
                SoftwareVersion.software == software,
                SoftwareVersion.version == min_version_str).first()
            if not min_version:
                raise ObjectNotFound("Version %s of software %s not found" %
                                        (software_name, min_version_str))
            requirement.min_version = min_version

        max_version_str = req.pop("max_version", None)
        if max_version_str:
            max_version = SoftwareVersion.query.filter(
                SoftwareVersion.software == software,
                SoftwareVersion.version == max_version_str).first()
            if not max_version:
                raise ObjectNotFound("Version %s of software %s not found" %
                                     (software_name, max_version_str))
            requirement.max_version = max_version

        if req:
            raise TypeError("Unexpected keys in software requirement: %r" %
                            req.keys())

        out.append(requirement)
    return out


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
                "batch": "INTEGER",
                "by": "NUMERIC(10, 4)",
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
                "title": "VARCHAR(255)",
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
                         ignore=["start", "end", "jobtype", "jobtype_version"],
                         disallow=["jobtype_version_id", "time_submitted",
                                   "time_started", "time_finished"])
    def post(self):
        """
        A ``POST`` to this endpoint will submit a new job.

        .. http:post:: /api/v1/jobs/ HTTP/1.1

            **Request**

            .. sourcecode:: http

                POST /api/v1/jobs/ HTTP/1.1
                Accept: application/json

                {
                    "end": 2.0,
                    "title": "Test Job 2",
                    "jobtype": "TestJobType",
                    "data": {
                        "foo": "bar"
                    },
                    "software_requirements": [
                        {
                        "software": "blender"
                        }
                    ],
                    "start": 1.0
                }

            **Response**

            .. sourcecode:: http

                HTTP/1.1 200 OK
                Content-Type: application/json

                {
                    "time_finished": null,
                    "time_started": null,
                    "end": 2.0,
                    "time_submitted": "2014-03-06 15:49:51.890145",
                    "jobtype_version": {
                        "version": 1,
                        "jobtype": "TestJobType"
                    },
                    "start": 1.0,
                    "priority": 0,
                    "state": "queued",
                    "parents": [],
                    "tasks_done": [],
                    "hidden": false,
                    "project_id": null,
                    "ram_warning": null,
                    "title": "Test Job 2",
                    "tags": [],
                    "user": null,
                    "by": 1.0,
                    "data": {
                        "foo": "bar"
                    },
                    "ram_max": null,
                    "notes": "",
                    "batch": 1,
                    "project": null,
                    "environ": null,
                    "requeue": 3,
                    "tasks": [
                        {
                            "state": "queued",
                            "frame": 1.0,
                            "id": 3
                        },
                        {
                            "state": "queued",
                            "frame": 2.0,
                            "id": 4
                        }
                    ],
                    "software_requirements": [
                        {
                            "min_version": null,
                            "max_version": null,
                            "max_version_id": null,
                            "software_id": 1,
                            "min_version_id": null,
                            "software": "blender"
                        }
                    ],
                    "tasks_queued": [
                        {
                            "state": "queued",
                            "frame": 1.0,
                            "id": 3
                        },
                        {
                            "state": "queued",
                            "frame": 2.0,
                            "id": 4
                        }
                    ],
                    "id": 2,
                    "ram": 32,
                    "cpus": 1,
                    "tasks_failed": [],
                    "children": []
                }

        :statuscode 201: a new job item was created
        :statuscode 400: there was something wrong with the request (such as
                            invalid columns being included)
        :statuscode 404: a referenced object, like a software or software
                            version, does not exist
        :statuscode 409: a conflicting job already exists
        """
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

        if "software_requirements" in g.json:
            try:
                software_requirements = parse_requirements(
                    g.json["software_requirements"])
            except TypeError as e:
                return jsonify(error=e.args), BAD_REQUEST
            except ObjectNotFound as e:
                return jsonify(error=e.args), NOT_FOUND
            del g.json["software_requirements"]

        if "start" in g.json:
            del g.json["start"]
        if "end" in g.json:
            del g.json["end"]
        job = Job(**g.json)
        job.jobtype_version = jobtype_version
        job.software_requirements = software_requirements

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
        while cur_frame <= end:
            task = Task()
            task.job = job
            task.frame = cur_frame
            db.session.add(task)
            cur_frame += by

        db.session.add(job)
        db.session.add_all(software_requirements)
        db.session.commit()
        job_data = job.to_dict()
        job_data["start"] = start
        job_data["end"] = min(cur_frame, end)
        del job_data["jobtype_version_id"]
        logger.info("Created new job %s", job_data)

        return jsonify(job_data), OK

    def get(self):
        """
        A ``GET`` to this endpoint will return a list of all jobs.

        .. http:get:: /api/v1/jobs/ HTTP/1.1

            **Request**

            .. sourcecode:: http

                GET /api/v1/jobs/ HTTP/1.1
                Accept: application/json

            **Response**

            .. sourcecode:: http

                HTTP/1.1 200 OK
                Content-Type: application/json

                [
                    {
                        "title": "Test Job",
                        "state": "queued",
                        "id": 1
                    },
                    {
                        "title": "Test Job 2",
                        "state": "queued",
                        "id": 2
                    }
                ]

        :statuscode 200: no error
        """
        out = []
        q = db.session.query(Job.id, Job.title, Job.state)

        for id, title, state in q:
            out.append({"id": id, "title": title, "state": str(state)})

        return jsonify(out), OK


class SingleJobAPI(MethodView):
    def get(self, job_name):
        """
        A ``GET`` to this endpoint will return the specified job, by name or id.

        .. http:get:: /api/v1/jobtypes/<str:tagname> HTTP/1.1

            **Request**

            .. sourcecode:: http

                GET /api/v1/jobts/Test%20Job%202 HTTP/1.1
                Accept: application/json

            **Response**

            .. sourcecode:: http

                HTTP/1.1 200 OK
                Content-Type: application/json

                {
                    "ram_warning": null,
                    "title": "Test Job",
                    "state": "queued",
                    "environ": null,
                    "user": null,
                    "priority": 0,
                    "time_finished": null,
                    "start": 2.0,
                    "id": 1,
                    "notes": "",
                    "ram": 32,
                    "tags": [],
                    "hidden": false,
                    "data": {
                        "foo": "bar"
                    },
                    "software_requirements": [
                        {
                            "software": "blender",
                            "software_id": 1,
                            "min_version": null,
                            "max_version": null,
                            "min_version_id": null,
                            "max_version_id": null
                        }
                    ],
                    "batch": 1,
                    "time_started": null,
                    "time_submitted": "2014-03-06 15:40:58.335259",
                    "requeue": 3,
                    "end": 4.0,
                    "parents": [],
                    "cpus": 1,
                    "ram_max": null,
                    "children": [],
                    "by": 1.0,
                    "project_id": null
                }

        :statuscode 200: no error
        :statuscode 404: job not found
        """
        if isinstance(job_name, STRING_TYPES):
            job = Job.query.filter_by(title=job_name).first()
        else:
            job = Job.query.filter_by(id=job_name).first()

        if not job:
            return jsonify(error="Job not found"), NOT_FOUND

        job_data = job.to_dict(unpack_relationships=["tags",
                                                     "data",
                                                     "software_requirements",
                                                     "parents",
                                                     "children"])

        first_task = Task.query.filter_by(job=job).order_by("frame asc").first()
        last_task = Task.query.filter_by(job=job).order_by("frame desc").first()

        if not first_task or not last_task:
            return (jsonify(error="Job does not have any tasks"),
                    INTERNAL_SERVER_ERROR)

        job_data["start"] = first_task.frame
        job_data["end"] = last_task.frame
        del job_data["jobtype_version_id"]

        return jsonify(job_data), OK

    def post(self, job_name):
        """
        A ``POST`` to this endpoint will update the specified job with the data
        in the request.  Columns not specified in the request will be left as
        they are.
        If the "start", "end" or "by" columns are updated, tasks will be created
        or deleted as required.

        .. http:post:: /api/v1/jobs/[<str:name>|<int:id>] HTTP/1.1

            **Request**

            .. sourcecode:: http

                PUT /api/v1/jobtypes/TestJobType HTTP/1.1
                Accept: application/json

                {
                    "start": 2.0
                }

            **Response**

            .. sourcecode:: http

                HTTP/1.1 201 CREATED
                Content-Type: application/json

                {
                    "end": 4.0,
                    "children": [],
                    "time_started": null,
                    "tasks_failed": [],
                    "project_id": null,
                    "id": 1,
                    "tasks": [
                        {
                            "state": "queued",
                            "id": 2,
                            "frame": 2.0
                        },
                        {
                            "state": "queued",
                            "id": 5,
                            "frame": 3.0
                        },
                        {
                            "state": "queued",
                            "id": 6,
                            "frame": 4.0
                        }
                    ],
                    "software_requirements": [
                        {
                            "software": "blender",
                            "min_version": null,
                            "max_version_id": null,
                            "software_id": 1,
                            "max_version": null,
                            "min_version_id": null
                        }
                    ],
                    "tags": [],
                    "environ": null,
                    "requeue": 3,
                    "start": 2.0,
                    "ram_warning": null,
                    "title": "Test Job",
                    "batch": 1,
                    "time_submitted": "2014-03-06 15:40:58.335259",
                    "ram_max": null,
                    "user": null,
                    "project": null,
                    "jobtype_version": {
                        "jobtype": "TestJobType",
                        "version": 1
                    },
                    "notes": "",
                    "data": {
                        "foo": "bar"
                    },
                    "ram": 32,
                    "parents": [],
                    "hidden": false,
                    "tasks_queued": [
                        {
                            "state": "queued",
                            "id": 2,
                            "frame": 2.0
                        },
                        {
                            "state": "queued",
                            "id": 5,
                            "frame": 3.0
                        },
                        {
                            "state": "queued",
                            "id": 6,
                            "frame": 4.0
                        }
                    ],
                    "tasks_done": [],
                    "priority": 0,
                    "cpus": 1,
                    "state": "queued",
                    "by": 1.0,
                    "time_finished": null
                }

        :statuscode 200: the job was updated
        :statuscode 400: there was something wrong with the request (such as
                            invalid columns being included)
        """
        if isinstance(job_name, STRING_TYPES):
            job = Job.query.filter_by(title=job_name).first()
        else:
            job = Job.query.filter_by(id=job_name).first()

        if not job:
            return jsonify(error="Job not found"), NOT_FOUND

        if "start" in g.json or "end" in g.json or "by" in g.json:
            old_first_task = Task.query.filter_by(job=job).order_by(
                "frame asc").first()
            old_last_task = Task.query.filter_by(job=job).order_by(
                "frame desc").first()

            if not old_first_task or not old_last_task:
                return (jsonify(error="Job does not have any tasks"),
                        INTERNAL_SERVER_ERROR)

            json = loads(request.data.decode(), parse_float=Decimal)
            start = Decimal(json.pop("start", old_first_task.frame))
            end = Decimal(json.pop("end", old_last_task.frame))
            by = Decimal(json.pop("by", job.by))

            if end < start:
                return jsonify(error="end must be greater than start")

            required_frames = []
            cur_frame = start
            while cur_frame <= end:
                required_frames.append(cur_frame)
                cur_frame += by

            existing_tasks = Task.query.filter_by(job=job).all()
            frames_to_create = required_frames
            for task in existing_tasks:
                if task.frame not in required_frames:
                    db.session.delete(task)
                else:
                    frames_to_create.remove(task.frame)

            for frame in frames_to_create:
                task = Task()
                task.job = job
                task.frame = frame
                db.session.add(task)

        if "time_started" in g.json:
            return (jsonify(error="\"time_started\" cannot be set manually"),
                    BAD_REQUEST)

        if "time_finished" in g.json:
            return (jsonify(error="\"time_finished\" cannot be set manually"),
                    BAD_REQUEST)

        if "time_submitted" in g.json:
            return (jsonify(error="\"time_submitted\" cannot be set manually"),
                    BAD_REQUEST)

        if "jobtype_version_id" in g.json:
            return (jsonify(error=
                           "\"jobtype_version_id\" cannot be set manually"),
                    BAD_REQUEST)

        for name in Job.types().columns:
            if name in g.json:
                col_type = getattr(Job.__class__, name)
                value = g.json.pop(name)
                if not isinstance(value, col_type.type):
                    return jsonify(error="Column \"%s\" is of type %r, but we "
                                   "expected %r" % (name,
                                                    type(value),
                                                    col_type.type))
                setattr(Job, name, value)

        g.json.pop("start", None)
        g.json.pop("end", None)
        if g.json:
            return jsonify(error="Unknown columns: %r" % g.json), BAD_REQUEST

        db.session.add(job)
        db.session.commit()
        job_data = job.to_dict()
        job_data["start"] = start
        job_data["end"] = min(cur_frame, end)
        del job_data["jobtype_version_id"]

        logger.info("Job %s has been updated to: %r", job.id, job_data)

        return jsonify(job_data), OK

class JobTasksIndexAPI(MethodView):
    def get(self, job_name):
        """
        A ``GET`` to this endpoint will return a list of all tasks in a job.

        .. http:get:: /api/v1/jobs/[<str:name>|<int:id>]/tasks HTTP/1.1

            **Request**

            .. sourcecode:: http

                GET /api/v1/jobs/Test%20Job%202/tasks/ HTTP/1.1
                Accept: application/json

            **Response**

            .. sourcecode:: http

                HTTP/1.1 200 OK
                Content-Type: application/json

                [
                    {
                        "hidden": false,
                        "id": 3,
                        "attempts": 0,
                        "priority": 0,
                        "time_started": null,
                        "time_submitted": "2014-03-06 15:49:51.892228",
                        "frame": 1.0,
                        "time_finished": null,
                        "job_id": 2,
                        "project_id": null,
                        "state": "queued",
                        "agent_id": null
                    },
                    {
                        "hidden": false,
                        "id": 4,
                        "attempts": 0,
                        "priority": 0,
                        "time_started": null,
                        "time_submitted": "2014-03-06 15:49:51.892925",
                        "frame": 2.0,
                        "time_finished": null,
                        "job_id": 2,
                        "project_id": null,
                        "state": "queued",
                        "agent_id": null
                    }
                ]

        :statuscode 200: no error
        """
        if isinstance(job_name, STRING_TYPES):
            job = Job.query.filter_by(title=job_name).first()
        else:
            job = Job.query.filter_by(id=job_name).first()

        if not job:
            return jsonify(error="Job not found"), NOT_FOUND

        tasks_q = Task.query.filter_by(job=job).order_by("frame asc")
        out = [x.to_dict(unpack_relationships=False) for x in tasks_q]

        return jsonify(out), OK
