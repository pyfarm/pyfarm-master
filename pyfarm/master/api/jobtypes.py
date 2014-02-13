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
        OK, CREATED, CONFLICT)
except ImportError:  # pragma: no cover
    from http.client import (
        OK, CREATED, CONFLICT)

from flask import g
from flask.views import MethodView

from pyfarm.core.logger import getLogger
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
    @validate_with_model(JobType, ignore=("sha1",))
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
