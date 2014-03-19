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
    from httplib import (
        NOT_FOUND, NO_CONTENT, OK, CREATED, BAD_REQUEST, CONFLICT,
        INTERNAL_SERVER_ERROR)
except ImportError:  # pragma: no cover
    from http.client import (
        NOT_FOUND, NO_CONTENT, OK, CREATED, BAD_REQUEST, CONFLICT,
        INTERNAL_SERVER_ERROR)

from flask import request, g
from flask.views import MethodView
from sqlalchemy.exc import IntegrityError, ProgrammingError

from pyfarm.core.logger import getLogger
from pyfarm.models.agent import Agent
from pyfarm.models.task import Task
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

        try:
            db.session.commit()

        except Exception as e:
            db.session.rollback()
            db_error = e.args[0].lower()

            # known cases for CONFLICT
            if isinstance(e, (ProgrammingError, IntegrityError)) \
                    and "unique" in db_error or "duplicate" in db_error:
                error = "Cannot create agent because the provided data for " \
                        "`ip`, `hostname` and/or `port` was not unique enough."
                return jsonify(error=error), CONFLICT

            # Output varies by db and api so we're not going to be explicit
            # here in terms of what we're checking.  Between the exception
            # type we're catching and this check it should be rare
            # that we hit this case.
            else:  # pragma: no cover
                error = "Unhandled error: %s.  This is often an issue " \
                        "with the agent's data for `ip`, `hostname` and/or " \
                        "`port` not being unique enough.  In other cases " \
                        "this can sometimes happen if the underlying " \
                        "database driver is either non-compliant with " \
                        "expectations or we've encountered a database error " \
                        "that we don't know how to handle yet.  If the " \
                        "latter is the case, please report this as a bug." % e

                return jsonify(error=error), INTERNAL_SERVER_ERROR

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

        :statuscode 200: no error, host may or may not have been found
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

        return jsonify(output), OK


class SingleAgentAPI(MethodView):
    """
    API view which is used for retrieving information about and updating
    single agents.
    """
    def get(self, agent_id):
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

    @validate_with_model(
        Agent, disallow=("id", ),
        ignore_missing=("ram", "cpus", "port", "free_ram", "hostname"))
    def post(self, agent_id):
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
        model = Agent.query.filter_by(id=agent_id).first()
        if model is None:
            return jsonify(error="Agent %s not found %s" % agent_id), NOT_FOUND

        if "remote_ip" not in g.json:
            g.json["remote_ip"] = request.remote_addr

        try:
            items = g.json.iteritems
        except AttributeError:
            items = g.json.items

        # update the model we found
        modified = {}
        for key, value in items():
            if value != getattr(model, key):
                setattr(model, key, value)
                modified[key] = value

        if modified:
            logger.debug(
                "Updated agent %r: %r", model.id, modified)
            db.session.add(model)
            db.session.commit()

        return jsonify(model.to_dict()), OK

    def delete(self, agent_id):
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

        :statuscode 204: the agent was deleted or did not exist
        """
        agent = Agent.query.filter_by(id=agent_id).first()
        if agent is None:
            return jsonify(None), NO_CONTENT
        else:
            db.session.delete(agent)
            db.session.commit()
            return jsonify(None), NO_CONTENT


class TasksInAgentAPI(MethodView):
    def get(self, agent_id):
        """
        A ``GET`` to this endpoint will return a list of all tasks assigned to
        this agent.

        .. http:get:: /api/v1/agents/<int:agent_id>/tasks/ HTTP/1.1

            **Request**

            .. sourcecode:: http

                GET /api/v1/agents/1/tasks/ HTTP/1.1
                Accept: application/json

            **Response**

            .. sourcecode:: http

                HTTP/1.1 200 OK
                Content-Type: application/json

                [
                    {
                        "state": "assign",
                        "priority": 0,
                        "job": {
                            "jobtype": "TestJobType",
                            "id": 1,
                            "title": "Test Job",
                            "jobtype_version": 1,
                            "jobtype_id": 1
                            },
                        "hidden": false,
                        "time_started": null,
                        "project_id": null,
                        "frame": 2.0
                        "agent_id": 1,
                        "id": 2,
                        "attempts": 2,
                        "project": null,
                        "time_finished": null,
                        "time_submitted": "2014-03-06T15:40:58.338904",
                        "job_id": 1
                    }
                ]

        :statuscode 200: no error
        :statuscode 404: agent not found
        """
        agent = Agent.query.filter_by(id=agent_id).first()
        if agent is None:
            return jsonify(error="agent not found"), NOT_FOUND

        out = []
        for task in agent.tasks:
            task_dict = task.to_dict(unpack_relationships=False)
            task_dict["job"] = {
                "id": task.job.id,
                "title": task.job.title,
                "jobtype": task.job.jobtype_version.jobtype.name,
                "jobtype_id": task.job.jobtype_version.jobtype_id,
                "jobtype_version": task.job.jobtype_version.version
            }
            out.append(task_dict)
        return jsonify(out), OK

    def post(self, agent_id):
        """
        A ``POST`` to this endpoint will assign am existing task to the agent.

        .. http:post:: /api/v1/agents/<int:agent_id>/tasks/ HTTP/1.1

            **Request**

            .. sourcecode:: http

                POST /api/v1/agents/1/tasks/ HTTP/1.1
                Accept: application/json

                {
                    "id": 2
                }

            **Response**

            .. sourcecode:: http

                HTTP/1.1 200 OK
                Content-Type: application/json

                {
                    "agent_id": 1,
                    "parents": [],
                    "attempts": 2,
                    "children": [],
                    "job": {
                        "title": "Test Job",
                        "id": 1
                    },
                    "project_id": null,
                    "agent": {
                        "ip": null,
                        "hostname": "agent1",
                        "port": 50000,
                        "id": 1
                    },
                    "hidden": false,
                    "job_id": 1,
                    "time_submitted": "2014-03-06T15:40:58.338904",
                    "frame": 2.0,
                    "priority": 0,
                    "state": "assign",
                    "time_finished": null,
                    "id": 2,
                    "project": null,
                    "time_started": null
                }

        :statuscode 200: no error
        :statuscode 404: agent not found
        """
        if "id" not in g.json:
            return jsonify(error="No id given for task"), BAD_REQUEST

        if len(g.json) > 1:
            return jsonify(error="Unknown keys in request"), BAD_REQUEST

        agent = Agent.query.filter_by(id=agent_id).first()
        if agent is None:
            return jsonify(error="agent not found"), NOT_FOUND

        task = Task.query.filter_by(id=g.json["id"]).first()
        if not task:
            return jsonify(error="Task not found"), NOT_FOUND

        task.agent = agent
        db.session.add(task)
        db.session.commit()
        logger.info("Assigned task %s (frame %s, job %s) to agent %s (%s)",
                    task.id, task.frame, task.job.title,
                    agent.id, agent.hostname)

        return jsonify(task.to_dict()), OK
