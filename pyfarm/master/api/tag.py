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

from flask import Response, request
from flask.views import MethodView

from pyfarm.core.logger import getLogger
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

    .. http:get:: /api/v1/tag/schema HTTP/1.1

        **Request**

        .. sourcecode:: http

            GET /api/v1/tag/schema HTTP/1.1
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

        .. http:post:: /api/v1/tag HTTP/1.1

            **Request**

            .. sourcecode:: http

                POST /api/v1/tag HTTP/1.1
                Accept: application/json

                {
                    "tag": "interesting"
                }


            **Response (new tag create)**

            .. sourcecode:: http

                HTTP/1.1 200 OK
                Content-Type: application/json

                {
                    "id": 1,
                    "tag": "interesting"
                }

            **Request**

            .. sourcecode:: http

                POST /api/v1/tag HTTP/1.1
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

        :qparam list_agents: If true, list all agents for every tag
        :qparam list_agents_full: If true, list agents with full info
        :qparam list_jobs: If true, list all jobs for every tag
        :qparam list_jobs_full: If true, list jobs with full info

        :statuscode 200: no error
        """
        out = []

        for tag in Tag.query.all():
            tag_dict = {"id": tag.id, "tag": tag.tag}

            if (request.args.get("list_agents") == "true" or
                request.args.get("list_agents_full") == "true"):
                agents = []
                for agent in tag.agents:
                    if request.args.get("list_agents_full") != "true":
                        agents.append({"id": agent.id,
                                       "hostname": agent.hostname})
                    else:
                        agents.append(agent.to_dict())
                tag_dict["agents"] = agents

            if (request.args.get("list_jobs") == "true" or
                request.args.get("list_jobs_full") == "true"):
                jobs = []
                for job in tag.jobs:
                    if request.args.get("list_jobs_full") != "true":
                        jobs.append({"id": job.id})
                    else:
                        jobs.append(job.to_dict())
                tag_dict["jobs"] = jobs

            out.append(tag_dict)

        return jsonify(out), OK


class AgentsInTagAPI(MethodView):
    def get(self, tag=None):
        out = []

        if (isinstance(tag, unicode) or
            isinstance(tag, str)):
            q = db.session.query(
                Agent.id,
                Agent.hostname).join(
                    AgentTagAssociation).join(
                        Tag).filter_by(tag=tag)
        else:
            q = db.session.query(
                Agent.id,
                Agent.hostname).join(
                    AgentTagAssociation).filter_by(tag_id=tag)

        for agent_id, hostname in q:
            out.append({"id": agent_id, "hostname": hostname})

        return jsonify(out), OK
