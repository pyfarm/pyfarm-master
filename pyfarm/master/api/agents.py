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

Contained within this module are an API handling functions which can
manage or query agents using JSON.
"""

try:
    from httplib import NOT_FOUND, NO_CONTENT, OK, CREATED, BAD_REQUEST
except ImportError:  # pragma: no cover
    from http.client import NOT_FOUND, NO_CONTENT, OK, CREATED, BAD_REQUEST

from flask import request, g
from flask.views import MethodView

from pyfarm.core.logger import getLogger
from pyfarm.models.agent import Agent
from pyfarm.master.application import db
from pyfarm.master.utility import (
    jsonify, validate_with_model, get_ipaddr_argument, get_integer_argument,
    get_hostname_argument, get_port_argument)

logger = getLogger("api.agents")


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
                "ram": "INTEGER",
                "free_ram": "INTEGER",
                "time_offset": "INTEGER",
                "use_address": "INTEGER",
                "ip": "IPv4Address",
                "hostname": "VARCHAR(255)",
                "cpus": "INTEGER",
                "port": "INTEGER",
                "state": "INTEGER",
                "ram_allocation": "FLOAT",
                "cpu_allocation": "FLOAT",
                "id": "INTEGER",
                "remote_ip": "IPv4Address"
            }

    :statuscode 200: no error
    """
    return jsonify(Agent.to_schema())


class AgentIndexAPI(MethodView):
    @validate_with_model(Agent, disallow=("id", ))
    def post(self):
        """
        A ``POST`` to this endpoint will always create a new agent. If you're
        looking to update an existing agent you should use url parameters and
        ``GET`` on ``/api/v1/agents/`` to find the agent you're looking for
         before performing an update or replacement of an agent's data.

        .. http:post:: /api/v1/agents/ HTTP/1.1

            **Request**

            .. sourcecode:: http

                POST /api/v1/agents/ HTTP/1.1
                Accept: application/json

                {
                    "cpu_allocation": 1.0,
                    "cpus": 14,
                    "free_ram": 133,
                    "hostname": "agent1",
                    "ip": "10.196.200.115",
                    "port": 64994,
                    "ram": 2157,
                    "ram_allocation": 0.8,
                    "state": 8
                 }

            **Response**

            .. sourcecode:: http

                HTTP/1.1 201 CREATED
                Content-Type: application/json

                {
                    "cpu_allocation": 1.0,
                    "cpus": 14,
                    "use_address": "remote",
                    "free_ram": 133,
                    "time_offset": 0,
                    "hostname": "agent1",
                    "id": 1,
                    "ip": "10.196.200.115",
                    "port": 64994,
                    "ram": 2157,
                    "ram_allocation": 0.8,
                    "state": "online",
                    "remote_ip": "10.196.200.115"
                 }

        :statuscode 201: a new agent was created
        :statuscode 400: there was something wrong with the request (such as
                         invalid columns being included)
        """
        g.json["remote_ip"] = request.remote_addr
        new_agent = Agent(**g.json)
        db.session.add(new_agent)
        db.session.commit()
        agent_data = new_agent.to_dict()
        logger.info("Created agent %r: %r", new_agent.id, agent_data)
        return jsonify(agent_data), CREATED

    def get(self):
        """
        A ``GET`` to this endpoint will return a list of known agents, with id
        and name.

        .. http:get:: /api/v1/agents/ HTTP/1.1

            **Request**

            .. sourcecode:: http

                GET /api/v1/agents/ HTTP/1.1
                Accept: application/json

            **Response**

            .. sourcecode:: http

                HTTP/1.1 200 OK
                Content-Type: application/json

                [
                    {
                        "hostname": "agent1",
                        "id": 1
                    },
                    {
                        "hostname": "agent2",
                        "id": 2
                    },
                    {
                        "hostname": "agent3.local",
                        "id": 3
                    }
                ]

            **Request (with filters)**

            .. sourcecode:: http

                GET /api/v1/agents/?min_ram=4096&min_cpus=4 HTTP/1.1
                Accept: application/json

            **Response**

            .. sourcecode:: http

                HTTP/1.1 200 OK
                Content-Type: application/json
                [
                  {
                    "hostname": "foobar",
                    "port": 50000,
                    "ip": "127.0.0.1",
                    "id": 1
                  }
                ]

        :qparam min_ram:
            If set, list only agents with ``min_ram` ram or more

        :qparam max_ram:
            If set, list only agents with ``max_ram`` ram or less

        :qparam min_cpus:
            If set, list only agents with ``min_cpus`` cpus or more

        :qparam max_cpus:
            If set, list only agents with ``max_cpus` cpus or less

        :qparam hostname:
            If set, list only agents matching ``hostname``

        :qparam ip:
            If set, list only agents matching ``ip``

        :qparam port:
            If set, list only agents matching ``port``.

        :statuscode 200: no error, hosts were found for the provided query
        :statuscode 404: error, no hosts were found for the provided query
        """
        query = db.session.query(
            Agent.id, Agent.hostname, Agent.port, Agent.ip)

        # parse url arguments
        min_ram = get_integer_argument("min_ram")
        max_ram = get_integer_argument("max_ram")
        min_cpus = get_integer_argument("min_cpus")
        max_cpus = get_integer_argument("max_cpus")
        hostname = get_hostname_argument("hostname")
        ip = get_ipaddr_argument("ip")
        port = get_port_argument("port")

        # construct query
        if min_ram is not None:
            query = query.filter(Agent.ram >= min_ram)

        if max_ram is not None:
            query = query.filter(Agent.ram <= max_ram)

        if min_cpus is not None:
            query = query.filter(Agent.cpus >= min_cpus)

        if max_cpus is not None:
            query = query.filter(Agent.cpus <= max_cpus)

        if hostname is not None:
            query = query.filter(Agent.hostname == hostname)

        if ip is not None:
            query = query.filter(Agent.ip == ip)

        if port is not None:
            query = query.filter(Agent.port == port)

        # run query and convert the results
        output = []
        for host in query:
            host = dict(zip(host.keys(), host))

            # convert the IPAddress object, if set
            if host["ip"] is not None:
                host["ip"] = str(host["ip"])

            output.append(host)

        if not output:
            return jsonify(None), NOT_FOUND
        else:
            return jsonify(output), OK


