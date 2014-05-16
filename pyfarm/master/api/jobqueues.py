# No shebang line, this module is meant to be imported
#
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
Job Queues
----------

This module defines an API for managing and querying job queues
"""
try:
    from httplib import OK
except ImportError:  # pragma: no cover
    from http.client import OK

from pyfarm.models.jobqueue import JobQueue
from pyfarm.master.utility import jsonify

def schema():
    """
    Returns the basic schema of :class:`.JobQueue`

    .. http:get:: /api/v1/jobqueues/schema HTTP/1.1

        **Request**

        .. sourcecode:: http

            GET /api/v1/jobqueues/schema HTTP/1.1
            Accept: application/json

        **Response**

        .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                "id": "INTEGER",
                "name": VARCHAR(255)",
                "minimum_agents": "INTEGER",
                "maximum_agents": "INTEGER",
                "priority": "INTEGER",
                "weight": "INTEGER",
                "parent_jobqueue_id": "INTEGER"
            }

    :statuscode 200: no error
    """
    return jsonify(JobQueue.to_schema()), OK
