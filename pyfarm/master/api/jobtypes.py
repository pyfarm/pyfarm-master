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
Jobtypes
--------

This module defines an API for managing and querying jobtypes
"""

try:
    from httplib import (
        OK, CREATED, CONFLICT, NOT_FOUND)
except ImportError:  # pragma: no cover
    from http.client import (
        OK, CREATED, CONFLICT, NOT_FOUND)

from flask import g, Response, request
from flask.views import MethodView

from sqlalchemy import or_

from pyfarm.core.logger import getLogger
from pyfarm.core.enums import STRING_TYPES
from pyfarm.models.software import JobTypeSoftwareRequirement
from pyfarm.models.jobtype import JobType
from pyfarm.master.application import db
from pyfarm.master.utility import jsonify, validate_with_model

logger = getLogger("api.jobtypes")


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
                "batch_contiguous": "BOOLEAN",
                "classname": "VARCHAR(64)",
                "code": "TEXT",
                "description": "TEXT",
                "id": "INTEGER",
                "max_batch": "INTEGER",
                "name": "VARCHAR(64)",
                "sha1": "VARCHAR(40)"
            }

    :statuscode 200: no error
    """
    return jsonify(JobType.to_schema()), OK


class JobTypeIndexAPI(MethodView):
    @validate_with_model(JobType, ignore=("sha1",), disallow=("jobs",))
    def post(self):
        """
        A ``POST`` to this endpoint will create a new jobtype.

        .. http:post:: /api/v1/jobtypes/ HTTP/1.1

            **Request**

            .. sourcecode:: http

                POST /api/v1/jobtypes/ HTTP/1.1
                Accept: application/json

                {
                    "name": "TestJobType",
                    "description": "Jobtype for testing inserts and queries",
                    "code": "\nfrom pyfarm.jobtypes.core.jobtype import "
                            "JobType\n\nclass TestJobType(JobType):\n"
                            "    def get_command(self):\n"
                            "        return \"/usr/bin/touch\"\n\n"
                            "    def get_arguments(self):\n"
                            "           return [os.path.join("
                            "self.assignment_data[\"job\"][\"data\"][\"path\"], "
                            "\"%04d\" % self.assignment_data[\"tasks\"]"
                            "[0][\"frame\"])]\n"
                }

            **Response**

            .. sourcecode:: http

                HTTP/1.1 200 OK
                Content-Type: application/json

                {
                    "id": 1,
                    "batch_contiguous": true,
                    "software_requirements": [],
                    "max_batch": 1,
                    "name": "TestJobType",
                    "classname": null,
                    "description": "Jobtype for testing inserts and queries",
                    "code": "\nfrom pyfarm.jobtypes.core.jobtype import "
                            "JobType\n\nclass TestJobType(JobType):\n"
                            "    def get_command(self):\n"
                            "        return \"/usr/bin/touch\"\n\n"
                            "    def get_arguments(self):\n"
                            "           return [os.path.join("
                            "self.assignment_data[\"job\"][\"data\"][\"path\"], "
                            "\"%04d\" % self.assignment_data[\"tasks\"]"
                            "[0][\"frame\"])]\n",
                    "sha1": "849d564da815f8bdfd9de0aaf4ac4fe6e9013015",
                    "jobs": []
                }

        :statuscode 201: a new jobtype item was created
        :statuscode 400: there was something wrong with the request (such as
                            invalid columns being included)
        :statuscode 409: a conflicting jobtype already exists
        """
        jobtype = JobType.query.filter_by(name=g.json["name"]).first()

        if jobtype:
            return (jsonify(error="Jobtype %s already exixts" %
                            g.json["name"]), CONFLICT)

        jobtype = JobType(**g.json)

        db.session.add(jobtype)
        db.session.commit()
        jobtype_data = jobtype.to_dict()
        logger.info("created jobtype %s: %r", jobtype.name, jobtype_data)

        return jsonify(jobtype_data), CREATED

    def get(self):
        """
        A ``GET`` to this endpoint will return a list of registered jobtypes.

        .. http:get:: /api/v1/jobtypes/ HTTP/1.1

            **Request**

            .. sourcecode:: http

                GET /api/v1/jobtypes/ HTTP/1.1
                Accept: application/json

            **Response**

            .. sourcecode:: http

                HTTP/1.1 200 OK
                Content-Type: application/json

                [
                    {
                    "id": 1,
                    "name": "TestJobType"
                    }
                ]

        :statuscode 200: no error
        """
        out = []
        q = db.session.query(JobType.id, JobType.name)

        for id, name in q:
            out.append({"id": id, "name": name})

        return jsonify(out), OK


