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

from uuid import UUID

try:
    from httplib import NOT_FOUND, NO_CONTENT, OK, CREATED, BAD_REQUEST
except ImportError:  # pragma: no cover
    from http.client import NOT_FOUND, NO_CONTENT, OK, CREATED, BAD_REQUEST

from flask import url_for, g
from flask.views import MethodView

from pyfarm.core.logger import getLogger
from pyfarm.core.enums import STRING_TYPES
from pyfarm.models.agent import Agent
from pyfarm.models.job import Job
from pyfarm.models.tag import Tag
from pyfarm.master.application import db
from pyfarm.master.utility import jsonify, validate_with_model

logger = getLogger("api.tags")


def schema():
    """
    Returns the basic schema of :class:`.Tag`

    .. http:get:: /api/v1/tags/schema/ HTTP/1.1

        **Request**

        .. sourcecode:: http

            GET /api/v1/tags/schema/ HTTP/1.1
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
    return jsonify(Tag.to_schema())


class TagIndexAPI(MethodView):
    @validate_with_model(Tag)
    def post(self):
        """
        A ``POST`` to this endpoint will do one of two things:

            * create a new tag and return the row
            * return the row for an existing tag

        Tags only have one column, the tag name. Two tags are automatically
        considered equal if the tag names are equal.

        .. http:post:: /api/v1/tags/ HTTP/1.1

            **Request**

            .. sourcecode:: http

                POST /api/v1/tags/ HTTP/1.1
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

                POST /api/v1/tags/ HTTP/1.1
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
        existing_tag = Tag.query.filter_by(tag=g.json["tag"]).first()

        if existing_tag:
            # No update needed, because Tag only has that one column
            return jsonify(existing_tag.to_dict()), OK

        else:
            new_tag = Tag(**g.json)
            db.session.add(new_tag)
            db.session.commit()
            tag_data = new_tag.to_dict(unpack_relationships=("agents", "jobs"))
            logger.info("created tag %s: %r", new_tag.id, tag_data)
            return jsonify(tag_data), CREATED

    def get(self):
        """
        A ``GET`` to this endpoint will return a list of known tags, with id.
        Associated agents and jobs are included for every tag

        :rtype : object
        .. http:get:: /api/v1/tags/ HTTP/1.1

            **Request**

            .. sourcecode:: http

                GET /api/v1/tags/ HTTP/1.1
                Accept: application/json

            **Response**

            .. sourcecode:: http

                HTTP/1.1 200 OK
                Content-Type: application/json

                [
                    {
                        "agents": [
                            1
                        ],
                        "jobs": [],
                        "id": 1,
                        "tag": "interesting"
                    },
                    {
                        "agents": [],
                        "jobs": [],
                        "id": 2,
                        "tag": "boring"
                    }
                ]

        :statuscode 200: no error
        """
        out = []

        for tag in Tag.query.all():
            out.append(tag.to_dict(unpack_relationships=("agents", "jobs")))

        return jsonify(out), OK


