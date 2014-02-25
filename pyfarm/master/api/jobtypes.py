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
        OK, CREATED, CONFLICT, NOT_FOUND, BAD_REQUEST, NO_CONTENT)
except ImportError:  # pragma: no cover
    from http.client import (
        OK, CREATED, CONFLICT, NOT_FOUND, BAD_REQUEST, NO_CONTENT)

from flask import g, Response, request
from flask.views import MethodView

from sqlalchemy import or_

from pyfarm.core.logger import getLogger
from pyfarm.core.enums import STRING_TYPES, PY3
from pyfarm.models.software import JobTypeSoftwareRequirement
from pyfarm.models.jobtype import JobType, JobTypeVersion
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
                "version": "INTEGER",
                "max_batch": "INTEGER",
                "name": "VARCHAR(64)"
            }

    :statuscode 200: no error
    """
    schema_dict = {
        "batch_contiguous": "BOOLEAN",
        "classname": "VARCHAR(64)",
        "code": "TEXT",
        "description": "TEXT",
        "id": "INTEGER",
        "version": "INTEGER",
        "max_batch": "INTEGER",
        "name": "VARCHAR(64)"}
    return jsonify(schema_dict), OK


class JobTypeIndexAPI(MethodView):
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
                    "version": 1,
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
                }

        :statuscode 201: a new jobtype item was created
        :statuscode 400: there was something wrong with the request (such as
                            invalid columns being included)
        :statuscode 409: a conflicting jobtype already exists
        """
        if "name" not in g.json:
            return jsonify(error="Jobtype does not specify a name"), BAD_REQUEST
        jobtype = JobType.query.filter_by(name=g.json["name"]).first()

        if jobtype:
            return (jsonify(error="Jobtype %s already exixts" %
                            g.json["name"]), CONFLICT)

        try:
            jobtype = JobType()
            jobtype.name = g.json.pop("name")
            jobtype.description = g.json.pop("description", None)
            jobtype_version = JobTypeVersion()
            jobtype_version.jobtype = jobtype
            jobtype_version.version = 1
            jobtype_version.code = g.json.pop("code")
            jobtype_version.classname = g.json.pop("classname", None)
            jobtype_version.batch_contiguous = g.json.pop("batch_contiguous",
                                                          None)
            jobtype_version.max_batch = g.json.pop("max_batch", None)
        except KeyError as e:
            return (jsonify(error="Missing key in input: %r" % e.args),
                    BAD_REQUEST)

        if g.json:
            return (jsonify(error="Unexpected keys in input: %s" %
                            g.json.keys()), BAD_REQUEST)

        db.session.add_all([jobtype, jobtype_version])
        db.session.commit()
        jobtype_data = jobtype_version.to_dict(unpack_relationships=False)
        jobtype_data.update(jobtype.to_dict(
            unpack_relationships=["software_requirements"]))
        del jobtype_data["jobtype_id"]
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
        A ``GET`` to this endpoint will return the most recent version of the
        referenced jobtype, by name or id.

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
                    "version": 1,
                    "max_batch": 1,
                    "name": "TestJobType",
                    "software_requirements": [
                            {
                            "id": 1,
                            "max_version": null,
                            "max_version_id": null,
                            "min_version": "8.21",
                            "min_version_id": 1,
                            "software": "/bin/touch",
                            "software_id": 1
                            }
                        ]
                }

        :statuscode 200: no error
        :statuscode 404: jobtype or version not found
        """
        if isinstance(jobtype_name, STRING_TYPES):
            jobtype = JobType.query.filter(JobType.name == jobtype_name).first()
        else:
            jobtype = JobType.query.filter_by(id=jobtype_name).first()

        jobtype_version = JobTypeVersion.query.filter_by(
            jobtype=jobtype).order_by("version desc").first()

        if not jobtype or not jobtype_version:
            return (jsonify(error="JobType %s not found" % jobtype_name),
                    NOT_FOUND)

        # For some reason, sqlalchemy sometimes returns this column as bytes
        # instead of string.  jsonify cannot decode that.
        if PY3 and isinstance(jobtype_version.code, bytes):
            jobtype_version.code = jobtype_version.code.decode()

        jobtype_data = jobtype_version.to_dict(
            unpack_relationships=["software_requirements"])
        jobtype_data.update(jobtype.to_dict(unpack_relationships=False))
        del jobtype_data["jobtype_id"]
        return jsonify(jobtype_data), OK

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
                    "max_batch": 1,
                    "name": "TestJobType", 
                    "description": "Jobtype for testing inserts and queries",
                    "software_requirements": []
                }

        :statuscode 201: a new tag was created
        :statuscode 400: there was something wrong with the request (such as
                            invalid columns being included)
        """
        if isinstance(jobtype_name, STRING_TYPES):
            jobtype = JobType.query.filter(JobType.name == jobtype_name).first()
        else:
            jobtype = JobType.query.filter_by(id=jobtype_name).first()

        max_version = None
        new = False if jobtype else True
        if jobtype:
            logger.debug(
                "jobtype %s will be get a new version with %r on commit",
                jobtype.name, g.json)
            max_version, = db.session.query(
                JobTypeVersion.version).filter_by(
                    jobtype=jobtype).order_by("version desc").first()
        else:
            jobtype = JobType()

        if max_version:
            version = max_version + 1
        else:
            version = 1

        try:
            jobtype.name = g.json.pop("name")
            jobtype.description = g.json.pop("description", None)
            jobtype_version = JobTypeVersion()
            jobtype_version.jobtype = jobtype
            jobtype_version.version = version
            jobtype_version.code = g.json.pop("code")
            jobtype_version.classname = g.json.pop("classname", None)
            jobtype_version.batch_contiguous = g.json.pop("batch_contiguous",
                                                          None)
            jobtype_version.max_batch = g.json.pop("max_batch", None)
        except KeyError as e:
            return (jsonify(error="Missing key in input: %r" % e.args),
                    BAD_REQUEST)

        if g.json:
            return (jsonify(error="Unexpected keys in input: %s" %
                            g.json.keys()), BAD_REQUEST)

        db.session.add_all([jobtype, jobtype_version])
        db.session.commit()
        jobtype_data = jobtype_version.to_dict(unpack_relationships=False)
        jobtype_data.update(jobtype.to_dict(
            unpack_relationships=["software_requirements"]))
        del jobtype_data["jobtype_id"]
        logger.info("%s jobtype %s in put: %r"
            "created" if new else "updated", jobtype.name, jobtype_data)

        return jsonify(jobtype_data), CREATED

    def delete(self, jobtype_name):
        """
        A ``DELETE`` to this endpoint will delete the requested jobtype

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
            jobtype = JobType.query.filter(JobType.name == jobtype_name).first()
        else:
            jobtype = JobType.query.filter_by(id=jobtype_name).first()

        if jobtype:
            logger.debug("jobtype %s will be deleted",jobtype.name, g.json)
            db.session.delete(jobtype)
            db.session.commit()
            logger.info("jobtype %s has been deleted",jobtype.name, g.json)

        return jsonify(), NO_CONTENT


class JobTypeCodeAPI(MethodView):
    def get(self, jobtype_name, version):
        """
        A ``GET`` to this endpoint will return just the python code for this
        version of the specified jobtype.

        .. http:get:: /api/v1/jobtypes/<str:jobtype>/versions/<int:version>/code HTTP/1.1

            **Request**

            .. sourcecode:: http

                GET /api/v1/jobtypes/TestJobType/versions/1/code HTTP/1.1
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
        :statuscode 404: jobtype or version not found
        """
        if isinstance(jobtype_name, STRING_TYPES):
            jobtype = JobType.query.filter_by(name=jobtype_name).first()
        else:
            jobtype = JobType.query.filter_by(id=jobtype_name).first()

        if not jobtype:
            return (jsonify(error="JobType %s not found" % jobtype_name),
                    NOT_FOUND)

        jobtype_version = JobTypeVersion.query.filter_by(
            jobtype=jobtype, version=version).first()

        if not jobtype_version:
            return (jsonify(error="JobType version %s not found" % version),
                    NOT_FOUND)

        return Response(jobtype_version.code, OK, mimetype="text/x-python")


class JobTypeSoftwareRequirementsIndexAPI(MethodView):
    def get(self, jobtype_name):
        if isinstance(jobtype_name, STRING_TYPES):
            jobtype = JobType.query.filter_by(name=jobtype_name).first()
        else:
            jobtype = JobType.query.filter_by(id=jobtype_name).first()

        if not jobtype:
            return (jsonify(error="JobType %s not found" % jobtype_name),
                    NOT_FOUND)

        jobtype_version = JobTypeVersion.query.filter_by(
            jobtype=jobtype).order_by("version desc").first()

        if not jobtype_version:
            return jsonify(error="JobType version not found"), NOT_FOUND

        out = [x.to_dict() for x in jobtype_version.software_requirements]

        return jsonify(out), OK

    @validate_with_model(JobTypeSoftwareRequirement,
                         ignore=["jobtype_version_id"])
    def post(self, jobtype_name):
        if isinstance(jobtype_name, STRING_TYPES):
            jobtype = JobType.query.filter_by(name=jobtype_name).first()
        else:
            jobtype = JobType.query.filter_by(id=jobtype_name).first()

        if not jobtype:
            return (jsonify(error="JobType %s not found" % jobtype_name),
                    NOT_FOUND)

        jobtype_version = JobTypeVersion.query.filter_by(
            jobtype=jobtype).order_by("version desc").first()
        if not jobtype_version:
            return jsonify(error="JobType version not found"), NOT_FOUND

        requirement = JobTypeSoftwareRequirement(**g.json)
        requirement.jobtype_version = jobtype_version

        db.session.add(requirement)
        db.session.commit()
        requirement_data = requirement.to_dict()
        logger.info("Created new software requirement for for jobtype %s: %r",
                    jobtype.id, requirement_data)

        return jsonify(requirement_data), CREATED
