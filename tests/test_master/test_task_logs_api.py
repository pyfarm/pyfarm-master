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


class TestTaskLogsAPI(BaseTestCase):
    def setup_app(self):
        super(TestTaskLogsAPI, self).setup_app()
        self.api = get_api_blueprint()
        self.app.register_blueprint(self.api)
        load_api(self.app, self.api)

    def make_objects(self):
        response1 = self.client.post(
            "/api/v1/agents/",
            content_type="application/json",
            data=dumps({
                "systemid": 42,
                "cpu_allocation": 1.0,
                "cpus": 16,
                "free_ram": 133,
                "hostname": "testagent1",
                "remote_ip": "10.0.200.1",
                "port": 64994,
                "ram": 2048,
                "ram_allocation": 0.8,
                "state": "running"}))
        self.assert_created(response1)
        agent_id = response1.json["id"]

        response2 = self.client.post(
            "/api/v1/jobtypes/",
            content_type="application/json",
            data=dumps({
                    "name": "TestJobType",
                    "description": "Jobtype for testing inserts and queries",
                    "max_batch": 1,
                    "code": "dummy code"
                    }))
        self.assert_created(response2)
        jobtype_id = response2.json['id']

        response3 = self.client.post(
            "/api/v1/jobs/",
            content_type="application/json",
            data=dumps({
                    "start": 1.0,
                    "end": 1.0,
                    "title": "Test Job",
                    "jobtype": "TestJobType",
                    "data": {"foo": "bar"},
                    "software_requirements": []
                    }))
        self.assert_created(response3)
        job_id = response3.json["id"]

        response4 = self.client.get("/api/v1/jobs/%s/tasks/" % job_id)
        self.assert_ok(response4)
        self.assertEqual(len(response4.json), 1)

        return job_id, response4.json[0]["id"], agent_id

    def test_task_logs_register_logfile(self):
        job_id, task_id, agent_id = self.make_objects()

        response1 = self.client.post(
            "/api/v1/jobs/%s/tasks/%s/attempts/1/logs/" % (job_id, task_id),
            content_type="application/json",
            data=dumps({
                "identifier": "testlogidentifier",
                "agent_id": agent_id}))
        self.assert_created(response1)
        created_on = response1.json["created_on"]

        response2 = self.client.get("/api/v1/jobs/%s/tasks/%s/attempts/1/logs/" %
                                    (job_id, task_id))
        self.assert_ok(response2)
        self.assertEqual(response2.json,
                         [{
                             "identifier": "testlogidentifier",
                             "agent_id": agent_id,
                             "created_on": created_on
                         }])

    def test_task_logs_get_index_unknown_task(self):
        response1 = self.client.get("/api/v1/jobs/42/tasks/42/attempts/1/logs/")
        self.assert_not_found(response1)

    def test_task_logs_register_logfile_unknown_task(self):
        response1 = self.client.post(
            "/api/v1/jobs/42/tasks/42/attempts/1/logs/",
            content_type="application/json",
            data=dumps({
                "identifier": "testlogidentifier",
                "agent_id": 1}))
        self.assert_not_found(response1)

    def test_task_logs_register_logfile_twice(self):
        job_id, task_id, agent_id = self.make_objects()

        response1 = self.client.post(
            "/api/v1/jobs/%s/tasks/%s/attempts/1/logs/" % (job_id, task_id),
            content_type="application/json",
            data=dumps({
                "identifier": "testlogidentifier",
                "agent_id": agent_id}))
        self.assert_created(response1)
        created_on = response1.json["created_on"]

        response2 = self.client.post(
            "/api/v1/jobs/%s/tasks/%s/attempts/1/logs/" % (job_id, task_id),
            content_type="application/json",
            data=dumps({
                "identifier": "testlogidentifier",
                "agent_id": agent_id}))
        self.assert_conflict(response2)

    def test_task_logs_get_single_log(self):
        job_id, task_id, agent_id = self.make_objects()

        response1 = self.client.post(
            "/api/v1/jobs/%s/tasks/%s/attempts/1/logs/" % (job_id, task_id),
            content_type="application/json",
            data=dumps({
                "identifier": "testlogidentifier",
                "agent_id": agent_id}))
        self.assert_created(response1)
        created_on = response1.json["created_on"]
        log_id = response1.json["id"]

        response2 = self.client.get(
            "/api/v1/jobs/%s/tasks/%s/attempts/1/logs/testlogidentifier" %
                (job_id, task_id))
        self.assert_ok(response2)
        self.assertEqual(response2.json,
                         {
                             "identifier": "testlogidentifier",
                             "agent_id": agent_id,
                             "created_on": created_on,
                             "id": log_id
                         })

    def test_task_logs_get_single_log_unknown_task(self):
        response1 = self.client.get(
            "/api/v1/jobs/42/tasks/42/attempts/1/logs/testlogidentifier")
        self.assert_not_found(response1)

    def test_task_logs_get_single_unknown_log(self):
        job_id, task_id, agent_id = self.make_objects()

        response1 = self.client.get(
            "/api/v1/jobs/%s/tasks/%s/attempts/1/logs/testlogidentifier" %
                (job_id, task_id))
        self.assert_not_found(response1)

    def test_task_logs_get_single_log_wrong_task(self):
        job_id, task_id, agent_id = self.make_objects()

        response1 = self.client.post(
            "/api/v1/jobs/%s/tasks/%s/attempts/1/logs/" % (job_id, task_id),
            content_type="application/json",
            data=dumps({
                "identifier": "testlogidentifier",
                "agent_id": agent_id}))
        self.assert_created(response1)

        response2 = self.client.post(
            "/api/v1/jobs/",
            content_type="application/json",
            data=dumps({
                    "start": 1.0,
                    "end": 1.0,
                    "title": "Test Job 2",
                    "jobtype": "TestJobType",
                    "data": {"foo": "bar"},
                    "software_requirements": []
                    }))
        self.assert_created(response2)
        job2_id = response2.json["id"]

        response3 = self.client.get("/api/v1/jobs/%s/tasks/" % job2_id)
        self.assert_ok(response3)
        self.assertEqual(len(response3.json), 1)
        task2_id = response3.json[0]["id"]

        response4 = self.client.get(
            "/api/v1/jobs/%s/tasks/%s/attempts/1/logs/testlogidentifier" %
                (job2_id, task2_id))
        self.assert_not_found(response4)

    def test_task_logs_upload_logfile(self):
        job_id, task_id, agent_id = self.make_objects()

        response1 = self.client.post(
            "/api/v1/jobs/%s/tasks/%s/attempts/1/logs/" % (job_id, task_id),
            content_type="application/json",
            data=dumps({
                "identifier": "testlogidentifier",
                "agent_id": agent_id}))
        self.assert_created(response1)
        created_on = response1.json["created_on"]

        response2 = self.client.put(
            "/api/v1/jobs/%s/tasks/%s/attempts/1/logs/testlogidentifier/logfile"
            % (job_id, task_id),
            content_type="text/csv",
            data="1,test log entry\n"
                 "2,another test log entry")
        self.assert_created(response2)