class SingleTagAPI(MethodView):
    def get(self, tagname=None):
        """
        A ``GET`` to this endpoint will return the referenced tag, either by
        name or id, including a list of agents and jobs associated with it.

        .. http:get:: /api/v1/tags/<str:tagname> HTTP/1.1

            **Request**

            .. sourcecode:: http

                GET /api/v1/tags/interesting HTTP/1.1
                Accept: application/json

            **Response**

            .. sourcecode:: http

                HTTP/1.1 200 OK
                Content-Type: application/json

                {
                    "agents": [{
                        "hostname": "agent3",
                        "href": "/api/v1/agents/94522b7e-817b-4358-95da-670b31aad624",
                        "id": 1
                    }],
                    "id": 1,
                    "jobs": [],
                    "tag": "interesting"
                }

        :statuscode 200: no error
        :statuscode 404: tag not found
        """
        if isinstance(tagname, STRING_TYPES):
            tag = Tag.query.filter_by(tag=tagname).first()
        else:
            tag = Tag.query.filter_by(id=tagname).first()

        if tag is None:
            return jsonify(error="tag `%s` not found" % tagname), NOT_FOUND

        tag_dict = tag.to_dict(unpack_relationships=("agents", "jobs"))

        return jsonify(tag_dict), OK

    @validate_with_model(Tag, ignore=("tag", ), disallow=("id", ))
    def put(self, tagname=None):
        """
        A ``PUT`` to this endpoint will create a new tag under the given URI.
        If a tag already exists under that URI, it will be deleted, then
        recreated.
        Note that when overwriting a tag like that, all relations that are not
        explicitly specified here will be deleted
        You can optionally specify a list of agents or jobs relations as
        integers in the request data.

        You should only call this by id for overwriting an existing tag or if you
        have a reserved tag id. There is currently no way to reserve a tag id.

        .. http:put:: /api/v1/tags/<str:tagname> HTTP/1.1

            **Request**

            .. sourcecode:: http

                PUT /api/v1/tags/interesting HTTP/1.1
                Accept: application/json

                {
                    "tag": "interesting"
                }

            **Response**

            .. sourcecode:: http

                HTTP/1.1 201 CREATED
                Content-Type: application/json

                {
                    "id": 1,
                    "tag": "interesting"
                }

            **Request**

            .. sourcecode:: http

                PUT /api/v1/tags/interesting HTTP/1.1
                Accept: application/json

                {
                    "tag": "interesting",
                    "agents": [1]
                    "jobs": []
                }

            **Response**

            .. sourcecode:: http

                HTTP/1.1 201 CREATED
                Content-Type: application/json

                {
                    "id": 1,
                    "tag": "interesting"
                }

        :statuscode 201: a new tag was created
        :statuscode 400: there was something wrong with the request (such as
                            invalid columns being included)
        :statuscode 404: a referenced agent or job does not exist
        """
        if isinstance(tagname, int):
            tag = Tag.query.filter_by(id=tagname).first()

            if "tag" in g.json and g.json["tag"] != tag.tag:
                error = "tag name retrieved for %s does not match tag " \
                        "name in request" % tagname
                return jsonify(error=error), BAD_REQUEST

            g.json.setdefault("tag", tag.tag)

        elif isinstance(tagname, STRING_TYPES):
            g.json.setdefault("tag", tagname)

            if g.json["tag"] != tagname:
                return jsonify(error="`tag` in data must be equal to the "
                                     "tag in the requested url"), BAD_REQUEST
            tag = Tag.query.filter_by(tag=g.json["tag"]).first()

        # If tag exists, delete it before recreating it
        if tag:
            logger.debug(
                "tag %s will be replaced with %r on commit", tag.tag, g.json)
            db.session.delete(tag)
            db.session.flush()

        agents = []
        if "agents" in g.json:
            agent_ids = g.json.pop("agents", [])

            if not isinstance(agent_ids, list):
                return jsonify(error="agents must be a list"), BAD_REQUEST

            try:
                agent_ids = list(map(UUID, agent_ids))
            except (ValueError, AttributeError):
                return jsonify(error="All agent ids must be UUIDs"), BAD_REQUEST

            # find all models matching the request id(s)
            agents = Agent.query.filter(Agent.id.in_(agent_ids)).all()

            # make sure all those ids were actually found
            missing_agents = set(agent_ids) - set(agent.id for agent in agents)
            if missing_agents:
                return jsonify(
                    error="agent(s) not found: %s" % missing_agents), NOT_FOUND

        jobs = []
        if "jobs" in g.json:
            job_ids = g.json.pop("jobs", [])

            if not isinstance(job_ids, list):
                return jsonify(error="jobs must be a list"), BAD_REQUEST

            # make sure all ids provided are ints
            if not all(isinstance(job_id, int) for job_id in job_ids):
                return jsonify(
                    error="all job ids must be integers"), BAD_REQUEST

            # find all models matching the request id(s)
            jobs = Job.query.filter(Agent.id.in_(job_ids)).all()

            # make sure all those ids were actually found
            missing_jobs = set(job_ids) - set(job.id for job in jobs)
            if missing_jobs:
                return jsonify(
                    error="job(s) not found: %s" % missing_jobs), NOT_FOUND

        new_tag = Tag(**g.json)
        if isinstance(tagname, int):
            new_tag.id = tagname
        new_tag.agents = agents
        new_tag.jobs = jobs

        logger.info("creating tag %s: %r", new_tag.tag, new_tag.to_dict())
        db.session.add(new_tag)
        db.session.commit()

        return (jsonify(new_tag.to_dict(unpack_relationships=("agents", "jobs"))),
                CREATED)

    def delete(self, tagname=None):
        """
        A ``DELETE`` to this endpoint will delete the tag under this URI,
        including all relations to tags or jobs.

        .. http:delete:: /api/v1/tags/<str:tagname> HTTP/1.1

            **Request**

            .. sourcecode:: http

                DELETE /api/v1/tags/interesting HTTP/1.1
                Accept: application/json

            **Response**

            .. sourcecode:: http

                HTTP/1.1 201 CREATED
                Content-Type: application/json

                {
                    "id": 1,
                    "tag": "interesting"
                }

        :statuscode 204: the tag was deleted or did not exist in the first place
        """
        if isinstance(tagname, STRING_TYPES):
            tag = Tag.query.filter_by(tag=tagname).first()
        else:
            tag = Tag.query.filter_by(id=tagname).first()

        if tag is None:
            return jsonify(None), NO_CONTENT

        db.session.delete(tag)
        db.session.commit()

        logger.info("deleted tag %s", tag.tag)

        return jsonify(None), NO_CONTENT


