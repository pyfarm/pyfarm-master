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
Path Maps
------

API endpoints for viewing and managing path maps
"""

try:
    from httplib import OK, CREATED, BAD_REQUEST
except ImportError:  # pragma: no cover
    from http.client import OK, CREATED, BAD_REQUEST


from flask import g
from flask.views import MethodView

from sqlalchemy import or_

from pyfarm.core.logger import getLogger
from pyfarm.core.enums import STRING_TYPES
from pyfarm.models.core.cfg import MAX_TAG_LENGTH
from pyfarm.models.pathmap import PathMap
from pyfarm.models.tag import Tag
from pyfarm.models.agent import Agent
from pyfarm.master.application import db
from pyfarm.master.utility import (
    jsonify, validate_with_model, get_integer_argument)


logger = getLogger("api.pathmaps")

def schema():
    """
    Returns the basic schema of :class:`.Agent`

    .. http:get:: /api/v1/agents/schema HTTP/1.1

        **Request**

        .. sourcecode:: http

            GET /api/v1/agents/schema HTTP/1.1
            Accept: application/json

        **Response**

        .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                "id": "INTEGER",
                "path_linux": "VARCHAR(512)",
                "path_windows": "VARCHAR(512)",
                "path_osx": "VARCHAR(512)",
                "tag": "VARCHAR(64)"
            }

    :statuscode 200: no error
    """
    out = PathMap.to_schema()
    del out["tag_id"]
    out["tag"] = "VARCHAR(%s)" % MAX_TAG_LENGTH
    return jsonify(out)

class PathMapIndexAPI(MethodView):
    @validate_with_model(PathMap, disallow=("id", ), ignore=("tag_id", "tag"))
    def post(self):
        """
        A ``POST`` to this endpoint will create a new path map.

        A path map will list the equivalent path prefixes for all three supported
        families of operating systems, Linux, Windows and OS X.
        A path map can optionally be restricted to one tag, in which case it will
        only apply to agents with that tag.
        If a tag is specified that does not exist yet, that tag will be
        transparently created.

        .. http:post:: /api/v1/pathmaps/ HTTP/1.1

            **Request**

            .. sourcecode:: http

                POST /api/v1/pathmaps/ HTTP/1.1
                Accept: application/json

                {
                    "path_linux": "/mnt/nfs",
                    "path_windows": "\\domain\cifs_server",
                    "path_osx": "/mnt/nfs",
                    "tag": "production"
                }

            **Response**

            .. sourcecode:: http

                HTTP/1.1 201 CREATED
                Content-Type: application/json

                {
                    "id": 1,
                    "path_linux": "/mnt/nfs",
                    "path_windows": "\\domain\cifs_server",
                    "path_osx": "/mnt/nfs",
                    "tag": "production"
                }

        :statuscode 201: a new pathmap was created
        :statuscode 400: there was something wrong with the request (such as
                            invalid columns being included)
        """
        tagname = g.json.pop("tag", None)
        if tagname:
            if not isinstance(tagname, STRING_TYPES):
                return jsonify(error="tag must be of type string"), BAD_REQUEST

        pathmap = PathMap(**g.json)

        if tagname:
            tag = Tag.query.filter_by(tag=tagname).first()
            if not tag:
                tag = Tag(tag=tagname)
                db.session.add(tag)
            pathmap.tag = tag

        db.session.add(pathmap)
        db.session.commit()

        out = pathmap.to_dict(unpack_relationships=False)
        if pathmap.tag:
            out["tag"] = pathmap.tag.tag

        return jsonify(out), CREATED

    def get(self):
        """
        A ``GET`` to this endpoint will return a list of all registered path
        maps, with id.
        It can be made with a for_agent query parameter, in which case it will
        return only those path maps that apply to that agent.

        .. http:get:: /api/v1/pathmaps/ HTTP/1.1

            **Request**

            .. sourcecode:: http

                GET /api/v1/pathmaps/ HTTP/1.1
                Accept: application/json

            **Response**

            .. sourcecode:: http

                HTTP/1.1 200 OK
                Content-Type: application/json

                [
                    {
                        "id": 1,
                        "path_osx": "/mnt/nfs",
                        "path_windows": "\\\\domains\\cifs_server",
                        "path_linux": "/mnt/nfs"
                    }, 
                    {
                        "id": 7,
                        "path_osx": "/renderout",
                        "path_windows": "c:\\renderout",
                        "path_linux": "/renderout"
                        "tag": "usual",
                    }
                ]

        :statuscode 200: no error
        """
        query = PathMap.query

        for_agent = get_integer_argument("for_agent")

        if for_agent:
            query =query.filter(or_(PathMap.tag == None,
                                    PathMap.tag.has(Tag.agents.any(
                                        Agent.id == for_agent))))

        logger.debug("Query: %s", str(query))

        output = []
        for map in query:
            map_dict = map.to_dict(unpack_relationships=False)
            if map.tag:
                map_dict["tag"] = map.tag.tag
            del map_dict["tag_id"]
            output.append(map_dict)

        return jsonify(output), OK
