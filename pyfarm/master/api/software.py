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
    from httplib import (
        NOT_FOUND, NO_CONTENT, OK, CREATED, BAD_REQUEST, INTERNAL_SERVER_ERROR,
        CONFLICT)
except ImportError:  # pragma: no cover
    from http.client import (
        NOT_FOUND, NO_CONTENT, OK, CREATED, BAD_REQUEST, INTERNAL_SERVER_ERROR,
        CONFLICT)

from flask import g
from flask.views import MethodView

from sqlalchemy import func
from sqlalchemy.exc import DatabaseError

from pyfarm.core.logger import getLogger
from pyfarm.core.enums import STRING_TYPES
from pyfarm.models.software import Software, SoftwareVersion
from pyfarm.master.application import db
from pyfarm.master.utility import jsonify, validate_with_model

logger = getLogger("api.software")

class VersionParseError(Exception):
    pass


def extract_version_dicts(json_in):
    out = []
    version_objects = json_in.pop("software_versions", [])
    if not isinstance(version_objects, list):
        raise VersionParseError("Column software_versions must be a list.")
    for software_obj in version_objects:
        if not isinstance(software_obj, dict):
            raise VersionParseError("""Entries in software_versions must be
                dictionaries.""")
        if not isinstance(software_obj["version"], STRING_TYPES):
            raise VersionParseError("Software versions must be strings.")
        version = {"version": software_obj["version"]}
        if "rank" in software_obj:
            if not isinstance(software_obj["rank"], int):
                raise VersionParseError("Software rank must be an int.")
            version["rank"] = software_obj["rank"]
        if ((len(software_obj) > 2 and "rank" in software_obj) or
            (len(software_obj) > 1 and "rank" not in software_obj)):
                raise VersionParseError("unknown columns in software version")
        out.append(version)

    return out


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
                "software": "VARCHAR(64)"
            }

    :statuscode 200: no error
    """
    return jsonify(Software.to_schema())


class SoftwareIndexAPI(MethodView):
    @validate_with_model(Software)
    def post(self):
        """
        A ``POST`` to this endpoint will create a new software tag.

        A list of versions can be included.  If the software item already exists
        the listed versions will be added to the existing ones.  Versions with no
        explicit rank are assumed to be the newest version available.  Users
        should not mix versions with an explicit rank with versions without one.

        .. http:post:: /api/v1/software/ HTTP/1.1

            **Request**

            .. sourcecode:: http

                POST /api/v1/software/ HTTP/1.1
                Accept: application/json

                {
                    "software": "blender"
                }


            **Response (new software item create)**

            .. sourcecode:: http

                HTTP/1.1 200 OK
                Content-Type: application/json

                {
                    "id": 4,
                    "software": "blender",
                    "software_versions": []
                }

        :statuscode 201: a new software item was created
        :statuscode 400: there was something wrong with the request (such as
                            invalid columns being included)
        :statuscode 409: a software tag with that name already exists
        """
        # Collect versions to add to the software object
        # Note: This can probably be done a lot simpler with generic parsing
        # of relations
        try:
            versions = extract_version_dicts(g.json)
        except VersionParseError as e:
            return jsonify(error=e.args[0]), BAD_REQUEST
        software = Software.query.filter_by(software=g.json["software"]).first()

        if software:
            return (jsonify(error="Software %s already exixts" %
                            g.json["software"]), CONFLICT)

        software = Software(**g.json)
        current_rank = 100
        for version_dict in versions:
            version_dict.setdefault("rank", current_rank)
            version = SoftwareVersion(**version_dict)
            version.software = software
            current_rank = max(version.rank, current_rank) + 100

        db.session.add(software)
        try:
            db.session.commit()
        except DatabaseError:
            return jsonify(error="Database error"), INTERNAL_SERVER_ERROR
        software_data = software.to_dict()
        logger.info("created software %s: %r", software.id, software_data)

        return jsonify(software_data), CREATED

    def get(self):
        """
        A ``GET`` to this endpoint will return a list of known software, with all
        known versions.

        .. http:get:: /api/v1/software/ HTTP/1.1

            **Request**

            .. sourcecode:: http

                GET /api/v1/software/ HTTP/1.1
                Accept: application/json

            **Response**

            .. sourcecode:: http

                HTTP/1.1 200 OK
                Content-Type: application/json

                [
                    {
                        "software": "Houdini",
                        "id": 1,
                        "software_versions": [
                            {
                                "version": "13.0.1",
                                "id": 1
                                "rank": 100
                            }
                        ]
                    }
                ]

        :statuscode 200: no error
        """
        out = []
        for software in Software.query:
            out.append(software.to_dict())

        return jsonify(out), OK
