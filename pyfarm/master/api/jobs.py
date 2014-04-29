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
----

This module defines an API for managing and querying jobs
"""

from decimal import Decimal
from json import loads

try:
    from httplib import (
        OK, BAD_REQUEST, NOT_FOUND, INTERNAL_SERVER_ERROR, CREATED)
except ImportError:  # pragma: no cover
    from http.client import (
        OK, BAD_REQUEST, NOT_FOUND, INTERNAL_SERVER_ERROR, CREATED)

from flask.views import MethodView
from flask import g, request

from sqlalchemy.sql import func, or_, and_

from pyfarm.core.logger import getLogger
from pyfarm.core.enums import STRING_TYPES, NUMERIC_TYPES
from pyfarm.scheduler.tasks import assign_tasks
from pyfarm.models.core.cfg import MAX_JOBTYPE_LENGTH
from pyfarm.models.jobtype import JobType, JobTypeVersion
from pyfarm.models.task import Task
from pyfarm.models.job import Job
from pyfarm.models.software import (
    Software, SoftwareVersion, JobSoftwareRequirement)
from pyfarm.master.application import db
from pyfarm.master.utility import jsonify, validate_with_model

RANGE_TYPES = NUMERIC_TYPES[:-1] + (Decimal, )

logger = getLogger("api.jobs")

# Load model mappings once per process
TASK_MODEL_MAPPINGS = Task.types().mappings


class ObjectNotFound(Exception):
    pass


def parse_requirements(requirements):
    """
    Takes a list dicts specifying a software and optional min- and max-versions
    and returns a list of :class:`JobRequirement` objects.

    Raises TypeError if the input was not as expected or ObjectNotFound if a
    referenced software of or version was not found.

    :param list requirements:
        A list of of dicts specifying a software and optionally min_version
        and/or max_version.

    :raises TypeError:
        Raised if ``requirements`` is not a list or if an entry in
        ``requirements`` is not a dictionary.

    :raises ValueError:
        Raised if there's a problem with the content of at least one of the
        requirement dictionaries.

    :raises ObjectNotFound:
        Raised if the referenced software or version was not found
    """
    if not isinstance(requirements, list):
        raise TypeError("software_requirements must be a list")

    out = []
    for entry in requirements:
        if not isinstance(entry, dict):
            raise TypeError("Every software_requirement must be a dict")

        requirement = JobSoftwareRequirement()
        software_name = entry.pop("software", None)
        if software_name is None:
            raise ValueError("Software requirement does not specify a software.")
        software = Software.query.filter_by(software=software_name).first()
        if not software:
            raise ObjectNotFound("Software %s not found" % software_name)
        requirement.software = software

        min_version_str = entry.pop("min_version", None)
        if min_version_str is not None:
            min_version = SoftwareVersion.query.filter(
                SoftwareVersion.software == software,
                SoftwareVersion.version == min_version_str).first()
            if not min_version:
                raise ObjectNotFound("Version %s of software %s not found" %
                                        (software_name, min_version_str))
            requirement.min_version = min_version

        max_version_str = entry.pop("max_version", None)
        if max_version_str is not None:
            max_version = SoftwareVersion.query.filter(
                SoftwareVersion.software == software,
                SoftwareVersion.version == max_version_str).first()
            if not max_version:
                raise ObjectNotFound("Version %s of software %s not found" %
                                     (software_name, max_version_str))
            requirement.max_version = max_version

        if entry:
            raise ValueError("Unexpected keys in software requirement: %r" %
                            entry.keys())

        out.append(requirement)
    return out


def schema():
    """
    Returns the basic schema of :class:`.Job`

    .. http:get:: /api/v1/jobtypes/schema HTTP/1.1

        **Request**

        .. sourcecode:: http

            GET /api/v1/jobs/schema HTTP/1.1
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
                         type_checks={"by": lambda x: isinstance(
                             x, RANGE_TYPES)},
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

                HTTP/1.1 201 CREATED
                Content-Type: application/json

                {
                    "time_finished": null,
                    "time_started": null,
                    "end": 2.0,
                    "time_submitted": "2014-03-06T15:40:58.335259",
                    "jobtype_version": 1,
                    "jobtype": "TestJobType",
                    "start": 1.0,
                    "priority": 0,
                    "state": "queued",
                    "parents": [],
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
                    "id": 2,
                    "ram": 32,
                    "cpus": 1,
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

        software_requirements = []
        if "software_requirements" in g.json:
            try:
                software_requirements = parse_requirements(
                    g.json["software_requirements"])
            except (TypeError, ValueError) as e:
                return jsonify(error=e.args), BAD_REQUEST
            except ObjectNotFound as e:
                return jsonify(error=e.args), NOT_FOUND
            del g.json["software_requirements"]

        g.json.pop("start", None)
        g.json.pop("end", None)
        job = Job(**g.json)
        job.jobtype_version = jobtype_version
        job.software_requirements = software_requirements

        custom_json = loads(request.data.decode(), parse_float=Decimal)
        if "start" not in custom_json or "end" not in custom_json:
            return jsonify(error="`start` or `end` not specified"), BAD_REQUEST
        start = custom_json["start"]
        end = custom_json["end"]
        if (not isinstance(start, RANGE_TYPES) or
            not isinstance(end, RANGE_TYPES)):
            return (jsonify(error="`start` and `end` need to be of type decimal "
                                    "or int"), BAD_REQUEST)

        if not end >= start:
            return (jsonify(error="`end` must be larger than or equal to start"),
                    BAD_REQUEST)

        by = custom_json.pop("by", Decimal("1.0"))
        if not isinstance(by, RANGE_TYPES):
            return (jsonify(error="`by` needs to be of type decimal or int"),
                    BAD_REQUEST)
        job.by = by

        current_frame = start
        while current_frame <= end:
            task = Task()
            task.job = job
            task.frame = current_frame
            task.priority = job.priority
            db.session.add(task)
            current_frame += by

        db.session.add(job)
        db.session.add_all(software_requirements)
        db.session.commit()
        job_data = job.to_dict(unpack_relationships=["tags",
                                                     "data",
                                                     "software_requirements",
                                                     "parents",
                                                     "children"])
        job_data["start"] = start
        job_data["end"] = min(current_frame, end)
        del job_data["jobtype_version_id"]
        job_data["jobtype"] = job.jobtype_version.jobtype.name
        job_data["jobtype_version"] = job.jobtype_version.version
        if job.state is None:
            num_assigned_tasks = Task.query.filter(Task.job == job,
                                                   Task.agent != None).count()
            if num_assigned_tasks > 0:
                job_data["state"] = "running"
            else:
                job_data["state"] = "queued"

        logger.info("Created new job %r", job_data)
        assign_tasks.delay()

        return jsonify(job_data), CREATED

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
        subq = db.session.query(
            Task.job_id,
            func.count(Task.id).label('assigned_tasks_count')).\
                filter(Task.agent_id != None).group_by(Task.job_id).subquery()
        q = db.session.query(Job.id, Job.title, Job.state,
                             subq.c.assigned_tasks_count).\
            outerjoin(subq, Job.id == subq.c.job_id)

        for id, title, state, assigned_tasks_count in q:
            data = {"id": id, "title": title}
            if state is None and not assigned_tasks_count:
                data["state"] = "queued"
            elif state is None:
                data["state"] = "assigned"
            else:
                data["state"] = str(state)
            out.append(data)

        return jsonify(out), OK


class SingleJobAPI(MethodView):
    def get(self, job_name):
        """
        A ``GET`` to this endpoint will return the specified job, by name or id.

        .. http:get:: /api/v1/jobs/[<str:name>|<int:id>] HTTP/1.1

            **Request**

            .. sourcecode:: http

                GET /api/v1/jobs/Test%20Job%202 HTTP/1.1
                Accept: application/json

            **Response**

            .. sourcecode:: http

                HTTP/1.1 200 OK
                Content-Type: application/json

                {
                    "ram_warning": null,
                    "title": "Test Job",
                    "state": "queued",
                    "jobtype_version": 1,
                    "jobtype": "TestJobType",
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
                    "time_submitted": "2014-03-06T15:40:58.335259",
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

        if not first_task or not last_task: # pragma: no cover
            return (jsonify(error="Job does not have any tasks"),
                    INTERNAL_SERVER_ERROR)

        job_data["start"] = first_task.frame
        job_data["end"] = last_task.frame
        job_data["jobtype"] = job.jobtype_version.jobtype.name
        job_data["jobtype_version"] = job.jobtype_version.version
        if job.state is None:
            num_assigned_tasks = Task.query.filter(Task.job == job,
                                                   Task.agent != None).count()
            if num_assigned_tasks > 0:
                job_data["state"] = "running"
            else:
                job_data["state"] = "queued"

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

                PUT /api/v1/jobs/Test%20Type HTTP/1.1
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
                    "jobtype_version": 1,
                    "jobtype": "TestJobType",
                    "time_started": null,
                    "tasks_failed": [],
                    "project_id": null,
                    "id": 1,
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
                    "time_submitted": "2014-03-06T15:40:58.335259",
                    "ram_max": null,
                    "user": null,
                    "notes": "",
                    "data": {
                        "foo": "bar"
                    },
                    "ram": 32,
                    "parents": [],
                    "hidden": false,
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

            if not old_first_task or not old_last_task: # pragma: no cover
                return (jsonify(error="Job does not have any tasks"),
                        INTERNAL_SERVER_ERROR)

            json = loads(request.data.decode(), parse_float=Decimal)
            start = Decimal(json.pop("start", old_first_task.frame))
            end = Decimal(json.pop("end", old_last_task.frame))
            by = Decimal(json.pop("by", job.by))

            if end < start:
                return jsonify(error="`end` must be greater than or equal to "
                                     "`start`"), BAD_REQUEST

            required_frames = []
            current_frame = start
            while current_frame <= end:
                required_frames.append(current_frame)
                current_frame += by

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
                task.priority = job.priority
                db.session.add(task)

        if "time_started" in g.json:
            return (jsonify(error="`time_started` cannot be set manually"),
                    BAD_REQUEST)

        if "time_finished" in g.json:
            return (jsonify(error="`time_finished` cannot be set manually"),
                    BAD_REQUEST)

        if "time_submitted" in g.json:
            return (jsonify(error="`time_submitted` cannot be set manually"),
                    BAD_REQUEST)

        if "jobtype_version_id" in g.json:
            return (jsonify(error=
                           "`jobtype_version_id` cannot be set manually"),
                    BAD_REQUEST)

        for name in Job.types().columns:
            if name in g.json:
                type = Job.types().mappings[name]
                value = g.json.pop(name)
                if not isinstance(value, type):
                    return jsonify(error="Column `%s` is of type %r, but we "
                                   "expected %r" % (name,
                                                    type(value),
                                                    type))
                setattr(job, name, value)

        if "software_requirements" in g.json:
            try:
                job.software_requirements = parse_requirements(
                    g.json["software_requirements"])
            except (TypeError, ValueError) as e:
                return jsonify(error=e.args), BAD_REQUEST
            except ObjectNotFound as e:
                return jsonify(error=e.args), NOT_FOUND
            del g.json["software_requirements"]

        g.json.pop("start", None)
        g.json.pop("end", None)
        if g.json:
            return jsonify(error="Unknown columns: %r" % g.json), BAD_REQUEST

        db.session.add(job)
        db.session.commit()
        job_data = job.to_dict(unpack_relationships=["tags",
                                                     "data",
                                                     "software_requirements",
                                                     "parents",
                                                     "children"])
        job_data["start"] = start
        job_data["end"] = min(current_frame, end)
        del job_data["jobtype_version_id"]
        job_data["jobtype"] = job.jobtype_version.jobtype.name
        job_data["jobtype_version"] = job.jobtype_version.version
        if job.state is None:
            num_assigned_tasks = Task.query.filter(Task.job == job,
                                                   Task.agent != None).count()
            if num_assigned_tasks > 0:
                job_data["state"] = "running"
            else:
                job_data["state"] = "queued"

        logger.info("Job %s has been updated to: %r", job.id, job_data)
        assign_tasks.delay()

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
                        "time_submitted": "2014-03-06T15:49:51.892228",
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
                        "time_submitted": "2014-03-06T15:49:51.892925",
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
        out = []
        for task in tasks_q:
            data = task.to_dict(unpack_relationships=False)
            if task.state == None and task.agent == None:
                data["state"] = "queued"
            elif task.state == None:
                data["state"] = "assigned"
            out.append(data)

        return jsonify(out), OK


class JobSingleTaskAPI(MethodView):
    def post(self, job_name, task_id):
        """
        A ``POST`` to this endpoint will update the specified task with the data
        in the request.  Columns not specified in the request will be left as
        they are.
        The agent will use this endpoint to inform the master of its progress.

        .. http:post:: /api/v1/jobs/[<str:name>|<int:id>]/tasks/<int:task_id> HTTP/1.1

            **Request**

            .. sourcecode:: http

                PUT /api/v1/job/Test%20Job/tasks/1 HTTP/1.1
                Accept: application/json

                {
                    "state": "running"
                }

            **Response**

            .. sourcecode:: http

                HTTP/1.1 201 CREATED
                Content-Type: application/json

                {
                    "time_finished": null,
                    "agent": null,
                    "attempts": 0,
                    "frame": 2.0,
                    "agent_id": null,
                    "job": {
                        "id": 1,
                        "title": "Test Job"
                    },
                    "time_started": null,
                    "state": "running",
                    "project_id": null,
                    "id": 2,
                    "time_submitted": "2014-03-06T15:40:58.338904",
                    "project": null,
                    "parents": [],
                    "job_id": 1,
                    "hidden": false,
                    "children": [],
                    "priority": 0
                }

        :statuscode 200: the task was updated
        :statuscode 400: there was something wrong with the request (such as
                            invalid columns being included)
        """
        task_query = Task.query.filter_by(id=task_id)
        if isinstance(job_name, STRING_TYPES):
            task_query.filter(Task.job.has(Job.title == job_name))
        else:
            task_query.filter(Task.job.has(Job.id == job_name))
        task = task_query.first()

        if not task:
            return jsonify(error="Task not found"), NOT_FOUND

        if "time_started" in g.json:
            return (jsonify(error="`time_started` cannot be set manually"),
                    BAD_REQUEST)

        if "time_finished" in g.json:
            return (jsonify(error="`time_finished` cannot be set manually"),
                    BAD_REQUEST)

        if "time_submitted" in g.json:
            return (jsonify(error="`time_submitted` cannot be set manually"),
                    BAD_REQUEST)

        if "job_id" in g.json:
            return jsonify(error="`job_id` cannot be changed"), BAD_REQUEST

        if "frame" in g.json:
            return jsonify(error="`frame` cannot be changed"), BAD_REQUEST

        new_state = g.json.pop("state", None)
        if new_state is not None and new_state is not task.state:
            logger.info("Task %s of job %s: state transition \"%s\" -> \"%s\"",
                        task_id, task.job.title, task.state, new_state)
            task.state = new_state
            db.session.flush()
            job = task.job
            num_active_tasks = db.session.query(Task).\
                filter(Task.job == job, or_(Task.state == None, and_(
                             Task.state != "done",
                             Task.state != "failed"))).count()
            if num_active_tasks == 0:
                num_failed_tasks = db.session.query(
                    Task).filter(Task.job == job,
                                  Task.state == "failed").count()
                if num_failed_tasks == 0:
                    logger.info("Job %s: state transition \"%s\" -> \"done\"",
                                job.title, job.state)
                    job.state = "done"
                else:
                    logger.info("Job %s: state transition \"%s\" -> \"failed\"",
                                job.title, job.state)
                    job.state = "failed"
                db.session.add(job)

        # Iterate over all keys in the request
        for key in list(g.json):
            if key in TASK_MODEL_MAPPINGS:
                value = g.json.pop(key)
                expected_types = TASK_MODEL_MAPPINGS[key]

                # incorrect type for `value`
                if not isinstance(value, expected_types):
                    return (jsonify(
                        error="Column %r is of type %r but we expected "
                              "type(s) %r" % (key, type(value),
                                              expected_types)), BAD_REQUEST)

                # correct type for `value`
                setattr(task, key, value)

        if g.json:
            return (jsonify(error="Unknown columns in request: %r" % g.json),
                    BAD_REQUEST)

        db.session.add(task)
        db.session.commit()

        task_data = task.to_dict()
        if task.state is None and task.agent is None:
            task_data["state"] = "queued"
        elif task.state is None:
            task_data["state"] = "assigned"
        logger.info("Task %s of job %s has been updated, new data: %r",
                    task_id, task.job.title, task_data)
        assign_tasks.delay()
        return jsonify(task_data), OK

    def get(self, job_name, task_id):
        """
        A ``GET`` to this endpoint will return the requested task

        .. http:get:: /api/v1/jobs/[<str:name>|<int:id>]/tasks/<int:task_id> HTTP/1.1

            **Request**

            .. sourcecode:: http

                GET /api/v1/jobs/Test%20Job%202/tasks/1 HTTP/1.1
                Accept: application/json

            **Response**

            .. sourcecode:: http

                HTTP/1.1 200 OK
                Content-Type: application/json

                {
                    "time_finished": null,
                    "agent": null,
                    "attempts": 0,
                    "frame": 2.0,
                    "agent_id": null,
                    "job": {
                        "id": 1,
                        "title": "Test Job"
                    },
                    "time_started": null,
                    "state": "running",
                    "project_id": null,
                    "id": 2,
                    "time_submitted": "2014-03-06T15:40:58.338904",
                    "project": null,
                    "parents": [],
                    "job_id": 1,
                    "hidden": false,
                    "children": [],
                    "priority": 0
                }

        :statuscode 200: no error
        """
        task_query = Task.query.filter_by(id=task_id)
        if isinstance(job_name, STRING_TYPES):
            task_query.filter(Task.job.has(Job.title == job_name))
        else:
            task_query.filter(Task.job.has(Job.id == job_name))
        task = task_query.first()

        if not task:
            return jsonify(error="Task not found"), NOT_FOUND

        task_data = task.to_dict()
        if task.state is None and task.agent is None:
            task_data["state"] = "queued"
        elif task.state is None:
            task_data["state"] = "assigned"

        return jsonify(task_data), OK
