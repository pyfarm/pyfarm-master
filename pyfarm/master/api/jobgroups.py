# No shebang line, this module is meant to be imported
#
# Copyright 2015 Ambient Entertainment GmbH & Co. KG
# Copyright 2015 Oliver Palmer
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
Job Groups
----------

This module defines an API for managing and querying job groups
"""
try:
    from httplib import (
        OK, NOT_FOUND, CREATED, NO_CONTENT, BAD_REQUEST, CONFLICT)
except ImportError:  # pragma: no cover
    from http.client import (
        OK, NOT_FOUND, CREATED, NO_CONTENT, BAD_REQUEST, CONFLICT)

from flask.views import MethodView
from flask import g

from sqlalchemy import func, asc
from pyfarm.core.logger import getLogger
from pyfarm.core.enums import WorkState
from pyfarm.models.user import User
from pyfarm.models.jobtype import JobType
from pyfarm.models.job import Job
from pyfarm.models.task import Task
from pyfarm.models.jobgroup import JobGroup
from pyfarm.master.config import config
from pyfarm.master.utility import jsonify, validate_with_model
from pyfarm.master.application import db

logger = getLogger("api.jobgroups")

AUTOCREATE_USERS = config.get("autocreate_users")
AUTO_USER_EMAIL = config.get("autocreate_user_email")


def schema():
    """
    Returns the basic schema of :class:`.JobGroup`

    .. http:get:: /api/v1/jobgroups/schema HTTP/1.1

        **Request**

        .. sourcecode:: http

            GET /api/v1/jobgroups/schema HTTP/1.1
            Accept: application/json

        **Response**

        .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                "main_jobtype": "VARCHAR(64)",
                "title": "VARCHAR(255)",
                "user": "VARCHAR(255)",
                "id": "INTEGER"
            }

    :statuscode 200: no error
    """
    schema_dict = JobGroup.to_schema()

    # In the database, we are storing the user by id, but over the wire, we are
    # using the username to identify the user instead.
    schema_dict["user"] = "VARCHAR(%s)" % config.get("max_username_length")
    del schema_dict["user_id"]
    schema_dict["main_jobtype"] = \
        "VARCHAR(%s)" % config.get("job_type_max_name_length")
    del schema_dict["main_jobtype_id"]
    return jsonify(schema_dict), OK

class JobGroupIndexAPI(MethodView):
    @validate_with_model(JobGroup, ignore=["user", "main_jobtype"],
                         disallow=["user_id", "main_jobtype_id"])
    def post(self):
        """
        A ``POST`` to this endpoint will create a new job group.

        .. http:post:: /api/v1/jobgroups/ HTTP/1.1

            **Request**

            .. sourcecode:: http

                POST /api/v1/jobgroups/ HTTP/1.1
                Accept: application/json

                {
                    "title": "Test Group",
                    "user": "testuser",
                    "main_jobtype": "Test JobType"
                }


            **Response**

            .. sourcecode:: http

                HTTP/1.1 201 CREATED
                Content-Type: application/json

                {
                    "id": 2,
                    "jobs": [],
                    "user": "testuser",
                    "main_jobtype": "Test JobType",
                    "title": "Test Group"
                }

        :statuscode 201: a new job group was created
        :statuscode 400: there was something wrong with the request (such as
                         invalid columns being included)
        """
        username = g.json.pop("user")
        user = User.query.filter_by(username=username).first()
        if not user and AUTOCREATE_USERS:
            user = User(username=username)
            if AUTO_USER_EMAIL:
                user.email = AUTO_USER_EMAIL.format(username=username)
            db.session.add(user)
            logger.warning("User %s was autocreated on job group create",
                           username)
        elif not user:
            return (jsonify(
                error="User %s not found" % username), NOT_FOUND)

        jobtype_name = g.json.pop("main_jobtype")
        jobtype = JobType.query.filter_by(name=jobtype_name).first()
        if not jobtype:
            return (jsonify(
                error="Jobtype %s not found" % jobtype_name), NOT_FOUND)

        jobgroup = JobGroup(user=user, main_jobtype=jobtype, **g.json)
        db.session.add(jobgroup)
        db.session.commit()

        jobgroup_data = jobgroup.to_dict()
        jobgroup_data.pop("user_id", None)
        jobgroup_data.pop("main_jobtype_id", None)
        logger.info("Created job group %s: %r", jobgroup.title, jobgroup_data)

        return jsonify(jobgroup_data), CREATED

    def get(self):
        """
        A ``GET`` to this endpoint will return a list of known job groups.

        .. http:get:: /api/v1/jobgroups/ HTTP/1.1

            **Request**

            .. sourcecode:: http

                GET /api/v1/jobgroups/ HTTP/1.1
                Accept: application/json

            **Response**

            .. sourcecode:: http

                HTTP/1.1 200 OK
                Content-Type: application/json

                [
                    {
                        "id": 2,
                        "user": "testuser",
                        "main_jobtype": "Test JobType",
                        "title": "Test Group"
                    }
                ]

        :statuscode 200: no error
        """
        out = []
        for jobgroup in JobGroup.query:
            jobgroup_data = jobgroup.to_dict(
                unpack_relationships=["user", "main_jobtype"])
            jobgroup_data.pop("user_id", None)
            jobgroup_data.pop("main_jobtype_id", None)
            out.append(jobgroup_data)

        return jsonify(out), OK


class SingleJobGroupAPI(MethodView):
    def get(self, group_id):
        """
        A ``GET`` to this endpoint will return the requested job group

        .. http:get:: /api/v1/jobgroups/<int:id> HTTP/1.1

            **Request**

            .. sourcecode:: http

                GET /api/v1/jobgroups/2 HTTP/1.1
                Accept: application/json

            **Response**

            .. sourcecode:: http

                HTTP/1.1 200 OK
                Content-Type: application/json

                {
                    "id": 2,
                    "user": "testuser",
                    "main_jobtype": "Test JobType",
                    "jobs": [],
                    "title": "Test Group"
                }

        :statuscode 200: no error
        :statuscode 404: the requested job group was not found
        """
        jobgroup = JobGroup.query.filter_by(id=group_id).first()

        if not jobgroup:
            return (jsonify(error="Requested job group %s not found" % group_id),
                    NOT_FOUND)

        jobgroup_data = jobgroup.to_dict()
        jobgroup_data.pop("user_id", None)
        jobgroup_data.pop("main_jobtype_id", None)

        return jsonify(jobgroup_data), OK

    def post(self, group_id):
        """
        A ``POST`` to this endpoint will update the specified group with the data
        in the request.  Columns not specified in the request will be left as
        they are.

        .. http:post:: /api/v1/jobgroups/<int:id> HTTP/1.1

            **Request**

            .. sourcecode:: http

                POST /api/v1/jobgroups/2 HTTP/1.1
                Accept: application/json

                {
                    "user": "testuser2"
                }

            **Response**

            .. sourcecode:: http

                HTTP/1.1 201 OK
                Content-Type: application/json

                {
                    "id": 2,
                    "user": "testuser2",
                    "main_jobtype": "Test JobType",
                    "jobs": [],
                    "title": "Test Group"
                }

        :statuscode 200: the job group was updated
        :statuscode 400: there was something wrong with the request (such as
                         invalid columns being included)
        """
        jobgroup = JobGroup.query.filter_by(id=group_id).first()

        if not jobgroup:
            return (jsonify(error="Requested job group %s not found" % group_id),
                    NOT_FOUND)

        if "title" in g.json:
            jobgroup.title = g.json.pop("title")
        if "user" in g.json:
            username = g.json.pop("user")
            user = User.query.filter_by(username=username).first()
            if not user:
                return (jsonify(error="User %s not found" % username), NOT_FOUND)
            jobgroup.user = user
        if "main_jobtype" in g.json:
            jobtype_name = g.json.pop("main_jobtype")
            jobtype = JobType.query.filter_by(name=jobtype_name).first()
            if not jobtype:
                return (jsonify(error="Jobtype %s not found" % jobtype_name),
                        NOT_FOUND)
            jobgroup.main_jobtype = jobtype

        if g.json:
            return jsonify(error="Unkown columns: %s" % g.json), BAD_REQUEST

        db.session.add(jobgroup)
        db.session.commit()

        jobgroup_data = jobgroup.to_dict()
        jobgroup_data.pop("user_id", None)
        jobgroup_data.pop("main_jobtype_id", None)
        logger.info("Updated job group %s: %r", jobgroup.title, jobgroup_data)

        return jsonify(jobgroup_data), OK

    def delete(self, group_id):
        """
        A ``DELETE`` to this endpoint will delete the specified job group

        .. http:delete:: /api/v1/jobgroup/<int:id>

            **Request**

            .. sourcecode:: http

                DELETE /api/v1/jobgroups/1 HTTP/1.1
                Accept: application/json

            **Response**

            .. sourcecode:: http

                HTTP/1.1 204 NO_CONTENT

        :statuscode 204: the job group was deleted or didn't exist
        :statuscode 409: the job group cannot be deleted because it still
                         contains jobs
        """
        jobgroup = JobGroup.query.filter_by(id=group_id).first()

        if not jobgroup:
            return jsonify(), NO_CONTENT

        num_jobs = Job.query.filter_by(group=jobgroup).count()
        if num_jobs > 0:
            return (jsonify(error="Cannot delete: job group has jobs assigned"),
                    CONFLICT)

        db.session.delete(jobgroup)
        db.session.commit()
        logger.info("Deleted job group %s", jobgroup.title)

        return jsonify(), NO_CONTENT

class JobsInJobGroupIndexAPI(MethodView):
    def get(self, group_id):
        """
        A ``GET`` to this endpoint will return all jobs in the speicfied
        jobgroup.

        .. http:get:: /api/v1/jobgroups/<int:id>/jobs HTTP/1.1

            **Request**

            .. sourcecode:: http

                GET /api/v1/jobgroups/2/jobs HTTP/1.1
                Accept: application/json

            **Response**

            .. sourcecode:: http

                HTTP/1.1 200 OK
                Content-Type: application/json

                {
                    "jobs":
                        [
                            {
                            "id": "12345",
                            "title": "Test Job",
                            "state": "queued",
                            "jobtype_id": 5,
                            "jobtype": "Test Jobtype",
                            "tasks_queued": 5,
                            "tasks_running": 0,
                            "tasks_done": 0,
                            "tasks_failed": 0
                            }
                        ]
                }

        :statuscode 200: no error
        :statuscode 404: the requested job group was not found
        """
        jobgroup = JobGroup.query.filter_by(id=group_id).first()

        if not jobgroup:
            return (jsonify(error="Requested job group %s not found" % group_id),
                    NOT_FOUND)

        queued_count_query = db.session.query(
            Task.job_id, func.count('*').label('t_queued')).\
                filter(Task.state == None).group_by(Task.job_id).subquery()
        running_count_query = db.session.query(
            Task.job_id, func.count('*').label('t_running')).\
                filter(Task.state == WorkState.RUNNING).\
                    group_by(Task.job_id).subquery()
        done_count_query = db.session.query(
            Task.job_id, func.count('*').label('t_done')).\
                filter(Task.state == WorkState.DONE).\
                    group_by(Task.job_id).subquery()
        failed_count_query = db.session.query(
            Task.job_id, func.count('*').label('t_failed')).\
                filter(Task.state == WorkState.FAILED).\
                    group_by(Task.job_id).subquery()
        jobs_query = db.session.query(
            Job,
            func.coalesce(
                queued_count_query.c.t_queued,
                0).label('t_queued'),
            func.coalesce(
                running_count_query.c.t_running,
                0).label('t_running'),
            func.coalesce(
                done_count_query.c.t_done,
                0).label('t_done'),
            func.coalesce(
                failed_count_query.c.t_failed,
                0).label('t_failed')).\
            outerjoin(queued_count_query,
                      Job.id == queued_count_query.c.job_id).\
            outerjoin(running_count_query,
                      Job.id == running_count_query.c.job_id).\
            outerjoin(done_count_query, Job.id == done_count_query.c.job_id).\
            outerjoin(failed_count_query, Job.id == failed_count_query.c.job_id).\
            filter(Job.group == jobgroup).\
            order_by(asc(Job.time_submitted)).all()

        out = {"jobs": []}
        for job, t_queued, t_running, t_done, t_failed in jobs_query:
            out["jobs"].append(
                {"id": job.id,
                 "title": job.title,
                 "state": str(job.state) or "queued",
                 "jobtype_id": job.jobtype_version.jobtype_id,
                 "jobtype": job.jobtype_version.jobtype.name,
                 "tasks_queued": t_queued,
                 "tasks_running": t_running,
                 "tasks_done": t_done,
                 "tasks_failed": t_failed})

        return jsonify(out), OK
