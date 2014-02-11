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
except ImportError:  # pragma: no cover
    from http.client import NOT_FOUND, NO_CONTENT, OK, CREATED, BAD_REQUEST

from flask import g
from flask.views import MethodView

from pyfarm.core.logger import getLogger
from pyfarm.core.enums import STRING_TYPES
from pyfarm.models.software import Software, SoftwareVersion
from pyfarm.master.application import db
from pyfarm.master.utility import jsonify, validate_with_model

logger = getLogger("api.software")


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
        A ``POST`` to this endpoint will do one of two things:

            * create a new software item and return the row
            * return the row for an existing item

        Software items only have two columns, software and version. Two software
        items are equal if both these columns are equal.

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

            **Request**

            .. sourcecode:: http

                POST /api/v1/software/ HTTP/1.1
                Accept: application/json

                {
                    "id": 4,
                    "software": "blender"
                    "software_versions": [
                        {
                            "version": "1.69"
                        }
                    ]
                }

            **Response (existing software item returned)**

            .. sourcecode:: http

                HTTP/1.1 200 OK
                Content-Type: application/json

                {
                    "id": 4,
                    "software": "blender",
                    "software_versions": [
                        {
                            "version": "1.69",
                            "id": 1
                            "rank": 100
                        }
                    ]
                }

        :statuscode 200: an existing software item was found and returned
        :statuscode 201: a new software item was created
        :statuscode 400: there was something wrong with the request (such as
                            invalid columns being included)
        """
        from sqlalchemy import func

        # Collect versions to add to the software object
        # Note: This can probably be done a lot simpler with generic parsing
        # of relations
        versions = []
        version_objects = g.json.pop("software_versions", [])
        del g.json["software_versions"]
        if not isinstance(version_objects, list):
            return jsonify(error="software_versions must be a list"), BAD_REQUEST
        for software_obj in version_objects:
            if not isinstance(software_obj, dict):
                return (jsonify(error="""Entries in software_versions
                                must be dictionaries."""),
                        BAD_REQUEST)
            if not isinstance(software_obj["version"], STRING_TYPES):
                return (jsonify(error="Software versions must be strings."),
                        BAD_REQUEST)
            version = {"version": software_obj["version"]}
            if "rank" in software_obj:
                if not isinstance(software_obj["rank"], int):
                    return (jsonify(error="Software rank must be an int."),
                            BAD_REQUEST)
                version["rank"] = software_obj["rank"]
            if ((len(software_obj) > 2 and "rank" in software_obj) or
                (len(software_obj) > 1 and "rank" not in software_obj)):
                    return (jsonify(error="unknown columns in software version"),
                            BAD_REQUEST)
            versions.append(version)

        software = Software.query.filter_by(software=g.json["software"]).first()

        new = False
        if not software:
            # This software tag does not exist yet, create new one
            new = True
            software = Software(**g.json)
            current_rank = 100
            for version_dict in versions:
                version = SoftwareVersion(**version_dict)
                version.software = software
                if "rank" not in version_dict:
                    version.rank = current_rank
                current_rank = max(version.rank, current_rank) + 100
        else:
            max_rank, = db.session.query(func.max(SoftwareVersion.rank))\
                                 .filter_by(software=software).one()
            if not max_rank:
                max_rank = 0
            # We assume that new software versions with no given rank are the
            # newest versions available
            current_rank = max_rank + 100
            for version_dict in versions:
                version = (SoftwareVersion.query.filter_by(software=software)
                           .filter_by(version=version_dict["version"])).first()
                if not version:
                    version = SoftwareVersion(**version_dict)
                    version.software = software
                if version.rank is None and "rank" not in version_dict:
                    version.rank = current_rank
                    current_rank += 100
                else: # Update the rank
                    version.rank = version_dict["rank"]

        db.session.add(software)
        db.session.commit()
        software_data = software.to_dict()
        logger.info("created software %s: %s" % (software.id, software_data))

        return jsonify(software_data), CREATED if new else OK

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
        all_software = Software.query.all()

        out = []
        for software in all_software:
            out.append(software.to_dict())

        return jsonify(out), OK
