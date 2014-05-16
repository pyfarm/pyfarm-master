# No shebang line, this module is meant to be imported
#
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
Job Queues
----------

This module defines an API for managing and querying job queues
"""
try:
    from httplib import OK, CREATED, CONFLICT, NOT_FOUND
except ImportError:  # pragma: no cover
    from http.client import OK, CREATED, CONFLICT, NOT_FOUND

from flask import g
from flask.views import MethodView

from pyfarm.core.logger import getLogger
from pyfarm.core.enums import STRING_TYPES

from pyfarm.models.jobqueue import JobQueue
from pyfarm.master.application import db
from pyfarm.master.utility import jsonify, validate_with_model


logger = getLogger("api.jobqueues")


def schema():
    """
    Returns the basic schema of :class:`.JobQueue`

    .. http:get:: /api/v1/jobqueues/schema HTTP/1.1

        **Request**

        .. sourcecode:: http

            GET /api/v1/jobqueues/schema HTTP/1.1
            Accept: application/json

        **Response**

        .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                "id": "INTEGER",
                "name": VARCHAR(255)",
                "minimum_agents": "INTEGER",
                "maximum_agents": "INTEGER",
                "priority": "INTEGER",
                "weight": "INTEGER",
                "parent_jobqueue_id": "INTEGER"
            }

    :statuscode 200: no error
    """
    return jsonify(JobQueue.to_schema()), OK


class JobQueueIndexAPI(MethodView):
    @validate_with_model(JobQueue)
    def post(self):
        """
        A ``POST`` to this endpoint will create a new job queue.

        .. http:post:: /api/v1/jobqueues/ HTTP/1.1

            **Request**

            .. sourcecode:: http

                POST /api/v1/jobqueues/ HTTP/1.1
                Accept: application/json

                {
                    "name": "Test Queue"
                }


            **Response**

            .. sourcecode:: http

                HTTP/1.1 201 CREATED
                Content-Type: application/json

                {
                    "weight": 10,
                    "jobs": [],
                    "minimum_agents": null,
                    "priority": 5,
                    "name": "Test Queue",
                    "maximum_agents": null,
                    "id": 1,
                    "parent": [],
                    "parent_jobqueue_id": null
                }

        :statuscode 201: a new job queue was created
        :statuscode 400: there was something wrong with the request (such as
                            invalid columns being included)
        :statuscode 409: a job queue with that name already exists
        """
        jobqueue = JobQueue.query.filter_by(name=g.json["name"]).first()
        if jobqueue:
            return (jsonify(error="Job queue %s already exixts" %
                            g.json["name"]), CONFLICT)

        jobqueue = JobQueue(**g.json)
        db.session.add(jobqueue)
        db.session.commit()

        jobqueue_data = jobqueue.to_dict()
        logger.info("created job queue %s: %r", jobqueue.name, jobqueue_data)

        return jsonify(jobqueue_data), CREATED

    def get(self):
        """
        A ``GET`` to this endpoint will return a list of known job queues.

        .. http:get:: /api/v1/jobqueues/ HTTP/1.1

            **Request**

            .. sourcecode:: http

                GET /api/v1/jobqueues/ HTTP/1.1
                Accept: application/json

            **Response**

            .. sourcecode:: http

                HTTP/1.1 200 OK
                Content-Type: application/json

                [
                    {
                        "priority": 5,
                        "weight": 10,
                        "parent_jobqueue_id": null,
                        "name": "Test Queue",
                        "minimum_agents": null,
                        "id": 1,
                        "maximum_agents": null
                    },
                    {
                        "priority": 5,
                        "weight": 10,
                        "parent_jobqueue_id": null,
                        "name": "Test Queue 2",
                        "minimum_agents": null,
                        "id": 2,
                        "maximum_agents": null
                    }
                ]

        :statuscode 200: no error
        """
        out = []
        for jobqueue in JobQueue.query:
            out.append(jobqueue.to_dict(unpack_relationships=False))

        return jsonify(out), OK


class SingleJobQueueAPI(MethodView):
    def get(self, queue_rq):
        """
        A ``GET`` to this endpoint will return the requested job queue

        .. http:get:: /api/v1/jobqueues/[<str:name>|<int:id>] HTTP/1.1

            **Request**

            .. sourcecode:: http

                GET /api/v1/software/Test%20Queue HTTP/1.1
                Accept: application/json

            **Response**

            .. sourcecode:: http

                HTTP/1.1 200 OK
                Content-Type: application/json

                {
                    "id": 1,
                    "parent": [],
                    "jobs": [],
                    "weight": 10,
                    "parent_jobqueue_id": null,
                    "priority": 5,
                    "minimum_agents": null,
                    "name": "Test Queue",
                    "maximum_agents": null
                }

        :statuscode 200: no error
        :statuscode 404: the requested job queue was not found
        """
        if isinstance(queue_rq, STRING_TYPES):
            jobqueue = JobQueue.query.filter_by(name=queue_rq).first()
        else:
            jobqueue = JobQueue.query.filter_by(id=queue_rq).first()

        if not jobqueue:
            return jsonify(error="Requested job queue not found"), NOT_FOUND

        return jsonify(jobqueue.to_dict()), OK

    def post(self, queue_rq):
        """
        A ``POST`` to this endpoint will update the specified queue with the data
        in the request.  Columns not specified in the request will be left as
        they are.

        .. http:post:: /api/v1/jobqueues/[<str:name>|<int:id>] HTTP/1.1

            **Request**

            .. sourcecode:: http

                PUT /api/v1/jobs/Test%20Queue HTTP/1.1
                Accept: application/json

                {
                    "priority": 6
                }

            **Response**

            .. sourcecode:: http

                HTTP/1.1 201 OK
                Content-Type: application/json

                {
                    "id": 1,
                    "parent": [],
                    "jobs": [],
                    "weight": 10,
                    "parent_jobqueue_id": null,
                    "priority": 6,
                    "minimum_agents": null,
                    "name": "Test Queue",
                    "maximum_agents": null
                }

        :statuscode 200: the job queue was updated
        :statuscode 400: there was something wrong with the request (such as
                            invalid columns being included)
        """
        if isinstance(queue_rq, STRING_TYPES):
            jobqueue = JobQueue.query.filter_by(name=queue_rq).first()
        else:
            jobqueue = JobQueue.query.filter_by(id=queue_rq).first()

        if not jobqueue:
            return jsonify(error="Requested job queue not found"), NOT_FOUND

        # This would allow users to create circles in the job queue tree
        if "parent_jobqueue_id" in g.json:
            return (jsonify(error="The parent queue cannot be changed"),
                    BAD_REQUEST)

        for name in JobQueue.types().columns:
            if name in g.json:
                type = JobQueue.types().mappings[name]
                value = g.json.pop(name)
                if not isinstance(value, type):
                    return (jsonify(error="Column `%s` is of type %r, but we "
                                    "expected %r" % (name,
                                                     type(value),
                                                     type)), BAD_REQUEST)
                setattr(jobqueue, name, value)

        db.session.add(jobqueue)
        db.session.commit()

        jobqueue_data = jobqueue.to_dict()
        logger.info("updated job queue %s: %r", jobqueue.name, jobqueue_data)

        return jsonify(jobqueue_data), OK
