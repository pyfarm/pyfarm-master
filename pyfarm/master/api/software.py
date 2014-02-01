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
Software
------

Contained within this module are an API handling functions which can
manage or query software items using JSON.
"""

try:
    from httplib import NOT_FOUND, NO_CONTENT, OK, CREATED, BAD_REQUEST
except ImportError: # pragma: no cover
    from http.client import NOT_FOUND, NO_CONTENT, OK, CREATED, BAD_REQUEST

from flask import Response, request
from flask.views import MethodView

from pyfarm.core.logger import getLogger
from pyfarm.models.software import Software
from pyfarm.master.application import db
from pyfarm.master.utility import json_from_request, jsonify, get_column_sets

ALL_SOFTWARE_COLUMNS, REQUIRED_SOFTWARRE_COLUMNS = get_column_sets(Software)

logger = getLogger("api.agents")


def schema():
    """
    Returns the basic schema of :class:`.Software`

    .. http:get:: /api/v1/software/schema HTTP/1.1

        **Request**

        .. sourcecode:: http

            GET /api/v1/software/schema HTTP/1.1
            Accept: application/json

        **Response**

        .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                "id": "INTEGER",
                "software": "VARCHAR(64)",
                "version": "VARCHAR(64)"
            }

    :statuscode 200: no error
    """
    return jsonify(Software().to_schema())


class SoftwareIndexAPI(MethodView):
    def post(self):
        """
        A ``POST`` to this endpoint will do one of two things:

            * create a new software item and return the row
            * return the row for an existing item

        Software items only have two columns, software and version. Two software
        items are equal if both these columns are equal.

        .. http:post:: /api/v1/software HTTP/1.1

            **Request**

            .. sourcecode:: http

                POST /api/v1/softwarre HTTP/1.1
                Accept: application/json

                {
                    "software": "blender",
                    "version": "1.56"
                }


            **Response (new software item create)**

            .. sourcecode:: http

                HTTP/1.1 200 OK
                Content-Type: application/json

                {
                    "id": 4,
                    "software": "bliender",
                    "version": "1.56"
                    }

            **Request**

            .. sourcecode:: http

                POST /api/v1/software HTTP/1.1
                Accept: application/json

                {
                    "id": 4,
                    "software": "bliender",
                    "version": "1.56"
                }

            **Response (existing software item returned)**

            .. sourcecode:: http

                HTTP/1.1 200 OK
                Content-Type: application/json

                {
                    "id": 4,
                    "software": "bliender",
                    "version": "1.56"
                }

        :statuscode 200: an existing software item was found and returned
        :statuscode 201: a new software item was created
        :statuscode 400: there was something wrong with the request (such as
                            invalid columns being included)
        """
        logger.info("In SoftwareIndexAPI.post")
        data = json_from_request(request,
                                 all_keys=ALL_SOFTWARE_COLUMNS,
                                 required_keys=REQUIRED_SOFTWARRE_COLUMNS,
                                 disallowed_keys=set(["id"]))
        logger.info("called json_from_request")
        # json_from_request returns a Response object on error
        if isinstance(data, Response):
            logger.info("json_from_request returned an error")
            return data
        logger.info("json_from_request returned data")

        existing_software = Software.query.filter_by(
            software=data["software"], version=data["version"]).first()

        if existing_software:
            # No update needed, because Software only has those two columns
            return jsonify(existing_software.to_dict()), OK

        else:
            new_software = Software(**data)
            db.session.add(new_software)
            db.session.commit()
            software_data = new_software.to_dict()
            logger.info("created software %s: %s" %
                        (new_software.id,
                         software_data))
            return jsonify(software_data), CREATED
