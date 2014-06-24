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
from os import makedirs
from os.path import join, exists

try:
    from httplib import BAD_REQUEST, CREATED
except ImportError:  # pragma: no cover
    from http.client import BAD_REQUEST, CREATED

from werkzeug.utils import secure_filename
from flask.views import MethodView
from flask import request, g

from pyfarm.core.config import read_env
from pyfarm.core.logger import getLogger
from pyfarm.master.utility import jsonify

logger = getLogger("api.agents")


class AgentUpdatesAPI(MethodView):
    def put(self, version):
        if request.mimetype != "application/zip":
            return (jsonify(error="Data for agent updates must be "
                                 "application/zip"), BAD_REQUEST)
        if not re.match("\d+(\.\d+(\.\d+)?)?((-pre\d?)|(-dev\d?)|(-rc?\d?)|"
                        "(-alpha\d?)|(-beta\d?))?$", version):
            return (jsonify(error="Version is not an acceptable version number"),
                    BAD_REQUEST)

        updates_dir = read_env("PYFARM_AGENT_UPDATES_DIR", "/tmp/pyfarm-updates")
        if not exists(updates_dir):
            makedirs(updates_dir)

        path = join(updates_dir, "pyfarm-agent-%s.zip" % version)
        with open(path, "wb+") as file:
            file.write(request.data)

        return "", CREATED
