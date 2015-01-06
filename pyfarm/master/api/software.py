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
--------

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
    """
    Raised by :func:`extract_version_dicts` when the
    function is unable to parse a version.
    """


def extract_version_dicts(json_in):
    """Extracts and returns a list of versions from ``json_in``."""
    out = []
    version_objects = json_in.pop("versions", [])
    if not isinstance(version_objects, list):
        raise VersionParseError("Column versions must be a list.")
    for software_obj in version_objects:
        if not isinstance(software_obj, dict):
            raise VersionParseError("Entries in versions must be dictionaries.")
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

                HTTP/1.1 201 CREATED
                Content-Type: application/json

                {
                    "id": 4,
                    "software": "blender",
                    "versions": []
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
                        "versions": [
                            {
                                "version": "13.0.1",
                                "id": 1,
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


class SingleSoftwareAPI(MethodView):
    def put(self, software_rq):
        """
        A ``PUT`` to this endpoint will create a new software tag under the
        given URI or update an existing software tag if one exists.
        Renaming existing software tags via this call is supported, but when
        creating new ones, the included software name must be equal to the one in
        the URI.

        You should only call this by id for overwriting an existing software tag
        or if you have a reserved software id. There is currently no way to
        reserve a tag id.

        .. http:put:: /api/v1/software/<str:softwarename> HTTP/1.1

            **Request**

            .. sourcecode:: http

                PUT /api/v1/software/blender HTTP/1.1
                Accept: application/json

                {
                    "software": "blender"
                }

            **Response**

            .. sourcecode:: http

                HTTP/1.1 201 CREATED
                Content-Type: application/json

                {
                    "id": 4,
                    "software": "blender",
                    "versions": []
                }

            **Request**

            .. sourcecode:: http

                PUT /api/v1/software/blender HTTP/1.1
                Accept: application/json

                {
                    "software": "blender",
                    "version": [
                        {
                            "version": "1.69"
                        }
                    ]
                }

            **Response**

            .. sourcecode:: http

                HTTP/1.1 201 CREATED
                Content-Type: application/json

                {
                    "id": 4,
                    "software": "blender",
                    "versions": [
                        {
                            "version": "1.69",
                            "id": 1,
                            "rank": 100
                        }
                    ]
                }

        :statuscode 200: an existing software tag was updated
        :statuscode 201: a new software tag was created
        :statuscode 400: there was something wrong with the request (such as
                            invalid columns being included)
        """
        if isinstance(software_rq, STRING_TYPES):
            if g.json["software"] != software_rq:
                return jsonify(error="""The name of the software must be equal
                               to the one in the URI."""), BAD_REQUEST
            software = Software.query.filter_by(software=software_rq).first()
        else:
            software = Software.query.filter_by(id=software_rq).first()

        new = False if software else True
        if not software:
            software = Software()
            # This is only checked when creating new software.  Otherwise,
            # renaming is allowed
            if g.json["software"] != software_rq:
                return jsonify(error="""The name of the software must be equal
                                     to the one in the URI."""), BAD_REQUEST

        # If this endpoint specified by id, make sure to create the new
        # software under this same id, too
        if isinstance(software_rq, int):
            software.id = software_rq

        software.software = g.json["software"]

        if "versions" in g.json:
            software.versions = []
            db.session.flush()
            versions = extract_version_dicts(g.json)
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

        return jsonify(software_data), CREATED if new else OK

    def get(self, software_rq):
        """
        A ``GET`` to this endpoint will return the requested software tag

        .. http:get:: /api/v1/software/<str:softwarename> HTTP/1.1

            **Request**

            .. sourcecode:: http

                GET /api/v1/software/Autodesk%20Maya HTTP/1.1
                Accept: application/json

            **Response**

            .. sourcecode:: http

                HTTP/1.1 200 OK
                Content-Type: application/json

                {
                    "software": "Autodesk Maya",
                    "id": 1,
                    "versions": [
                        {
                            "version": "2013",
                            "id": 1,
                            "rank": 100
                        },
                        {
                            "version": "2014",
                            "id": 2,
                            "rank": 200
                        }
                    ]
                }

        :statuscode 200: no error
        :statuscode 404: the requested software tag was not found
        """
        if isinstance(software_rq, STRING_TYPES):
            software = Software.query.filter_by(software=software_rq).first()
        else:
            software = Software.query.filter_by(id=software_rq).first()

        if not software:
            return jsonify(error="Requested software not found"), NOT_FOUND

        return jsonify(software.to_dict()), OK

    def delete(self, software_rq):
        """
        A ``DELETE`` to this endpoint will delete the requested software tag

        .. http:delete:: /api/v1/software/<str:softwarename> HTTP/1.1

            **Request**

            .. sourcecode:: http

                DELETE /api/v1/software/Autodesk%20Maya HTTP/1.1
                Accept: application/json

            **Response**

            .. sourcecode:: http

                HTTP/1.1 204 NO_CONTENT

        :statuscode 204: the software tag was deleted or didn't exist
        """
        if isinstance(software_rq, STRING_TYPES):
            software = Software.query.filter_by(software=software_rq).first()
        else:
            software = Software.query.filter_by(id=software_rq).first()

        if not software:
            return jsonify(None), NO_CONTENT

        db.session.delete(software)
        db.session.commit()
        logger.info("Deleted software %s", software.software)

        return jsonify(None), NO_CONTENT


class SoftwareVersionsIndexAPI(MethodView):
    def get(self, software_rq):
        """
        A ``GET`` to this endpoint will list all known versions for this software

        .. http:get:: /api/v1/software/<str:softwarename>/versions/ HTTP/1.1

            **Request**

            .. sourcecode:: http

                GET /api/v1/software/Autodesk%20Maya/versions/ HTTP/1.1
                Accept: application/json

            **Response**

            .. sourcecode:: http

                HTTP/1.1 200 OK
                Content-Type: application/json

                [
                    {
                        "version": "2013",
                        "id": 1,
                        "rank": 100
                    },
                    {
                        "version": "2014",
                        "id": 2,
                        "rank": 200
                    }
                ]

        :statuscode 200: no error
        :statuscode 404: the requested software tag was not found
        """
        if isinstance(software_rq, STRING_TYPES):
            software = Software.query.filter_by(software=software_rq).first()
        else:
            software = Software.query.filter_by(id=software_rq).first()

        if not software:
            return jsonify(error="Requested software not found"), NOT_FOUND

        out = [{"version": x.version, "id": x.id, "rank": x.rank}
               for x in software.versions]
        return jsonify(out), OK

    @validate_with_model(SoftwareVersion, ignore=("software_id", "rank"),
                         disallow=("id", ))
    def post(self, software_rq):
        """
        A ``POST`` to this endpoint will create a new version for this software.

        A rank can optionally be included.  If it isn't, it is assumed that this
        is the newest version for this software

        .. http:post:: /api/v1/software/versions/ HTTP/1.1

            **Request**

            .. sourcecode:: http

                POST /api/v1/software/blender/versions/ HTTP/1.1
                Accept: application/json

                {
                    "version": "1.70"
                }

            **Response**

            .. sourcecode:: http

                HTTP/1.1 200 OK
                Content-Type: application/json

                {
                    "id": 4,
                    "version": "1.70",
                    "rank": "100"
                }

        :statuscode 201: a new software version was created
        :statuscode 400: there was something wrong with the request (such as
                            invalid columns being included)
        :statuscode 409: a software version with that name already exists
        """
        if isinstance(software_rq, STRING_TYPES):
            software = Software.query.filter_by(software=software_rq).first()
        else:
            software = Software.query.filter_by(id=software_rq).first()

        if not software:
            return jsonify(error="Requested software not found"), NOT_FOUND

        existing_version = SoftwareVersion.query.filter(
            SoftwareVersion.software == software,
            SoftwareVersion.version == g.json["version"]).first()
        if existing_version:
            return (jsonify(error="Version %s already exixts" %
                            g.json["version"]), CONFLICT)

        with db.session.no_autoflush:
            version = SoftwareVersion(**g.json)
            version.software = software

            if version.rank is None:
                max_rank, = db.session.query(
                    func.max(SoftwareVersion.rank)).filter_by(
                        software=software).one()
                version.rank = max_rank + 100 if max_rank is not None else 100
                if version.rank % 100 != 0:
                    version.rank += 100 - (version.rank % 100)

            db.session.add(version)
            try:
                db.session.commit()
            except DatabaseError as e:
                logger.error("DatabaseError error on SoftwareVersion POST: %r",
                            e.args)
                return jsonify(error="Database error"), INTERNAL_SERVER_ERROR

            version_data = {
                "id": version.id,
                "version": version.version,
                "rank": version.rank
                }
            logger.info("created software version %s for software %s: %r",
                        version.id, software.software, version_data)

            return jsonify(version_data), CREATED

class SingleSoftwareVersionAPI(MethodView):
    def delete(self, software_rq, version_name):
        """
        A ``DELETE`` to this endpoint will delete the requested software version

        .. http:delete:: /api/v1/software/<str:softwarename>/versions/<str:version> HTTP/1.1

            **Request**

            .. sourcecode:: http

                DELETE /api/v1/software/Autodesk%20Maya/versions/2013 HTTP/1.1
                Accept: application/json

            **Response**

            .. sourcecode:: http

                HTTP/1.1 204 NO_CONTENT

        :statuscode 204: the software version was deleted or didn't exist
        :statuscode 404: the software specified does not exist
        """
        if isinstance(software_rq, STRING_TYPES):
            software = Software.query.filter_by(software=software_rq).first()
        else:
            software = Software.query.filter_by(id=software_rq).first()

        if not software:
            return jsonify(error="Requested software not found"), NOT_FOUND

        if isinstance(version_name, STRING_TYPES):
            version = SoftwareVersion.query.filter(
                SoftwareVersion.software==software,
                SoftwareVersion.version==version_name).first()
        else:
            version = SoftwareVersion.query.filter_by(id=version_name).first()

        if not version:
            return jsonify(None), NO_CONTENT

        db.session.delete(version)
        db.session.commit()

        logger.info("deleted software version %s for software %s",
                    version.id, software.software)

        return jsonify(None), NO_CONTENT

    def get(self, software_rq, version_name):
        """
        A ``GET`` to this endpoint will return the specified version

        .. http:get:: /api/v1/software/<str:softwarename>/versions/<str:version> HTTP/1.1

            **Request**

            .. sourcecode:: http

                GET /api/v1/software/Autodesk%20Maya/versions/2014 HTTP/1.1
                Accept: application/json

            **Response**

            .. sourcecode:: http

                HTTP/1.1 200 OK
                Content-Type: application/json

                {
                    "version": "2013",
                    "id": 1,
                    "rank": 100
                }

        :statuscode 200: no error
        :statuscode 404: the requested software tag or version was not found
        """
        if isinstance(software_rq, STRING_TYPES):
            software = Software.query.filter_by(software=software_rq).first()
        else:
            software = Software.query.filter_by(id=software_rq).first()

        if not software:
            return jsonify(error="Requested software not found"), NOT_FOUND

        if isinstance(version_name, STRING_TYPES):
            version = SoftwareVersion.query.filter(
                SoftwareVersion.software==software,
                SoftwareVersion.version==version_name).first()
        else:
            version = SoftwareVersion.query.filter_by(id=version_name).first()

        if not version:
            return jsonify(error="Requested version not found"), NOT_FOUND

        out = {
            "id": version.id,
            "version": version.version,
            "rank": version.rank}
        return jsonify(out), OK
