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
from pyfarm.models.task import Task
from pyfarm.master.application import db
from pyfarm.master.utility import jsonify, validate_with_model

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
    @validate_with_model(Agent)
    def post(self):
        """
        A ``POST`` to this endpoint will do one of two things:

            * update an existing agent and return the row
            * create a new agent and return the row

        In order to update an existing agent the following columns
        must match an existing agent.  Generally speaking however, this
        functionality is included solely limit the number of duplicate
        agents:

            * hostname
            * port
            * ram
            * cpus

        If the incoming request contains data (from the list above) that
        matches an existing agent, the existing agent will be updated and
        returned.  In all other cases, a ``POST`` to this endpoint will
        result in the creation of a new agent.

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
                    "state": "running"
                 }


            **Response (existing agent updated)**

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
                    "state": "running",
                    "remote_ip": "10.196.200.115"
                 }

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

            **Response (agent created)**

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

        :statuscode 200: an existing agent was updated
        :statuscode 201: a new agent was created
        :statuscode 400: there was something wrong with the request (such as
                         invalid columns being included)
        """
        # check to see if there's already an existing agent with
        # this information
        existing_agent = Agent.query.filter_by(
            hostname=g.json["hostname"], port=g.json["port"]).first()

        # agent already exists, try to update it
        if existing_agent:
            updated = {}

            try:
                items = g.json.iteritems
            except AttributeError:
                items = g.json.items

            for key, value in items():
                if getattr(existing_agent, key) != value:
                    setattr(existing_agent, key, value)
                    updated[key] = value

            # make sure remote_ip is updated too
            updated["remote_ip"] = request.remote_addr

            # if not fields were updated, nothing to do here
            if updated:
                logger.debug(
                    "updated agent %s: %r", existing_agent.id, updated)
                db.session.add(existing_agent)
                db.session.commit()

            return jsonify(existing_agent.to_dict()), OK

        # didn't find an agent that matched the incoming data
        # so we'll create one
        else:
            g.json["remote_ip"] = request.remote_addr
            new_agent = Agent(**g.json)
            db.session.add(new_agent)
            db.session.commit()
            agent_data = new_agent.to_dict()
            logger.info("created agent %s: %s" % (new_agent.id, agent_data))
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
                        "hostname": "agent1",
                        "id": 1
                    }
                ]


        :qparam min_ram: If set, list only agents with min_ram ram or more
        :qparam max_ram: If set, list only agents with max_ram ram or less
        :qparam min_cpus: If set, list only agents with min_cpus cpus or more
        :qparam max_cpus: If set, list only agents with max_cpus cpus or less

        :statuscode 200: no error
        """
        out = []
        q = db.session.query(Agent.id, Agent.hostname)

        if request.args.get("min_ram") is not None:
            q = q.filter(Agent.ram >= request.args.get("min_ram", type=int))

        if request.args.get("max_ram") is not None:
            q = q.filter(Agent.ram <= request.args.get("max_ram", type=int))

        if request.args.get("min_cpus") is not None:
            q = q.filter(Agent.cpus >= request.args.get("min_cpus", type=int))

        if request.args.get("max_cpus") is not None:
            q = q.filter(Agent.cpus <= request.args.get("max_cpus", type=int))

        for agent_id, hostname in q:
            out.append({"id": agent_id, "hostname": hostname})

        return jsonify(out), OK


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
                error="expected `agent_id` to be an integer"), BAD_REQUEST

        agent = Agent.query.filter_by(id=agent_id).first()
        if agent is not None:
            return jsonify(agent.to_dict())
        else:
            return jsonify(error="agent %s not found" % agent_id), NOT_FOUND

    # TODO: docs need a few more examples here
    @validate_with_model(Agent, disallow=("id", ))
    def post(self, agent_id):
        """
        Update an agent's columns with new information

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
            return jsonify(error="agent %s not found %s" % agent_id), NOT_FOUND

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
                "updated agent %s: %r", model.id, modified)
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
            return jsonify(), NO_CONTENT
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