class SingleJobTypeAPI(MethodView):
    def get(self, jobtype_name):
        """
        A ``GET`` to this endpoint will return the referenced jobtype, by name,
        id, or sha1 sum.

        .. http:get:: /api/v1/jobtypes/<str:tagname> HTTP/1.1

            **Request**

            .. sourcecode:: http

                GET /api/v1/jobtypes/TestJobType HTTP/1.1
                Accept: application/json

            **Response**

            .. sourcecode:: http

                HTTP/1.1 200 OK
                Content-Type: application/json

                {
                    "batch_contiguous": true,
                    "classname": null,
                    "code": "\nfrom pyfarm.jobtypes.core.jobtype import "
                            "JobType\n\nclass TestJobType(JobType):\n"
                            "    def get_command(self):\n"
                            "        return \"/usr/bin/touch\"\n\n"
                            "    def get_arguments(self):\n"
                            "           return [os.path.join("
                            "self.assignment_data[\"job\"][\"data\"][\"path\"], "
                            "\"%04d\" % self.assignment_data[\"tasks\"]"
                            "[0][\"frame\"])]\n",
                    "id": 1,
                    "jobs": [],
                    "max_batch": 1,
                    "name": "TestJobType", 
                    "sha1": "849d564da815f8bdfd9de0aaf4ac4fe6e9013015",
                    "software_requirements": []
                }

        :statuscode 200: no error
        :statuscode 404: tag not found
        """
        if isinstance(jobtype_name, STRING_TYPES):
            jobtype = JobType.query.filter(
                or_(JobType.name == jobtype_name,
                    JobType.sha1 == jobtype_name)).first()
        else:
            jobtype = JobType.query.filter_by(id=jobtype_name).first()

        if not jobtype:
            return (jsonify(error="JobType %s not found" % jobtype_name),
                    NOT_FOUND)

        # For some reason, sqlalchemy sometimes returns this column as bytes
        # instead of string.  jsonify cannot decode that.
        if PY3 and isinstance(jobtype.code, bytes):
            jobtype.code = jobtype.code.decode()

        return jsonify(jobtype.to_dict()), OK

    @validate_with_model(JobType, ignore=("sha1",), disallow=("jobs",))
    def put(self, jobtype_name):
        """
        A ``PUT`` to this endpoint will create a new jobtag under the given URI.
        If a jobtype already exists under that URI, it will be deleted, then
        recreated.

        You should only call this by id for overwriting an existing jobtype or if
        you have a reserved jobtype id. There is currently no way to reserve a
        jobtype id.

        .. http:put:: /api/v1/jobtypes/<str:tagname> HTTP/1.1

            **Request**

            .. sourcecode:: http

                PUT /api/v1/jobtypes/TestJobType HTTP/1.1
                Accept: application/json

                {
                    "name": "TestJobType",
                    "description": "Jobtype for testing inserts and queries",
                    "code": "\nfrom pyfarm.jobtypes.core.jobtype import "
                            "JobType\n\nclass TestJobType(JobType):\n"
                            "    def get_command(self):\n"
                            "        return \"/usr/bin/touch\"\n\n"
                            "    def get_arguments(self):\n"
                            "           return [os.path.join("
                            "self.assignment_data[\"job\"][\"data\"][\"path\"], "
                            "\"%04d\" % self.assignment_data[\"tasks\"]"
                            "[0][\"frame\"])]\n"
                }

            **Response**

            .. sourcecode:: http

                HTTP/1.1 201 CREATED
                Content-Type: application/json

                {
                    "batch_contiguous": true,
                    "classname": null,
                    "code": "\nfrom pyfarm.jobtypes.core.jobtype import "
                            "JobType\n\nclass TestJobType(JobType):\n"
                            "    def get_command(self):\n"
                            "        return \"/usr/bin/touch\"\n\n"
                            "    def get_arguments(self):\n"
                            "           return [os.path.join("
                            "self.assignment_data[\"job\"][\"data\"][\"path\"], "
                            "\"%04d\" % self.assignment_data[\"tasks\"]"
                            "[0][\"frame\"])]\n",
                    "id": 1,
                    "jobs": [],
                    "max_batch": 1,
                    "name": "TestJobType", 
                    "description": "Jobtype for testing inserts and queries",
                    "sha1": "849d564da815f8bdfd9de0aaf4ac4fe6e9013015",
                    "software_requirements": []
                }

        :statuscode 201: a new tag was created
        :statuscode 400: there was something wrong with the request (such as
                            invalid columns being included)
        """
        if isinstance(jobtype_name, STRING_TYPES):
            jobtype = JobType.query.filter(
                or_(JobType.name == jobtype_name,
                    JobType.sha1 == jobtype_name)).first()
        else:
            jobtype = JobType.query.filter_by(id=jobtype_name).first()

        if jobtype:
            logger.debug(
                "jobtype %s will be replaced with %r on commit",
                jobtype.name, g.json)
            db.session.delete(jobtype)
            db.session.flush()

        jobtype = JobType(**g.json)

        db.session.add(jobtype)
        db.session.commit()
        jobtype_data = jobtype.to_dict()
        logger.info("created jobtype %s in put: %r", jobtype.name, jobtype_data)

        return jsonify(jobtype_data), CREATED

    def delete(self, jobtype_name):
        """
        A ``DELETE`` to this endpoint will delete the requested jobtyoe

        .. http:delete:: /api/v1/jobtypes/<str:jobtype_name> HTTP/1.1

            **Request**

            .. sourcecode:: http

                DELETE /api/v1/jobtypes/TestJobType HTTP/1.1
                Accept: application/json

            **Response**

            .. sourcecode:: http

                HTTP/1.1 204 NO_CONTENT

        :statuscode 204: the jobtype was deleted or didn't exist
        """
        if isinstance(jobtype_name, STRING_TYPES):
            jobtype = JobType.query.filter(
                or_(JobType.name == jobtype_name,
                    JobType.sha1 == jobtype_name)).first()
        else:
            jobtype = JobType.query.filter_by(id=jobtype_name).first()

        if jobtype:
            logger.debug("jobtype %s will be deleted",jobtype.name, g.json)
            db.session.delete(jobtype)
            db.session.commit()
            logger.info("jobtype %s has been deleted",jobtype.name, g.json)

        return jsonify(), NO_CONTENT


