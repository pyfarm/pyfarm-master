# No shebang line, this module is meant to be imported
#
# Copyright 2013 Oliver Palmer
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
Index
=====

Contains the endpoints for master"s index ("/")
"""

import os

from flask import Response, abort, render_template

from pyfarm.master.application import app


def favicon():
    """
    Sends out the favicon from the static directory

    .. warning::
        On deployment, /favicon.ico should really be handled by
        the frontend server and **not** the application.
    """
    path = os.path.join(app.static_folder, "favicon.ico")

    try:
        with open(path, "rb") as stream:
            # construct a response and ask the client not
            # to ask again about this file for a while
            return Response(
                response=stream.read(),
                headers={"Cache-Control": "max-age=2628000"})
    except OSError:
        abort(404)

    except IOError:
        abort(500)


def index_page():
    return render_template("pyfarm/index.html")