class AgentsInTagIndexAPI(MethodView):
    def post(self, tagname=None):
        """
        A ``POST`` will add an agent to the list of agents tagged with this tag
        The tag can be given as a string or as an integer (its id).

        .. http:post:: /api/v1/tags/<str:tagname>/agents/ HTTP/1.1

            **Request**

            .. sourcecode:: http

                POST /api/v1/tags/interesting/agents/ HTTP/1.1
                Accept: application/json

                {
                    "agent_id": "dd0c6da2-0c91-42cf-a82f-6d503aae43d3"
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

                POST /api/v1/tags/interesting/agents/ HTTP/1.1
                Accept: application/json

                {
                    "agent_id": "dd0c6da2-0c91-42cf-a82f-6d503aae43d3"
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
            tag = Tag.query.filter_by(id=tagname).first()

        if tag is None:
            return jsonify(error="tag %s not found" % tagname), NOT_FOUND

        if not isinstance(g.json, dict):
            return jsonify(error="expected a json dictionary"), BAD_REQUEST

        request_fields = set(g.json)
        extra_fields = request_fields - set(["agent_id"])

        if extra_fields:
            return jsonify(error="unsupported fields for "
                                 "this request: %s" % extra_fields), BAD_REQUEST

        if "agent_id" not in request_fields:
            return jsonify(error="field `agent_id` is missing"), BAD_REQUEST

        if not isinstance(g.json["agent_id"], STRING_TYPES):
            return jsonify(
                error="Expected a string for `agent_id`"), BAD_REQUEST

        agent = Agent.query.filter_by(id=g.json["agent_id"]).first()
        if agent is None:
            return jsonify(
                error="agent %s does not exist" % g.json["agent_id"]), NOT_FOUND

        if agent not in tag.agents:
            tag.agents.append(agent)
            db.session.commit()
            logger.debug(
                "added agent %s (%s) to tag %s",
                agent.id, agent.hostname, tag.tag)
            return jsonify(
                id=agent.id,
                href=url_for(".single_agent_api", agent_id=agent.id)), CREATED
        else:
            return jsonify(
                id=agent.id,
                href=url_for(".single_agent_api", agent_id=agent.id)), OK

    def get(self, tagname=None):
        """
        A ``GET`` to this endpoint will list all agents associated with this
        tag.

        .. http:get:: /api/v1/tags/<str:tagname>/agents/ HTTP/1.1

            **Request**

            .. sourcecode:: http

                GET /api/v1/tags/interesting/agents/ HTTP/1.1
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
            tag = Tag.query.filter_by(id=tagname).first()

        if tag is None:
            return jsonify(error="tag %s not found" % tagname), NOT_FOUND

        out = []
        for agent in tag.agents:
            out.append({
                "id": agent.id,
                "hostname": agent.hostname,
                "href": url_for(".single_agent_api", agent_id=agent.id)})

        return jsonify(out), OK
