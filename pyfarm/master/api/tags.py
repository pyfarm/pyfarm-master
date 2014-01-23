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
Tag
===

Contained within this module are an API handling functions which can
manage or query tags using JSON.
"""

try:
    from httplib import NOT_FOUND, NO_CONTENT, OK, CREATED, BAD_REQUEST
except ImportError:
    from http.client import NOT_FOUND, NO_CONTENT, OK, CREATED, BAD_REQUEST

from flask import Response, request, url_for
from flask.views import MethodView

from pyfarm.core.logger import getLogger
from pyfarm.core.enums import STRING_TYPES, APIError
from pyfarm.models.agent import Agent, AgentTagAssociation
from pyfarm.models.job import Job, JobTagAssociation
from pyfarm.models.tag import Tag
from pyfarm.master.application import db
from pyfarm.master.utility import json_from_request, jsonify, get_column_sets

ALL_TAG_COLUMNS, REQUIRED_TAG_COLUMNS = get_column_sets(Tag)

logger = getLogger("api.tags")


def schema():
    """
    Returns the basic schema of :class:`.Tag`

    .. http:get:: /api/v1/tags/schema HTTP/1.1

        **Request**

        .. sourcecode:: http

            GET /api/v1/tags/schema HTTP/1.1
            Accept: application/json

        **Response**

        .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                "id": "INTEGER",
                "tag": "VARCHAR(64)"
            }

    :statuscode 200: no error
    """
    return jsonify(Tag().to_schema())


class TagIndexAPI(MethodView):
    def post(self):
        """
        A ``POST`` to this endpoint will do one of two things:

            * create a new tag and return the row
            * return the row for an existing tag

       Tags only have one column, the tag name. Two tags are automatically
       considered equal if the tag names are equal.

        .. http:post:: /api/v1/tags HTTP/1.1

            **Request**

            .. sourcecode:: http

                POST /api/v1/tags HTTP/1.1
                Accept: application/json

                {
                    "tag": "interesting"
                }

            **Response (new tag create)**

            .. sourcecode:: http

                HTTP/1.1 201 CREATED
                Content-Type: application/json

                {
                    "id": 1,
                    "tag": "interesting"
                }

            **Request**

            .. sourcecode:: http

                POST /api/v1/tags HTTP/1.1
                Accept: application/json

                {
                    "tag": "interesting"
                }

            **Response (existing tag returned)**

            .. sourcecode:: http

                HTTP/1.1 200 OK
                Content-Type: application/json

                {
                    "id": 1,
                    "tag": "interesting"
                }

        :statuscode 200: an existing tag was found and returned
        :statuscode 201: a new tag was created
        :statuscode 400: there was something wrong with the request (such as
                            invalid columns being included)
        """
        data = json_from_request(request,
                                 all_keys=ALL_TAG_COLUMNS,
                                 required_keys=REQUIRED_TAG_COLUMNS,
                                 disallowed_keys=set(["id"]))
        # json_from_request returns a Response object on error
        if isinstance(data, Response):
            return data

        existing_tag = Tag.query.filter_by(tag=data["tag"]).first()

        if existing_tag:
            # No update needed, because Tag only has that one column
            return jsonify(existing_tag.to_dict()), OK

        else:
            new_tag = Tag(**data)
            db.session.add(new_tag)
            db.session.commit()
            tag_data = new_tag.to_dict()
            logger.info("created tag %s: %s" %
                        (new_tag.id,
                         tag_data))
            return jsonify(tag_data), CREATED

    def get(self):
        """
        A ``GET`` to this endpoint will return a list of known tags, with id.
        Associated agents and jobs can be included for every tag, however that
        feature may become a performance problem if used too much.
        Only use it if you need that information anyway and the alternative would
        be separate API calls for every tag returned here.

        .. http:get:: /api/v1/tags HTTP/1.1

            **Request**

            .. sourcecode:: http

                GET /api/v1/tags HTTP/1.1
                Accept: application/json

            **Response**

            .. sourcecode:: http

                HTTP/1.1 200 OK
                Content-Type: application/json

                [
                    {
                        "id": 1,
                        "tag": "interesting"
                    },
                    {
                        "id": 2,
                        "tag": "boring"
                    }
                ]

            **Request**

            .. sourcecode:: http

                GET /api/v1/tags?list_agents=true HTTP/1.1
                Accept: application/json

            **Response**

            .. sourcecode:: http

                HTTP/1.1 200 OK
                Content-Type: application/json

                [
                    {
                        "agents": [
                        {
                            "href": "/api/v1/agents/1",
                            "hostname": "agent3",
                            "id": 1
                        }
                        ],
                        "id": 1,
                        "tag": "interesting"
                    },
                    {
                        "agents": [],
                        "id": 2,
                        "tag": "boring"
                    }
                ]

        :qparam list_agents: If true, list all agents for every tag
        :qparam list_agents_full: If true, list agents with full info
        :qparam list_jobs: If true, list all jobs for every tag
        :qparam list_jobs_full: If true, list jobs with full info

        :statuscode 200: no error
        """
        out = []

        for tag in Tag.query.all():
            tag_dict = {"id": tag.id, "tag": tag.tag}

            # TODO Instead of doing one query per tag, do a single big query to
            # get all agent-tag relations
            if request.args.get("list_agents") == "true":
                agents = []
                for agent in tag.agents:
                    agent_entry = {"id": agent.id,
                                   "hostname": agent.hostname,
                                   "href": url_for(".single_agent_api",
                                                   agent_id=agent.id)}
                    if request.args.get("list_agents_full") == "true":
                        agent_entry["data"] = agent.to_dict()
                    agents.append(agent_entry)
                tag_dict["agents"] = agents

            if request.args.get("list_jobs") == "true":
                jobs = []
                for job in tag.jobs:
                    job_entry = {"id": job.id,
                                 # TODO Replace with url_for() once we actually
                                 # have a job endpoint
                                 "href": "/api/v1/jobs/%s" % job.id}
                    if request.args.get("list_jobs_full") == "true":
                        job_entry["data"] = job.to_dict()
                    jobs.append(job_entry)
                tag_dict["jobs"] = jobs

            out.append(tag_dict)

        return jsonify(out), OK


class AgentsInTagIndexAPI(MethodView):
    def post(self, tagname=None):
        """
        A ``POST`` will add an agent to the list of agents tagged with this tag
        The tag can be given as a string or as an integer (its id).

        .. http:post:: /api/v1/tags/interesting/agents HTTP/1.1

            **Request**

            .. sourcecode:: http

                POST /api/v1/tags/interesting/agents HTTP/1.1
                Accept: application/json

                {
                    "agent_id": 1
                }

            **Response (agent newly tagged)**

            .. sourcecode:: http

                HTTP/1.1 201 CREATED
                Content-Type: application/json

                {
                    "href": "/api/v1/agents/1",
                    "id": 1
                }

            **Request**

            .. sourcecode:: http

                POST /api/v1/tags/interesting/agents HTTP/1.1
                Accept: application/json

                {
                    "agent_id": 1
                }

            **Response (agent already had that tag)**

            .. sourcecode:: http

                HTTP/1.1 200 OK
                Content-Type: application/json

                {
                    "href": "/api/v1/agents/1",
                    "id": 1
                }

            **Request**

            .. sourcecode:: http

                POST /api/v1/tags/1/agents HTTP/1.1
                Accept: application/json

                {
                    "agent_id": 1
                }

            **Response (agent already had that tag)**

            .. sourcecode:: http

                HTTP/1.1 200 OK
                Content-Type: application/json

                {
                    "href": "/api/v1/agents/1",
                    "id": 1
                }

        :statuscode 200: an existing tag was found and returned
        :statuscode 201: a new tag was created
        :statuscode 400: there was something wrong with the request (such as
                            invalid columns being included)
        :statuscode 404: either the tag or the referenced agent does not exist
        """
        if isinstance(tagname, STRING_TYPES):
            tag = Tag.query.filter_by(tag=tagname).first()
        else:
            tag = Tag.query.filter_by(tag_id=tagname).first()
        if tag is None:
            return jsonify(message="Tag not found"), NOT_FOUND

        data = json_from_request(request)
        # json_from_request returns a Response object on error
        if isinstance(data, Response):
            return data

        if len(data) > 1:
            return jsonify(errorno=APIError.EXTRA_FIELDS_ERROR,
                           message="Unknown fields in JSON data"), BAD_REQUEST

        if "agent_id" not in data:
            return jsonify(errorno=APIError.MISSING_FIELDS,
                           message="Field agent_id missing"), BAD_REQUEST

        agent = Agent.query.filter_by(id=data["agent_id"]).first()
        if agent is None:
            return jsonify(message="Specified agent does not exist"), NOT_FOUND

        if agent not in tag.agents:
            tag.agents.append(agent)
            db.session.commit()
            logger.info("Added agent %s (%s) to tag %s" % (
                agent.id, agent.hostname, tag.tag))
            return jsonify({"id": agent.id,
                            "href": url_for(".single_agent_api", 
                                              agent_id=agent.id)}), CREATED
        else:
            return jsonify({"id": agent.id,
                            "href": url_for(".single_agent_api", 
                                              agent_id=agent.id)}), OK

    def get(self, tagname=None):
        """
        A ``GET`` to this endpoint will list all agents associated with this tag.

        .. http:get:: /api/v1/tags/interesting/agents HTTP/1.1

            **Request**

            .. sourcecode:: http

                GET /api/v1/tags/interesting/agents HTTP/1.1
                Accept: application/json

            **Response**

            .. sourcecode:: http

                HTTP/1.1 201 CREATED
                Content-Type: application/json

                [
                    {
                        "hostname": "agent3",
                        "id": 1,
                        "href": "/api/v1/agents/1
                    }
                ]

        :statuscode 200: the list of agents associated with this tag is returned
        :statuscode 404: the tag specified does not exist
        """
        if isinstance(tagname, STRING_TYPES):
            tag = Tag.query.filter_by(tag=tagname).first()
        else:
            tag = Tag.query.filter_by(tag_id=tagname).first()
        if tag is None:
            return jsonify(message="Tag not found"), NOT_FOUND

        out = []
        for agent in tag.agents:
            out.append({"id": agent.id,
                        "hostname": agent.hostname,
                        "href": url_for(".single_agent_api", agent_id=agent.id)})

        return jsonify(out), OK