class JobTypeCodeAPI(MethodView):
    def get(self, jobtype_name):
        """
        A ``GET`` to this endpoint will return just the python code for this
        jobtype

        .. http:get:: /api/v1/jobtypes/<str:jobtype>/code HTTP/1.1

            **Request**

            .. sourcecode:: http

                GET /api/v1/jobtypes/TestJobType/code HTTP/1.1
                Accept: text/x-python

            **Response**

            .. sourcecode:: http

                HTTP/1.1 200 OK
                Content-Type: text/x-python

                from pyfarm.jobtypes.core.jobtype import JobType

                class TestJobType(JobType):
                    def get_command(self):
                        return "/usr/bin/touch"

                    def get_arguments(self):
                        return [os.path.join(
                            self.assignment_data["job"]["data"]["path"], "%04d" %
                            self.assignment_data["tasks"][0]["frame"])]

        :statuscode 200: no error
        :statuscode 404: jobtype not found
        """
        if isinstance(jobtype_name, STRING_TYPES):
            jobtype = JobType.query.filter(
                or_(JobType.name == jobtype_name,
                    JobType.sha1 == jobtype_name)).first()
        else:
            jobtype = JobType.query.filter_by(id=jobtype_name).first()

        if not jobtype:
            return (jsonify(error="JobType %s not found" % jobtype_name),
                    NOT_FOUND)

        return Response(jobtype.code, OK, mimetype="text/x-python")

    def put(self, jobtype_name):
        """
        A ``PUT`` to this endpoint will overwrite the code of the given jobtype
        with the given data.  The sha1 column will be recomputed.

        .. http:put:: /api/v1/jobtypes/<str:jobtype>/code HTTP/1.1

            **Request**

            .. sourcecode:: http

                PUT /api/v1/jobtypes/TestJobType/code HTTP/1.1
                Accept: text/x-python
                Content-Type: text/x-python

                class TestJobType(JobType):
                    def get_command(self):
                        return "/bin/true"

                    def get_arguments(self):
                        return ""

            **Response**

            .. sourcecode:: http

                HTTP/1.1 201 CREATED
                Content-Type: text/x-python

                PUT /api/v1/jobtypes/TestJobType/code HTTP/1.1
                Accept: text/x-python
                Content-Type: text/x-python

                class TestJobType(JobType):
                    def get_command(self):
                        return "/bin/true"

                    def get_arguments(self):
                        return ""

        :statuscode 201: the jobtype's code was overwritten
        """
        if isinstance(jobtype_name, STRING_TYPES):
            jobtype = JobType.query.filter(
                or_(JobType.name == jobtype_name,
                    JobType.sha1 == jobtype_name)).first()
        else:
            jobtype = JobType.query.filter_by(id=jobtype_name).first()

        if not jobtype:
            return (jsonify(error="JobType %s not found" % jobtype_name),
                    NOT_FOUND)

        jobtype.code = request.data
        db.session.add(jobtype)
        db.session.commit()

        logger.info("Updated code for jobtype %s to %s",
                    jobtype.name,
                    jobtype.code)

        return Response(jobtype.code, CREATED, mimetype="text/x-python")


