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

from json import dumps


# test class must be loaded first
from pyfarm.master.testutil import BaseTestCase
BaseTestCase.build_environment()

from pyfarm.master.application import get_api_blueprint
from pyfarm.master.entrypoints import load_api
from pyfarm.models.jobqueue import JobQueue


class TestJobQueueAPI(BaseTestCase):
    def setup_app(self):
        super(TestJobQueueAPI, self).setup_app()
        self.api = get_api_blueprint()
        self.app.register_blueprint(self.api)
        load_api(self.app, self.api)

    def test_jobqueue_schema(self):
        response = self.client.get("/api/v1/jobqueues/schema")
        self.assert_ok(response)
        schema = JobQueue.to_schema()
        self.assertEqual(response.json, schema)

    def test_jobqueue_post(self):
        response1 = self.client.post(
            "/api/v1/jobqueues/",
            content_type="application/json",
            data=dumps({"name": "Test JobQueue"}))
        self.assert_created(response1)
        id = response1.json['id']

        response2 = self.client.get("/api/v1/jobqueues/Test%20JobQueue")
        self.assert_ok(response2)
        self.assertEqual(
            response2.json, {
                "id": id,
                "name": "Test JobQueue",
                "parent": None,
                "minimum_agents": None,
                "maximum_agents": None,
                "parent_jobqueue_id": None,
                "priority": 0,
                "weight": 10,
                "jobs": [],
                "children": []
                })

        response3 = self.client.get("/api/v1/jobqueues/%s" % id)
        self.assert_ok(response3)
        self.assertEqual(
            response3.json, {
                "id": id,
                "name": "Test JobQueue",
                "parent": None,
                "minimum_agents": None,
                "maximum_agents": None,
                "parent_jobqueue_id": None,
                "priority": 0,
                "weight": 10,
                "jobs": [],
                "children": []
                })

    def test_jobqueue_post_conflict(self):
        response1 = self.client.post(
            "/api/v1/jobqueues/",
            content_type="application/json",
            data=dumps({"name": "Test JobQueue"}))
        self.assert_created(response1)

        response2 = self.client.post(
            "/api/v1/jobqueues/",
            content_type="application/json",
            data=dumps({"name": "Test JobQueue"}))
        self.assert_conflict(response2)

    def test_jobqueue_list(self):
        response1 = self.client.post(
            "/api/v1/jobqueues/",
            content_type="application/json",
            data=dumps({"name": "Test JobQueue"}))
        self.assert_created(response1)
        id = response1.json['id']

        response2 = self.client.get("/api/v1/jobqueues/")
        self.assert_ok(response2)
        self.assertEqual(
            response2.json, [
                    {
                        "weight": 10,
                        "priority": 0,
                        "parent_jobqueue_id": None,
                        "id": id,
                        "maximum_agents": None,
                        "minimum_agents": None,
                        "name": "Test JobQueue"
                    }
                ])

    def test_jobqueue_get_unknown(self):
        response1 = self.client.get("/api/v1/jobqueues/Unknown%20JobQueue")
        self.assert_not_found(response1)

    def test_jobqueue_edit(self):
        response1 = self.client.post(
            "/api/v1/jobqueues/",
            content_type="application/json",
            data=dumps({"name": "Test JobQueue"}))
        self.assert_created(response1)
        id = response1.json['id']

        response2 = self.client.post(
            "/api/v1/jobqueues/Test%20JobQueue",
            content_type="application/json",
            data=dumps({
                "weight": 20,
                "minimum_agents": 3
                }))
        self.assert_ok(response2)
        self.assertEqual(
            response2.json, {
                "id": id,
                "name": "Test JobQueue",
                "parent": None,
                "minimum_agents": 3,
                "maximum_agents": None,
                "parent_jobqueue_id": None,
                "priority": 0,
                "weight": 20,
                "jobs": [],
                "children": []
                })

        response3 = self.client.post(
            "/api/v1/jobqueues/%s" % id,
            content_type="application/json",
            data=dumps({
                "priority": 1
                }))
        self.assert_ok(response3)
        self.assertEqual(
            response3.json, {
                "id": id,
                "name": "Test JobQueue",
                "parent": None,
                "minimum_agents": 3,
                "maximum_agents": None,
                "parent_jobqueue_id": None,
                "priority": 1,
                "weight": 20,
                "jobs": [],
                "children": []
                })

    def test_jobqueue_edit_unknown_key(self):
        response1 = self.client.post(
            "/api/v1/jobqueues/",
            content_type="application/json",
            data=dumps({"name": "Test JobQueue"}))
        self.assert_created(response1)
        id = response1.json['id']

        response2 = self.client.post(
            "/api/v1/jobqueues/Test%20JobQueue",
            content_type="application/json",
            data=dumps({
                "unknown_key": True
                }))
        self.assert_bad_request(response2)

    def test_jobqueue_edit_unknown_queue(self):
        response1 = self.client.post(
            "/api/v1/jobqueues/Unknown%20JobQueue",
            content_type="application/json",
            data=dumps({
                "weight": 29
                }))
        self.assert_not_found(response1)

    def test_jobqueue_edit_parent(self):
        response1 = self.client.post(
            "/api/v1/jobqueues/",
            content_type="application/json",
            data=dumps({"name": "Test JobQueue"}))
        self.assert_created(response1)
        id = response1.json['id']

        response2 = self.client.post(
            "/api/v1/jobqueues/Test%20JobQueue",
            content_type="application/json",
            data=dumps({
                "parent_jobqueue_id": 1
                }))
        self.assert_bad_request(response2)

    def test_jobqueue_delete(self):
        response1 = self.client.post(
            "/api/v1/jobqueues/",
            content_type="application/json",
            data=dumps({"name": "Test JobQueue"}))
        self.assert_created(response1)

        response2 = self.client.delete("/api/v1/jobqueues/Test%20JobQueue")
        self.assert_no_content(response2)

        response3 = self.client.get("/api/v1/jobqueues/Test%20JobQueue")
        self.assert_not_found(response3)

    def test_jobqueue_delete_unknown(self):
        response1 = self.client.delete("/api/v1/jobqueues/Unknown%20JobQueue")
        self.assert_no_content(response1)

    def test_jobqueue_delete_with_child_queues(self):
        response1 = self.client.post(
            "/api/v1/jobqueues/",
            content_type="application/json",
            data=dumps({"name": "Test JobQueue"}))
        self.assert_created(response1)
        parent_id = response1.json["id"]

        response2 = self.client.post(
            "/api/v1/jobqueues/",
            content_type="application/json",
            data=dumps({
                "name": "Child Queue",
                "parent_jobqueue_id": parent_id}))
        self.assert_created(response2)

        response3 = self.client.delete("/api/v1/jobqueues/%s" % parent_id)
        self.assert_conflict(response3)

    def test_jobqueue_delete_with_jobs(self):
        response1 = self.client.post(
            "/api/v1/jobqueues/",
            content_type="application/json",
            data=dumps({"name": "Test JobQueue"}))
        self.assert_created(response1)
        parent_id = response1.json["id"]

        response2 = self.client.post(
            "/api/v1/jobtypes/",
            content_type="application/json",
            data=dumps({
                    "name": "TestJobType",
                    "description": "Jobtype for testing inserts and queries",
                    "max_batch": 1,
                    "code": "ignored"
                    }))
        self.assert_created(response2)
        jobtype_id = response2.json['id']

        response3 = self.client.post(
            "/api/v1/jobs/",
            content_type="application/json",
            data=dumps({
                    "start": 1.0,
                    "end": 2.0,
                    "title": "Test Job",
                    "jobtype": "TestJobType",
                    "data": {"foo": "bar"},
                    "job_queue_id": parent_id
                    }))
        self.assert_created(response3)

        response4 = self.client.delete("/api/v1/jobqueues/Test%20JobQueue")
        self.assert_conflict(response4)
