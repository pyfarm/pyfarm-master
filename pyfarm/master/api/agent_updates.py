# No shebang line, this module is meant to be imported
#
# Copyright 2014 Ambient Entertainment Gmbh & Co. KG
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
Agent Updates
-------------

The API allows access to agent update packages, possibly through redirects
"""
import re
import tempfile
from os import makedirs
from os.path import join, isdir, isfile
from errno import EEXIST

try:
    from httplib import BAD_REQUEST, CREATED, NOT_FOUND
except ImportError:  # pragma: no cover
    from http.client import BAD_REQUEST, CREATED, NOT_FOUND

from werkzeug.utils import secure_filename
from flask.views import MethodView
from flask import request, g, redirect, send_file

from pyfarm.core.config import read_env
from pyfarm.core.logger import getLogger
from pyfarm.master.utility import jsonify

logger = getLogger("api.agents")

VERSION_REGEX = re.compile("\d+(\.\d+(\.\d+)?)?((-pre\d?)|(-dev\d?)|(-rc?\d?)|"
                           "(-alpha\d?)|(-beta\d?))?$")

UPDATES_DIR = read_env(
    "PYFARM_AGENT_UPDATES_DIR", join(tempfile.gettempdir(), "pyfarm-updates"))
UPDATES_WEBDIR = read_env("PYFARM_AGENT_UPDATES_WEBDIR", None)

try:
    makedirs(UPDATES_DIR)
except OSError as e:  # pragma: no cover
    if e.errno != EEXIST:
        raise


class AgentUpdatesAPI(MethodView):
    def put(self, version):
        """
        A ``PUT`` to this endpoint will upload a new version of pyfarm-agent to
        be used for agent auto-updates.  The update must be a zip file.

        .. http:put:: /api/v1/agents/updates/<string:version> HTTP/1.1

            **Request**

            .. sourcecode:: http

                PUT /api/v1/agents/updates/1.2.3 HTTP/1.1
                Content-Type: application/zip

                <binary data>

            **Response**

            .. sourcecode:: http

                HTTP/1.1 200 OK
                Content-Type: application/json

        :statuscode 201: The update was put in place
        :statuscode 400: there was something wrong with the request (such as an
                         invalid version number specified or the  mime type not
                         being application/zip)
        """
        if request.mimetype != "application/zip":
            return (jsonify(error="Data for agent updates must be "
                                  "application/zip"), BAD_REQUEST)
        if not VERSION_REGEX.match(version):
            return (jsonify(error="Version is not an acceptable version number"),
                    BAD_REQUEST)

        path = join(UPDATES_DIR, "pyfarm-agent-%s.zip" % version)
        with open(path, "wb+") as zip_file:
            zip_file.write(request.data)

        return "", CREATED

    def get(self, version):
        """
        A ``GET`` to this endpoint will return the update package as a zip file
        the specified version

        .. http:get:: /api/v1/agents/updates/<string:version> HTTP/1.1

            **Request**

            .. sourcecode:: http

                PUT /api/v1/agents/updates/1.2.3 HTTP/1.1
                Accept: application/zip

            **Response**

            .. sourcecode:: http

                HTTP/1.1 200 OK
                Content-Type: application/zip

                <binary data>

        :statuscode 200: The update file was found and is returned
        :statuscode 301: The update can be found under a different URL
        :statuscode 400: there was something wrong with the request (such as an
                         invalid version number specified or the  mime type not
                         being application/zip)
        """
        if not VERSION_REGEX.match(version):
            return (jsonify(error="Version is not an acceptable version number"),
                    BAD_REQUEST)
        filename = "pyfarm-agent-%s.zip" % version

        if UPDATES_WEBDIR:
            return redirect(join(UPDATES_WEBDIR, filename))

        update_file = join(UPDATES_DIR, filename)
        if not isfile(update_file):
            return (jsonify(error="Specified update not found"), NOT_FOUND)

        return send_file(update_file)
