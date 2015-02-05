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

import re
import uuid
from datetime import datetime
import json

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

from sqlalchemy import or_, not_

from pyfarm.core.logger import getLogger
from pyfarm.core.enums import WorkState, AgentState
from pyfarm.core.config import read_env
from pyfarm.scheduler.tasks import (
    assign_tasks, update_agent, assign_tasks_to_agent, send_tasks_to_agent)
from pyfarm.models.agent import Agent, AgentMacAddress
from pyfarm.models.gpu import GPU
from pyfarm.models.task import Task
from pyfarm.models.software import Software, SoftwareVersion
from pyfarm.master.application import db
from pyfarm.master.utility import (
    jsonify, validate_with_model, get_ipaddr_argument, get_integer_argument,
    get_hostname_argument, get_port_argument, isuuid)

logger = getLogger("api.agents")

DEFAULT_AGENT_SOFTWARE = json.loads(
    read_env("PYFARM_DEFAULT_AGENT_SOFTWARE", "{}"))
MAC_RE = re.compile("^([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}$")


def fail_missing_assignments(agent, current_assignments):
    known_task_ids = []
    for assignment in current_assignments.values():
        for task in assignment["tasks"]:
            known_task_ids.append(task["id"])
    tasks_query = Task.query.filter(Task.agent == agent,
                                    or_(Task.state == None,
                                        ~Task.state.in_(
                                            [WorkState.FAILED, WorkState.DONE])))
    if known_task_ids:
        tasks_query = tasks_query.filter(not_(Task.id.in_(known_task_ids)))

    failed_tasks = []
    unsent_tasks = False
    for task in tasks_query:
        if task.sent_to_agent:
            task.state = WorkState.FAILED
            db.session.add(task)
            failed_tasks.append(task)
            logger.warning("Task %s (frame %s from job %r (%s)) was not in the "
                           "current assignments of agent %r (id %s) when it "
                           "should be.  Marking it as failed.",
                           task.id, task.frame, task.job.title,
                           task.job_id, agent.hostname, agent.id)
        else:
            unsent_tasks = True

    if unsent_tasks:
        send_tasks_to_agent.delay(agent.id)

    return failed_tasks

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
                "hostname": "VARCHAR(255)",
                "cpus": "INTEGER",
                "port": "INTEGER",
                "state": "INTEGER",
                "ram_allocation": "FLOAT",
                "cpu_allocation": "FLOAT",
                "id": "UUIDType",
                "remote_ip": "IPv4Address"
            }

    :statuscode 200: no error
    """
    return jsonify(Agent.to_schema())


class AgentIndexAPI(MethodView):
    @validate_with_model(Agent, ignore=("current_assignments", "id"))
    def post(self):
        """
        A ``POST`` to this endpoint will either create or update an existing
        agent.  The ``port`` and ``id`` columns will determine if an
        agent already exists.

            * If an agent is found matching the ``port`` and ``id``
              columns from the request the existing model will be updated and
              the resulting data and the ``OK`` code will be returned.

            * If we don't find an agent matching the ``port`` and ``id``
              however a new agent will be created and the resulting data and the
              ``CREATED`` code will be returned.

        .. note::
            The ``remote_ip`` field is not required and should typically
            not be included in a request.  When not provided ``remote_ip``
            is be populated by the server based off of the ip of the
            incoming request.  Providing ``remote_ip`` in your request
            however will override this behavior.

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
                    "id": "6a0c11df-660f-4c1e-9fb4-5fe2b8cd2437",
                    "remote_ip": "10.196.200.115",
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
                    "id": "6a0c11df-660f-4c1e-9fb4-5fe2b8cd2437",
                    "port": 64994,
                    "ram": 2157,
                    "ram_allocation": 0.8,
                    "state": "online",
                    "remote_ip": "10.196.200.115"
                 }

            **Response (existing agent updated)**

            .. sourcecode:: http

                HTTP/1.1 200 OK
                Content-Type: application/json

                {
                    "cpu_allocation": 1.0,
                    "cpus": 14,
                    "use_address": "remote",
                    "free_ram": 133,
                    "time_offset": 0,
                    "hostname": "agent1",
                    "id": "6a0c11df-660f-4c1e-9fb4-5fe2b8cd2437",
                    "port": 64994,
                    "ram": 2157,
                    "ram_allocation": 0.8,
                    "state": "online",
                    "remote_ip": "10.196.200.115"
                 }
 
        :statuscode 201:
            a new agent was created

        :statuscode 200:
            an existing agent is updated with data from the request

        :statuscode 400:
            there was something wrong with the request (such as
            invalid columns being included)
        """
        # Read in and convert the id field
        try:
            g.json["id"] = uuid.UUID(g.json["id"])
        except KeyError:
            return jsonify(error="`id` not provided"), BAD_REQUEST

        # Set remote_ip if it did not come in with the request
        g.json.setdefault("remote_ip", request.remote_addr)

        current_assignments = g.json.pop("current_assignments", None)
        mac_addresses = g.json.pop("mac_addresses", None)
        # TODO return BAD_REQUEST on bad mac addresses
        if mac_addresses is not None:
            mac_addresses = [x.lower() for x in mac_addresses if MAC_RE.match(x)]

        gpus = g.json.pop("gpus", None)

        agent = Agent.query.filter_by(
            port=g.json["port"], id=g.json["id"]).first()

        if agent is None:
            try:
                agent = Agent(**g.json)

            # There may be something wrong with one of the fields
            # that's causing our sqlalchemy model raise a ValueError.
            except ValueError as e:
                return jsonify(error=str(e)), BAD_REQUEST

            for item in DEFAULT_AGENT_SOFTWARE:
                software = Software.query.filter_by(
                    software=item["software"]).first()
                if not software:
                    return (jsonify(
                        error="Default agent software %r not found" %
                            item["software"]),
                        INTERNAL_SERVER_ERROR)
                version = SoftwareVersion.query.filter_by(
                    software=software, version=item["version"]).first()
                if not version:
                    return (jsonify(
                        error="Default agent software %r version %s not found" %
                            (item["software"], item["version"])),
                        INTERNAL_SERVER_ERROR)
                agent.software_versions.append(version)

            if mac_addresses is not None:
                for address in mac_addresses:
                    mac_address = AgentMacAddress(agent=agent,
                                                  mac_address=address)
                    db.session.add(mac_address)

            if gpus is not None:
                for gpu_name in gpus:
                    gpu = GPU.query.filter_by(
                        fullname=gpu_name).first()
                    if not gpu:
                        gpu = GPU(fullname=gpu_name)
                        db.session.add(gpu)
                    agent.gpus.append(gpu)

            db.session.add(agent)

            try:
                db.session.commit()

            except Exception as e:
                e = e.args[0].lower()
                error = "Unhandled error: %s.  This is often an issue " \
                        "with the agent's data for `ip`, `hostname` and/or " \
                        "`port` not being unique enough.  In other cases " \
                        "this can sometimes happen if the underlying " \
                        "database driver is either non-compliant with " \
                        "expectations or we've encountered a database error " \
                        "that we don't know how to handle yet.  If the " \
                        "latter is the case, please report this as a bug." % e

                return jsonify(error=error), INTERNAL_SERVER_ERROR

            else:
                agent_data = agent.to_dict(unpack_relationships=False)
                logger.info("Created agent %r: %r", agent.id, agent_data)
                assign_tasks.delay()
                return jsonify(agent_data), CREATED

        else:
            updated = False

            for key in g.json.copy():
                value = g.json.pop(key)

                if not hasattr(agent, key):
                    return jsonify(
                        error="Agent has no such column `%s`" % key), \
                           BAD_REQUEST

                if getattr(agent, key) != value:
                    try:
                        setattr(agent, key, value)

                    except Exception as e:
                        return jsonify(
                            error="Error while setting `%s`: %s" % (key, e)), \
                               BAD_REQUEST
                    else:
                        updated = True

            if mac_addresses is not None:
                updated = True
                for existing_address in agent.mac_addresses:
                    if existing_address.mac_address.lower() not in mac_addresses:
                        logger.debug("Existing address %s is not in supplied "
                                     "mac addresses, for agent %s, removing it.",
                                     existing_address.mac_address,
                                     agent.hostname)
                        agent.mac_addresses.remove(existing_address)
                    else:
                        mac_addresses.remove(
                            existing_address.mac_address.lower())

                for new_address in mac_addresses:
                    mac_address = AgentMacAddress(
                        agent=agent, mac_address=new_address)
                    db.session.add(mac_address)

            if gpus is not None:
                updated = True
                for existing_gpu in agent.gpus:
                    if existing_gpu.fullname not in gpus:
                        logger.debug("Existing gpu %s is not in supplied "
                                     "gpus, for agent %s, removing it.",
                                     existing_address.mac_address,
                                     agent.hostname)
                        agent.gpus.remove(existing_gpu)
                    else:
                        gpus.remove(existing_gpu.fullname)

                for gpu_name in gpus:
                    gpu = GPU.query.filter_by(fullname=gpu_name).first()
                    if not gpu:
                        gpu = GPU(fullname=gpu_name)
                        db.session.add(gpu)
                    agent.gpus.append(gpu)

            # TODO Only do that if this is really the agent speaking to us.
            failed_tasks = []
            if (current_assignments is not None and
                agent.state != AgentState.OFFLINE):
                    fail_missing_assignments(agent, current_assignments)

            if updated or failed_tasks:
                agent.last_heard_from = datetime.utcnow()
                db.session.add(agent)

                try:
                    db.session.commit()

                except Exception as e:
                    return jsonify(error="Unhandled error: %s" % e), \
                           INTERNAL_SERVER_ERROR

                else:
                    agent_data = agent.to_dict(unpack_relationships=False)
                    logger.info("Updated agent %r: %r", agent.id, agent_data)
                    for task in failed_tasks:
                        task.job.update_state()
                    db.session.commit()
                    assign_tasks.delay()
                    return jsonify(agent_data), OK

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
                        "id": "dd0c6da2-0c91-42cf-a82f-6d503aae43d3"
                    },
                    {
                        "hostname": "agent2",
                        "id": "8326779e-90b5-447c-8da8-1eaa154771d9"
                    },
                    {
                        "hostname": "agent3.local",
                        "id": "14b28230-64a1-4b62-803e-5fd1baa209e4"
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
                    "remote_ip": "127.0.0.1",
                    "id": "e20bae92-6472-442e-98a8-0ea4c9ee41cd"
                  }
                ]

        :qparam min_ram:
            If set, list only agents with ``min_ram`` ram or more

        :qparam max_ram:
            If set, list only agents with ``max_ram`` ram or less

        :qparam min_cpus:
            If set, list only agents with ``min_cpus`` cpus or more

        :qparam max_cpus:
            If set, list only agents with ``max_cpus`` cpus or less

        :qparam hostname:
            If set, list only agents matching ``hostname``

        :qparam remote_ip:
            If set, list only agents matching ``remote_ip``

        :qparam port:
            If set, list only agents matching ``port``.

        :statuscode 200:
            no error, host may or may not have been found
        """
        query = db.session.query(
            Agent.id, Agent.hostname, Agent.port, Agent.remote_ip)

        # parse url arguments
        min_ram = get_integer_argument("min_ram")
        max_ram = get_integer_argument("max_ram")
        min_cpus = get_integer_argument("min_cpus")
        max_cpus = get_integer_argument("max_cpus")
        hostname = get_hostname_argument("hostname")
        remote_ip = get_ipaddr_argument("remote_ip")
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

        if remote_ip is not None:
            query = query.filter(Agent.remote_ip == remote_ip)

        if port is not None:
            query = query.filter(Agent.port == port)

        # run query and convert the results
        output = []
        for host in query:
            host = dict(zip(host.keys(), host))

            # convert the IPAddress object, if set
            if host["remote_ip"] is not None:
                host["remote_ip"] = str(host["remote_ip"])

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

        .. http:get:: /api/v1/agents/(str:agent_id) HTTP/1.1

            **Request (agent exists)**

            .. sourcecode:: http

                GET /api/v1/agents/4eefca76-1127-4c17-a3df-c1a7de685541 HTTP/1.1
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
                    "id": "322360ad-976f-4103-9acc-a811d43fd24d",
                    "ip": "10.196.200.115",
                    "port": 64994,
                    "ram": 2157,
                    "ram_allocation": 0.8,
                    "state": 202,
                    "remote_ip": "10.196.200.115"
                 }

            **Request (no such agent)**

            .. sourcecode:: http

                GET /api/v1/agents/4eefca76-1127-4c17-a3df-c1a7de685541 HTTP/1.1
                Accept: application/json

            **Response**

            .. sourcecode:: http

                HTTP/1.1 404 NOT FOUND
                Content-Type: application/json

                {"error": "Agent `4eefca76-1127-4c17-a3df-c1a7de685541` not "
                          "found"}

        :statuscode 200: no error
        :statuscode 400: something within the request is invalid
        :statuscode 404: no agent could be found using the given id
        """
        agent = Agent.query.filter_by(id=agent_id).first()
        if agent is not None:
            return jsonify(agent.to_dict(unpack_relationships=False))
        else:
            return jsonify(error="Agent %s not found" % agent_id), NOT_FOUND

    @validate_with_model(
        Agent,
        type_checks={"id": isuuid},
        ignore=("current_assignments", ),
        ignore_missing=(
            "ram", "cpus", "port", "free_ram", "hostname"))
    def post(self, agent_id):
        """
        Update an agent's columns with new information by merging the provided
        data with the agent's current definition in the database.

        .. http:post:: /api/v1/agents/(str:agent_id) HTTP/1.1

            **Request**

            .. sourcecode:: http

                POST /api/v1/agents/29d466a5-34f8-408a-b613-e6c2715077a0 HTTP/1.1
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
                    "id": "29d466a5-34f8-408a-b613-e6c2715077a0",
                    "ip": "10.196.200.115",
                    "port": 64994,
                    "ram": 1234,
                    "ram_allocation": 0.8,
                    "state": "running",
                    "remote_ip": "10.196.200.115"
                }

        :statuscode 200:
            no error

        :statuscode 400:
            something within the request is invalid

        :statuscode 404:
            no agent could be found using the given id
        """
        agent = Agent.query.filter_by(id=agent_id).first()
        if agent is None:
            return jsonify(error="Agent %s not found" % agent_id), NOT_FOUND

        if "remote_ip" not in g.json:
            g.json["remote_ip"] = request.remote_addr

        current_assignments = g.json.pop("current_assignments", None)
        mac_addresses = g.json.pop("mac_addresses", None)

        # TODO return BAD_REQUEST on bad mac addresses
        if mac_addresses is not None:
            mac_addresses = [x.lower() for x in mac_addresses if MAC_RE.match(x)]

        gpus = g.json.pop("gpus", None)

        try:
            items = g.json.iteritems
        except AttributeError:
            items = g.json.items

        modified = {}
        for key, value in items():
            if value != getattr(agent, key):
                try:
                    setattr(agent, key, value)

                # There may be something wrong with one of the fields
                # that's causing our sqlalchemy model to raise a ValueError.
                except ValueError as e:
                    return jsonify(error=str(e)), BAD_REQUEST

                modified[key] = value

        agent.last_heard_from = datetime.utcnow()

        if "upgrade_to" in modified:
            update_agent.delay(agent.id)

        if mac_addresses is not None:
            modified["mac_addresses"] = mac_addresses
            for existing_address in agent.mac_addresses:
                if existing_address.mac_address.lower() not in mac_addresses:
                    logger.debug("Existing address %s is not in supplied "
                                 "mac addresses, for agent %s, removing it.",
                                 existing_address.mac_address,
                                 agent.hostname)
                    agent.mac_addresses.remove(existing_address)
                else:
                    mac_addresses.remove(
                        existing_address.mac_address.lower())

            for new_address in mac_addresses:
                mac_address = AgentMacAddress(
                    agent=agent, mac_address=new_address)
                db.session.add(mac_address)

        if gpus is not None:
            modified["gpus"] = gpus
            for existing_gpu in agent.gpus:
                if existing_gpu.fullname not in gpus:
                    logger.debug("Existing gpu %s is not in supplied "
                                    "gpus, for agent %s, removing it.",
                                    existing_address.mac_address,
                                    agent.hostname)
                    agent.gpus.remove(existing_gpu)
                else:
                    gpus.remove(existing_gpu.fullname)

            for gpu_name in gpus:
                gpu = GPU.query.filter_by(fullname=gpu_name).first()
                if not gpu:
                    gpu = GPU(fullname=gpu_name)
                    db.session.add(gpu)
                agent.gpus.append(gpu)

        # TODO Only do that if this is really the agent speaking to us.
        failed_tasks = []
        if (current_assignments is not None and
            agent.state != AgentState.OFFLINE):
            failed_tasks = fail_missing_assignments(agent, current_assignments)

        logger.debug(
            "Updated agent %r: %r", agent.id, modified)
        db.session.add(agent)
        db.session.commit()

        for task in failed_tasks:
            task.job.update_state()
        db.session.commit()

        assign_tasks_to_agent.delay(agent_id)

        return jsonify(agent.to_dict(unpack_relationships=False)), OK

    def delete(self, agent_id):
        """
        Delete a single agent

        .. http:delete:: /api/v1/agents/(uuid:agent_id) HTTP/1.1

            **Request (agent exists)**

            .. sourcecode:: http

                DELETE /api/v1/agents/b25ee7eb-9586-439a-b131-f5d022e0d403 HTTP/1.1
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
            assign_tasks.delay()
            return jsonify(None), NO_CONTENT


