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
    from httplib import OK, CREATED, CONFLICT, NOT_FOUND, NO_CONTENT, BAD_REQUEST
except ImportError:  # pragma: no cover
    from http.client import (
        OK, CREATED, CONFLICT, NOT_FOUND, NO_CONTENT, BAD_REQUEST)

from flask import g
from flask.views import MethodView

from pyfarm.core.logger import getLogger
from pyfarm.core.enums import STRING_TYPES

from pyfarm.models.job import Job
from pyfarm.models.jobqueue import JobQueue
from pyfarm.master.application import db
from pyfarm.master.utility import jsonify, validate_with_model


logger = getLogger("api.jobqueues")


# Load model mappings once per process
JOBQUEUE_MODEL_MAPPINGS = JobQueue.types().mappings


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
                    "parent": null,
                    "parent_jobqueue_id": null
                }

        :statuscode 201: a new job queue was created
        :statuscode 400: there was something wrong with the request (such as
                         invalid columns being included)
        :statuscode 409: a job queue with that name already exists
        """
        jobqueue = JobQueue.query.filter_by(name=g.json["name"]).first()
        if jobqueue:
            return (jsonify(error="Job queue %s already exists" %
                            g.json["name"]), CONFLICT)

        jobqueue = JobQueue(**g.json)
        db.session.add(jobqueue)
        db.session.flush()

        jobqueue.fullpath = jobqueue.path()
        db.session.add(jobqueue)
        db.session.commit()

        jobqueue_data = jobqueue.to_dict()
        logger.info("Created job queue %s: %r", jobqueue.name, jobqueue_data)

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
            return (jsonify(error="Requested job queue %r not found" % queue_rq),
                    NOT_FOUND)

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
            return (jsonify(error="Requested job queue %r not found" % queue_rq),
                    NOT_FOUND)

        # This would allow users to create circles in the job queue tree
        if "parent_jobqueue_id" in g.json:
            return (jsonify(error="The parent queue cannot be changed"),
                    BAD_REQUEST)

        for name in JOBQUEUE_MODEL_MAPPINGS:
            if name in g.json:
                expected_type = JOBQUEUE_MODEL_MAPPINGS[name]
                value = g.json.pop(name)
                if not isinstance(value, expected_type):
                    return (jsonify(error="Column `%s` is of type %r, but we "
                                    "expected %r" % (name,
                                                     type(value),
                                                     expected_type)),
                                    BAD_REQUEST)
                setattr(jobqueue, name, value)

        if g.json:
            return jsonify(error="Unkown columns: %s" % g.json), BAD_REQUEST

        # It is possible for a call to this to change a queue's name
        db.session.add(jobqueue)
        db.session.flush()
        jobqueue.fullpath = jobqueue.path()
        for childqueue in jobqueue.children:
            childqueue.fullpath = childqueue.path()
            db.session.add(childqueue)

        db.session.add(jobqueue)
        db.session.commit()

        jobqueue_data = jobqueue.to_dict()
        logger.info("Updated job queue %s: %r", jobqueue.name, jobqueue_data)

        return jsonify(jobqueue_data), OK

    def delete(self, queue_rq):
        """
        A ``DELETE`` to this endpoint will delete the specified job queue

        .. http:delete:: /api/v1/jobqueue/HTTP/[<str:name>|<int:id>] 1.1

            **Request**

            .. sourcecode:: http

                DELETE /api/v1/jobs/Test%20Queue HTTP/1.1
                Accept: application/json

            **Response**

            .. sourcecode:: http

                HTTP/1.1 204 NO_CONTENT

        :statuscode 204: the job queue was deleted or didn't exist
        :statuscode 409: the job queue cannot be deleted because it still
                         contains jobs or child queues
        """
        if isinstance(queue_rq, STRING_TYPES):
            jobqueue = JobQueue.query.filter_by(name=queue_rq).first()
        else:
            jobqueue = JobQueue.query.filter_by(id=queue_rq).first()

        if not jobqueue:
            return jsonify(), NO_CONTENT

        num_sub_queues = JobQueue.query.filter_by(parent=jobqueue).count()
        if num_sub_queues > 0:
            return (jsonify(error="Cannot delete: job queue has child queues"),
                    CONFLICT)

        num_jobs = Job.query.filter_by(queue=jobqueue).count()
        if num_jobs > 0:
            return (jsonify(error="Cannot delete: job queue has jobs assigned"),
                    CONFLICT)

        db.session.delete(jobqueue)
        db.session.commit()
        logger.info("Deleted job queue %s", jobqueue.name)

        return jsonify(), NO_CONTENT
