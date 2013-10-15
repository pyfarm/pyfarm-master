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
Agents
------

Contained within this module are API handling functions which can
    * create new agents
    * update existing agent data
    * delete existing agents
"""

from functools import partial
from httplib import NOT_FOUND, NO_CONTENT, OK
from flask import request
from flask.views import MethodView
from pyfarm.core.enums import APIError
from pyfarm.models.agent import AgentModel
from pyfarm.master.application import db
from pyfarm.master.utility import JSONResponse, column_cache, json_from_request


to_json = partial(json_from_request,
                  all_keys=column_cache.all_columns(AgentModel),
                  disallowed_keys=set(["id"]))


# TODO: add endpoint for /agents/new
def create_agent():
    pass


# TODO: add endpoint for /agents<query parameters> [state|ram|cpus|etc]
# TODO: check docs, there's probably a standard way for providing typed args
def query_agents():
    pass


class AgentTasksAPI(MethodView):
    """
    API view which is used for modifying, adding, or removing tasks
    for a specific agent

    .. note::
        This view is mainly for querying tasks, modification of tasking
        is usually done via the queue endpoints.
    """
    pass


class AgentAPI(MethodView):
    """
    API view which is used for retrieving information about and updating
    single agents.
    """
    def get(self, agent_id=None):
        """
        Return basic information about a single agent

        .. http:get:: /api/v1/(int:agent_id) HTTP/1.1

            **Request (agent exists)**

            .. sourcecode:: http

                GET /api/v1/agents/1 HTTP/1.1
                Accept: application/json

            **Response**

            .. sourcecode:: http

                HTTP/1.1 200 OK
                Content-Type: application/json

                {
                    "cpu_allocation": 1.0,
                    "cpus": 14,
                    "freeram": 133,
                    "hostname": "agent1",
                    "id": 1,
                    "ip": "10.196.200.115",
                    "port": 64994,
                    "ram": 2157,
                    "ram_allocation": 0.8,
                    "state": 8
                 }

            **Request (no such agent)**

            .. sourcecode:: http

                GET /api/v1/agents/1234 HTTP/1.1
                Accept: application/json

            **Response**

            .. sourcecode:: http

                HTTP/1.1 404 NOT FOUND
                Content-Type: application/json

                [4, "no agent found for `1234`"]

        :statuscode 200: no error
        :statuscode 404: no agent could be found using the given id
        """
        agent = AgentModel.query.filter_by(id=agent_id).first()
        if agent is not None:
            return JSONResponse(agent.to_dict())
        else:
            errorno, msg = APIError.DATABASE_ERROR
            msg = "no agent found for `%s`" % agent_id
            return JSONResponse((errorno, msg), status=NOT_FOUND)

    # TODO: docs need a few more examples here
    def post(self, agent_id=None):
        """
        Update an agent's columns with new information

        .. http:post:: /api/v1/(int:agent_id) HTTP/1.1

            **Request**

            .. sourcecode:: http

                POST /api/v1/agents/1 HTTP/1.1
                Accept: application/json

                {"ram": 1234}


            **Response**

            .. sourcecode:: http

                HTTP/1.1 200 OK
                Content-Type: application/json

                {
                    "cpu_allocation": 1.0,
                    "cpus": 14,
                    "freeram": 133,
                    "hostname": "agent1",
                    "id": 1,
                    "ip": "10.196.200.115",
                    "port": 64994,
                    "ram": 1234,
                    "ram_allocation": 0.8,
                    "state": 8
                }

        :statuscode 200: no error
        :statuscode 400: something within the request is invalid
        :statuscode 404: no agent could be found using the given id
        """
        # get json data
        data = to_json(request)
        if isinstance(data, JSONResponse):
            return data

        # get model
        model = AgentModel.query.filter_by(id=agent_id).first()
        if model is None:
            errorno, msg = APIError.DATABASE_ERROR
            msg = "no agent found for `%s`" % agent_id
            return JSONResponse((errorno, msg), status=NOT_FOUND)

        # update model
        modified = False
        for key, value in data.iteritems():
            if value != getattr(model, key):
                setattr(model, key, value)
                modified = True

        if modified:
            db.session.add(model)
            db.session.commit()

        return JSONResponse(model.to_dict(), status=OK)

    def delete(self, agent_id=None):
        """
        Delete a single agent

        .. http:delete:: /api/v1/agents/(int:agent_id) HTTP/1.1

            **Request (agent exists)**

            .. sourcecode:: http

                DELETE /api/v1/1 HTTP/1.1
                Accept: application/json

            **Response**

            .. sourcecode:: http

                HTTP/1.1 200 OK
                Content-Type: application/json


            **Request (agent does not exist)**

            .. sourcecode:: http

                DELETE /api/v1/agents/1 HTTP/1.1
                Accept: application/json

            **Response**

            .. sourcecode:: http

                HTTP/1.1 204 NO CONTENT
                Content-Type: application/json

        :statuscode 200: the agent existed and was deleted
        :statuscode 204: the agent did not exist, nothing to delete
        """
        agent = AgentModel.query.filter_by(id=agent_id).first()
        if agent is None:
            return JSONResponse(status=NO_CONTENT)
        else:
            db.session.delete(agent)
            db.session.commit()
            return JSONResponse(status=OK)