class TasksInAgentAPI(MethodView):
    def get(self, agent_id):
        """
        A ``GET`` to this endpoint will return a list of all tasks assigned to
        this agent.

        .. http:get:: /api/v1/agents/<str:agent_id>/tasks/ HTTP/1.1

            **Request**

            .. sourcecode:: http

                GET /api/v1/agents/bbf55143-f2b1-4c15-9d41-139bd8057931/tasks/ HTTP/1.1
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
                        "agent_id": "bbf55143-f2b1-4c15-9d41-139bd8057931",
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
            return jsonify(error="Agent %r not found" % agent_id), NOT_FOUND

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

        .. http:post:: /api/v1/agents/<str:agent_id>/tasks/ HTTP/1.1

            **Request**

            .. sourcecode:: http

                POST /api/v1/agents/238d7334-8ca5-4469-9f54-e76c66614a43/tasks/ HTTP/1.1
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
                        "id": "238d7334-8ca5-4469-9f54-e76c66614a43"
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

        :statuscode 200:
            no error

        :statuscode 404:
            agent not found
        """
        if "id" not in g.json:
            return jsonify(error="No id given for task"), BAD_REQUEST

        if len(g.json) > 1:
            return jsonify(error="Unknown keys in request"), BAD_REQUEST

        agent = Agent.query.filter_by(id=agent_id).first()
        if agent is None:
            return jsonify(error="Agent %r not found" % agent_id), NOT_FOUND

        task = Task.query.filter_by(id=g.json["id"]).first()
        if not task:
            return jsonify(error="Task not found"), NOT_FOUND

        task.agent = agent
        db.session.add(task)
        db.session.commit()
        logger.info("Assigned task %s (frame %s, job %s) to agent %s (%s)",
                    task.id, task.frame, task.job.title,
                    agent.id, agent.hostname)
        assign_tasks.delay()

        return jsonify(task.to_dict()), OK
