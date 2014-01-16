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

from pyfarm.models.software import Software
from pyfarm.master.utility import json_from_request, get_column_sets, jsonify

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