class JobTypeSoftwareRequirementsIndexAPI(MethodView):
    def get(self, jobtype_name):
        if isinstance(jobtype_name, STRING_TYPES):
            jobtype = JobType.query.filter(
                or_(JobType.name == jobtype_name,
                    JobType.sha1 == jobtype_name)).first()
        else:
            jobtype = JobType.query.filter_by(id=jobtype_name).first()

        if not jobtype:
            return (jsonify(error="JobType %s not found" % jobtype_name),
                    NOT_FOUND)

        out = [x.to_dict() for x in jobtype.software_requirements]

        return jsonify(out), OK

    @validate_with_model(JobTypeSoftwareRequirement)
    def post(self, jobtype_name):
        if isinstance(jobtype_name, STRING_TYPES):
            jobtype = JobType.query.filter(
                or_(JobType.name == jobtype_name,
                    JobType.sha1 == jobtype_name)).first()
        else:
            jobtype = JobType.query.filter_by(id=jobtype_name).first()

        if not jobtype:
            return (jsonify(error="JobType %s not found" % jobtype_name),
                    NOT_FOUND)

        if g.json["jobtype_id"] != jobtype.id:
            return jsonify(error="Wrong jobtype id in data"), BAD_REQUEST

        requirement = JobTypeSoftwareRequirement(**g.json)
        db.session.add(requirement)
        db.session.commit()
        requirement_data = requirement.to_dict()
        logger.info("Created new software requirement for for jobtype %s: %r",
                    jobtype.id, requirement_data)

        return jsonify(requirement_data), CREATED
