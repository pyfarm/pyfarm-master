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

from httplib import BAD_REQUEST, OK
from functools import wraps
from flask import request, abort
from flask.views import MethodView
from pyfarm.core.logger import getLogger
from pyfarm.core.enums import APIError
from pyfarm.models.agent import AgentModel
from pyfarm.master.application import db
from pyfarm.master.utility import JSONResponse, get_required_columns

logger = getLogger("api.agents")


def try_or_fail(callable, error, description):
    try:
        return callable()
    except:
        abort(BAD_REQUEST)

from textwrap import dedent
msg = dedent("""

* merge decorator into utilities
* return all row/columns in the post body
* catch any unhandled exceptions for SQL (display in response)
* common class for convert a model to json
""")

raise Exception(msg)

# TODO: move to utilities
class requires_columns(object):
    def __init__(self, model, data_class=dict):
        self.required_columns = get_required_columns(model)
        self.data_class = data_class

    def __call__(self, func):
        @wraps(func)
        def caller(*args, **kwargs):
            # before doing anything else, make sure we can
            # decode the json data
            try:
                data = request.get_json()
            except ValueError, e:
                logger.exception(e)
                return JSONResponse(
                    APIError.JSON_DECODE_FAILED, status=BAD_REQUEST)

            # make sure the type coming in from the json data
            # is correct
            if not isinstance(data, self.data_class):
                logger.error("invalid json class")
                logger.debug("provided: %s, " % str(type(data)) +
                             "expected: %s" % self.data_class)
                return JSONResponse(
                    APIError.UNEXPECTED_DATATYPE, status=BAD_REQUEST)

            # ensure all the keys exist
            if set(data) != self.required_columns:
                logger.error("not enough columns provided")
                logger.debug("provided: %s, " % set(data) +
                             "expected: %s" % self.required_columns)
                return JSONResponse(
                    APIError.MISSING_FIELDS, status=BAD_REQUEST)

            # now check for null data
            if isinstance(data, dict):
                for key, value in data.iteritems():
                    if value is None:
                        logger.error("column %s should not be null")
                        return JSONResponse(
                            APIError.UNEXPECTED_NULL, status=BAD_REQUEST)

            return func(*args, **kwargs)

        # TODO: catch errors with the insertion
        # TODO: trap error and respond on failure
        return caller



#TODO: documentation
#TODO: on hold, POST/UPDATE for agents needs to be finished first
class AgentsIndex(MethodView):
    """
    Endpoint for /agents
    """
    def get(self):
        # TODO: add filtering
        data = dict(
            (i.hostname, (i.id, i.state, i.freeram, i.ram, i.cpus))
            for i in AgentModel.query)
        return JSONResponse(data)

    @requires_columns(AgentModel)
    def post(self):
        data = request.get_json()
        agent = AgentModel()

        for key, value in data.iteritems():
            if isinstance(value, unicode):
                value = str(value)
            if key in data:
                setattr(agent, key, data[key])

        # TODO: trap error and respond on failure
        db.session.add(agent)
        db.session.commit()

        return JSONResponse("", status=OK)