class SingleAgentAPI(MethodView):
    """
    API view which is used for retrieving information about and updating
    single agents.
    """
    def get(self, agent_id=None):
        """
        Return basic information about a single agent

        .. http:get:: /api/v1/agents/(int:agent_id) HTTP/1.1

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
                    "use_address": 311,
                    "free_ram": 133,
                    "time_offset": 0,
                    "hostname": "agent1",
                    "id": 1,
                    "ip": "10.196.200.115",
                    "port": 64994,
                    "ram": 2157,
                    "ram_allocation": 0.8,
                    "state": 202,
                    "remote_ip": "10.196.200.115"
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
        if not isinstance(agent_id, int):
            return jsonify(
                error="Expected `agent_id` to be an integer"), BAD_REQUEST

        agent = Agent.query.filter_by(id=agent_id).first()
        if agent is not None:
            return jsonify(agent.to_dict())
        else:
            return jsonify(error="Agent %s not found" % agent_id), NOT_FOUND

    @validate_with_model(Agent, disallow=("id", ))
    def post(self, agent_id=None):
        """
        Update an agent's columns with new information by merging the provided
        data with the agent's current definition in the database.

        .. http:post:: /api/v1/agents/(int:agent_id) HTTP/1.1

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
                    "use_address": 311,
                    "free_ram": 133,
                    "time_offset": 0,
                    "hostname": "agent1",
                    "id": 1,
                    "ip": "10.196.200.115",
                    "port": 64994,
                    "ram": 1234,
                    "ram_allocation": 0.8,
                    "state": "running",
                    "remote_ip": "10.196.200.115"
                }

        :statuscode 200: no error
        :statuscode 400: something within the request is invalid
        :statuscode 404: no agent could be found using the given id
        """
        if not isinstance(agent_id, int):
            return jsonify(
                error="Expected an integer for `agent_id`"), BAD_REQUEST

        # get model
        model = Agent.query.filter_by(id=agent_id).first()
        if model is None:
            return jsonify(error="Agent %s not found %s" % agent_id), NOT_FOUND

        try:
            items = g.json.iteritems
        except AttributeError:
            items = g.json.items

        # update model
        modified = {}
        for key, value in items():
            if value != getattr(model, key):
                setattr(model, key, value)
                modified[key] = value

        if modified:
            logger.debug(
                "Updated agent %s: %r", model.id, modified)
            db.session.add(model)
            db.session.commit()

        return jsonify(model.to_dict()), OK

    def delete(self, agent_id=None):
        """
        Delete a single agent

        .. http:delete:: /api/v1/agents/(int:agent_id) HTTP/1.1

            **Request (agent exists)**

            .. sourcecode:: http

                DELETE /api/v1/agents/1 HTTP/1.1
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
        if not isinstance(agent_id, int):
            return jsonify(
                error="Expected an integer for `agent_id"), BAD_REQUEST

        agent = Agent.query.filter_by(id=agent_id).first()
        if agent is None:
            return jsonify(), NO_CONTENT
        else:
            db.session.delete(agent)
            db.session.commit()
            return jsonify(), OK
