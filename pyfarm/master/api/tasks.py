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
Tasks
-----

Contained within this module are an API handling functions which can
manage or query using JSON.
"""
from flask.views import MethodView

from pyfarm.models.task import Task
from pyfarm.master.utility import (
    JSONResponse, json_from_request, get_column_sets)

# TODO: connect the below in the endpoints


def schema():
    """
    Returns the basic schema of :class:`.Task`

    .. http:get:: /api/v1/tasks/schema HTTP/1.1

        **Request**

        .. sourcecode:: http

            GET /api/v1/tasks/schema HTTP/1.1
            Accept: application/json

        **Response**

        .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                "agent_id": "INTEGER",
                "attempts": "INTEGER",
                "frame": "FLOAT",
                "hidden": "BOOLEAN",
                "id": "INTEGER",
                "job_id": "INTEGER",
                "priority": "INTEGER",
                "project_id": "INTEGER",
                "state": "INTEGER",
                "time_finished": "DATETIME",
                "time_started": "DATETIME",
                "time_submitted": "DATETIME"
            }

    :statuscode 200: no error
    """
    return JSONResponse(Task().to_schema())


class TaskIndexAPI(MethodView):
    # TODO: GET with query parameters (plain index will need pagination)
    # TODO: GET docs
    # TODO: POST for new tasks only (return error for other cases)
    # TODO: POST docs
    pass


class SingleTaskAPI(MethodView):
    # TODO: GET
    # TODO: GET docs
    # TODO: POST (same format, logging, etc as agent single POST when possible)
    # TODO: POST docs
    pass
