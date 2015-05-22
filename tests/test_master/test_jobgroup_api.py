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
from pyfarm.master.config import config
from pyfarm.master.entrypoints import load_api
from pyfarm.models.jobgroup import JobGroup


jobtype_code = """from pyfarm.jobtypes.core.jobtype import JobType

class TestJobType(JobType):
    def get_command(self):
        return "/usr/bin/touch"
    def get_arguments(self):
        return [os.path.join(
            self.assignment_data["job"]["data"]["path"],
            "%04d" % self.assignment_data[\"tasks\"][0][\"frame\"])]
"""


class TestJobGroupAPI(BaseTestCase):
    def setup_app(self):
        super(TestJobGroupAPI, self).setup_app()
        self.api = get_api_blueprint()
        self.app.register_blueprint(self.api)
        load_api(self.app, self.api)

    def create_a_jobtype(self):
        response1 = self.client.post(
            "/api/v1/jobtypes/",
            content_type="application/json",
            data=dumps({
                    "name": "TestJobType",
                    "description": "Jobtype for testing inserts and queries",
                    "max_batch": 1,
                    "code": jobtype_code
                    }))
        self.assert_created(response1)
        jobtype_id = response1.json['id']

        return "TestJobType", jobtype_id

    def create_a_jobgroup(self, jobtype_name):
        post_response = self.client.post(
            "/api/v1/jobgroups/",
            content_type="application/json",
            data=dumps({"title": "Test JobGroup",
                        "main_jobtype": jobtype_name,
                        "user": "testuser"}))
        self.assert_created(post_response)

        return post_response.json['id']

    def test_jobgroup_schema(self):
        response = self.client.get("/api/v1/jobgroups/schema")
        self.assert_ok(response)
        schema = JobGroup.to_schema()
        schema["user"] = "VARCHAR(%s)" % config.get("max_username_length")
        del schema["user_id"]
        schema["main_jobtype"] = \
            "VARCHAR(%s)" % config.get("job_type_max_name_length")
        del schema["main_jobtype_id"]
        self.assertEqual(response.json, schema)

    def test_jobgroup_post(self):
        jobtype_name, jobtype_id = self.create_a_jobtype()

        post_response = self.client.post(
            "/api/v1/jobgroups/",
            content_type="application/json",
            data=dumps({"title": "Test JobGroup",
                        "main_jobtype": jobtype_name,
                        "user": "testuser"}))
        self.assert_created(post_response)
        id = post_response.json['id']
        self.assertEqual(
            post_response.json, {
                "id": id,
                "title": "Test JobGroup",
                "main_jobtype": jobtype_name,
                "user": "testuser",
                "jobs": []
               })

        get_response = self.client.get("/api/v1/jobgroups/%s" % id)
        self.assert_ok(get_response)
        self.assertEqual(
            get_response.json, {
                "id": id,
                "title": "Test JobGroup",
                "main_jobtype": jobtype_name,
                "user": "testuser",
                "jobs": []
               })

    def test_jobgroup_post_bad_key(self):
        jobtype_name, jobtype_id = self.create_a_jobtype()

        post_response = self.client.post(
            "/api/v1/jobgroups/",
            content_type="application/json",
            data=dumps({"title": "Test JobGroup",
                        "main_jobtype": jobtype_name,
                        "user": "testuser",
                        "bad_key": 1}))
        self.assert_bad_request(post_response)

    def test_jobgroup_get_unknown(self):
        get_response = self.client.get( "/api/v1/jobgroups/42")
        self.assert_not_found(get_response)

    def test_jobgroup_list(self):
        jobtype_name, jobtype_id = self.create_a_jobtype()
        id = self.create_a_jobgroup(jobtype_name)

        get_response = self.client.get( "/api/v1/jobgroups/")
        self.assert_ok(get_response)
        self.assertEqual(
            get_response.json,[
                {
                "id": id,
                "title": "Test JobGroup",
                "main_jobtype": jobtype_name,
                "user": "testuser"
                }
            ])

    def test_jobgroup_edit(self):
        jobtype_name, jobtype_id = self.create_a_jobtype()
        id = self.create_a_jobgroup(jobtype_name)

        post_response = self.client.post(
            "/api/v1/jobgroups/%s" % id,
            content_type="application/json",
            data=dumps({"title": "Test JobGroup 2",
                        "main_jobtype": jobtype_name,
                        "user": "testuser"}))
        self.assert_ok(post_response)

        self.assertEqual(
            post_response.json, {
                "id": id,
                "title": "Test JobGroup 2",
                "main_jobtype": jobtype_name,
                "user": "testuser",
                "jobs": []
               })

    def test_jobgroup_edit_unknown(self):
        post_response = self.client.post(
            "/api/v1/jobgroups/42",
            content_type="application/json",
            data=dumps({"title": "Test JobGroup 2"}))
        self.assert_not_found(post_response)

    def test_jobgroup_edit_unknown_user(self):
        jobtype_name, jobtype_id = self.create_a_jobtype()
        id = self.create_a_jobgroup(jobtype_name)

        post_response = self.client.post(
            "/api/v1/jobgroups/%s" % id,
            content_type="application/json",
            data=dumps({"user": "unknown_user"}))
        self.assert_not_found(post_response)

    def test_jobgroup_edit_unknown_jobtype(self):
        jobtype_name, jobtype_id = self.create_a_jobtype()
        id = self.create_a_jobgroup(jobtype_name)

        post_response = self.client.post(
            "/api/v1/jobgroups/%s" % id,
            content_type="application/json",
            data=dumps({"main_jobtype": "unknown_jobtype"}))
        self.assert_not_found(post_response)

    def test_jobgroup_edit_bad_key(self):
        jobtype_name, jobtype_id = self.create_a_jobtype()
        id = self.create_a_jobgroup(jobtype_name)

        post_response = self.client.post(
            "/api/v1/jobgroups/%s" % id,
            content_type="application/json",
            data=dumps({"bad_key": 1}))
        self.assert_bad_request(post_response)

    def test_jobgroup_delete(self):
        jobtype_name, jobtype_id = self.create_a_jobtype()
        id = self.create_a_jobgroup(jobtype_name)

        delete_response = self.client.delete( "/api/v1/jobgroups/%s" % id)
        self.assert_no_content(delete_response)

    def test_jobgroup_delete_unknown(self):
        delete_response = self.client.delete( "/api/v1/jobgroups/42")
        self.assert_no_content(delete_response)

    def test_jobgroup_delete_in_use(self):
        jobtype_name, jobtype_id = self.create_a_jobtype()
        id = self.create_a_jobgroup(jobtype_name)

        job_post_response = self.client.post(
            "/api/v1/jobs/",
            content_type="application/json",
            data=dumps({
                    "title": "Test Job",
                    "jobtype": jobtype_name,
                    "data": {"foo": "bar"},
                    "job_group_id": id
                    }))
        self.assert_created(job_post_response)

        delete_response = self.client.delete( "/api/v1/jobgroups/%s" % id)
        self.assert_conflict(delete_response)
