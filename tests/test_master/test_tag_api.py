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


try:
    from httplib import CREATED, NO_CONTENT
except ImportError:
    from http.client import CREATED, NO_CONTENT

# test class must be loaded first
from pyfarm.master.testutil import BaseTestCase
BaseTestCase.build_environment()

from pyfarm.master.application import get_api_blueprint, before_request
from pyfarm.master.entrypoints.main import load_api
from pyfarm.models.tag import Tag


class TestTagAPI(BaseTestCase):
    def setup_app(self):
        super(TestTagAPI, self).setup_app()
        self.api = get_api_blueprint()
        self.app.register_blueprint(self.api)
        load_api(self.app, self.api)

        @self.app.before_request
        def before_each_request():
            return before_request()

    def test_tags_schema(self):
        response = self.client.get("/api/v1/tags/schema")
        self.assert_ok(response)
        self.assertEqual(response.json, Tag.to_schema())

    def test_tag_post(self):
        response1 = self.client.post(
            "/api/v1/tags/",
            content_type="application/json",
            data=dumps({
                "tag": "foo"}))
        self.assert_created(response1)
        id = response1.json['id']

        response2 = self.client.get("/api/v1/tags/%d" % id)
        self.assert_ok(response2)
        self.assertEqual(
            response2.json, {
                "agents": [],
                "id": 1,
                "jobs": [],
                "tag": "foo"
                })

    def test_tag_post_existing(self):
        response1 = self.client.post(
            "/api/v1/tags/",
            content_type="application/json",
            data=dumps({
                "tag": "foo"}))
        self.assert_created(response1)

        response2 = self.client.post(
            "/api/v1/tags/",
            content_type="application/json",
            data=dumps({
                "tag": "foo"}))
        self.assert_ok(response2)

    def test_tag_put(self):
        response1 = self.client.put(
            "/api/v1/tags/foo",
            content_type="application/json",
            data=dumps({
                "tag": "foo"}))
        self.assert_created(response1)

        # Must be idempotent
        response2 = self.client.put(
            "/api/v1/tags/foo",
            content_type="application/json",
            data=dumps({
                "tag": "foo"}))
        self.assert_created(response2)
        id = response2.json['id']

        response3 = self.client.get("/api/v1/tags/foo")
        self.assert_ok(response3)
        self.assertEqual(
            response3.json, {
                "agents": [],
                "id": id,
                "jobs": [],
                "tag": "foo"
                })

    def test_tag_put_mismatch(self):
        response1 = self.client.put(
            "/api/v1/tags/foo",
            content_type="application/json",
            data=dumps({
                "tag": "bar"}))
        self.assert_bad_request(response1)

    def test_tag_put_with_wrong_agent(self):
        response1 = self.client.put(
            "/api/v1/tags/foo",
            content_type="application/json",
            data=dumps({
                "tag": "foo",
                "agents": [1]}))
        self.assert_not_found(response1)

    def test_tag_put_with_agents(self):
        # create an agent to link to
        response1 = self.client.post(
            "/api/v1/agents",
            content_type="application/json",
            data=dumps({
                "cpu_allocation": 1.0,
                "cpus": 16,
                "free_ram": 133,
                "hostname": "testagent1",
                "ip": "10.0.200.1",
                "port": 64994,
                "ram": 2048,
                "ram_allocation": 0.8,
                "state": "running"}))
        self.assert_created(response1)
        agent_id = response1.json['id']

        response2 = self.client.put(
            "/api/v1/tags/foo",
            content_type="application/json",
            data=dumps({
                "tag": "foo",
                "agents": [agent_id]}))
        self.assert_created(response2)

    def test_tag_put_mismatch_with_agents(self):
        # create an agent to link to
        response1 = self.client.post(
            "/api/v1/agents",
            content_type="application/json",
            data=dumps({
                "cpu_allocation": 1.0,
                "cpus": 16,
                "free_ram": 133,
                "hostname": "testagent1",
                "ip": "10.0.200.1",
                "port": 64994,
                "ram": 2048,
                "ram_allocation": 0.8,
                "state": "running"}))
        self.assert_created(response1)
        agent_id = response1.json['id']

        response2 = self.client.put(
            "/api/v1/tags/foo",
            content_type="application/json",
            data=dumps({
                "tag": "bar",
                "agents": [agent_id]}))
        self.assert_bad_request(response2)

    def test_tag_delete(self):
        response1 = self.client.put(
            "/api/v1/tags/foo",
            content_type="application/json",
            data=dumps({
                "tag": "foo"}))
        self.assert_created(response1)

        response2 = self.client.delete("/api/v1/tags/foo")
        self.assert_no_content(response2)

        response3 = self.client.get("/api/v1/tags/foo")
        self.assert_not_found(response3)

        # Must be idempotent
        response4 = self.client.delete("/api/v1/tags/foo")
        self.assert_no_content(response4)

        response5 = self.client.get("/api/v1/tags/foo")
        self.assert_not_found(response5)

    def test_tag_post_agent(self):
        # create an agent to link to
        response1 = self.client.post(
            "/api/v1/agents",
            content_type="application/json",
            data=dumps({
                "cpu_allocation": 1.0,
                "cpus": 16,
                "free_ram": 133,
                "hostname": "testagent1",
                "ip": "10.0.200.1",
                "port": 64994,
                "ram": 2048,
                "ram_allocation": 0.8,
                "state": "running"}))
        self.assert_created(response1)
        agent_id = response1.json['id']

        response2 = self.client.put(
            "/api/v1/tags/foo",
            content_type="application/json",
            data=dumps({
                "tag": "foo"}))
        self.assert_created(response2)

        response3 = self.client.post(
            "/api/v1/tags/foo/agents/",
            content_type="application/json",
            data=dumps({
                "agent_id": agent_id}))
        self.assert_created(response3)

        response4 = self.client.get(
            "/api/v1/tags/foo/agents/",
            content_type="application/json")
        self.assert_ok(response4)
        self.assertEqual(response4.json, [{"hostname": "testagent1",
                                           "href": "/api/v1/agents/1",
                                           "id": agent_id}])
