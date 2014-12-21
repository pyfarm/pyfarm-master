# No shebang line, this module is meant to be imported
#
# Copyright 2013 Oliver Palmer
# Copyright 2013 Ambient Entertainment GmbH & Co. KG
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

import uuid

try:
    from httplib import CREATED, NO_CONTENT
except ImportError:
    from http.client import CREATED, NO_CONTENT

# test class must be loaded first
from pyfarm.master.testutil import BaseTestCase
BaseTestCase.build_environment()

from pyfarm.master.utility import default_json_encoder, dumps
from pyfarm.master.application import get_api_blueprint
from pyfarm.master.entrypoints import load_api
from pyfarm.models.agent import Agent


class TestAgentAPI(BaseTestCase):
    def setup_app(self):
        super(TestAgentAPI, self).setup_app()
        self.api = get_api_blueprint()
        self.app.register_blueprint(self.api)
        load_api(self.app, self.api)

    def test_agents_schema(self):
        response = self.client.get("/api/v1/agents/schema")
        self.assert_ok(response)
        self.assertEqual(response.json, Agent.to_schema())

    def test_agent_read_write(self):
        id_ = uuid.uuid4()
        response1 = self.client.post(
            "/api/v1/agents/",
            content_type="application/json",
            data=dumps({
                "id": id_,
                "cpu_allocation": 1.0,
                "cpus": 16,
                "os_class": "windows",
                "os_fullname": "Windows 7 SP1",
                "cpu_name": "Zilog Z80",
                "free_ram": 133,
                "hostname": "testagent1",
                "remote_ip": "10.0.200.1",
                "port": 64994,
                "ram": 2048,
                "ram_allocation": 0.8,
                "state": "running"}))
        self.assert_created(response1)
        id = response1.json["id"]
        self.assertIn("last_heard_from", response1.json)
        last_heard_from = response1.json["last_heard_from"]

        response2 = self.client.get("/api/v1/agents/%d" % id)
        self.assert_ok(response2)
        self.assertEqual(
            response2.json, {
                "systemid": 42,
                "ram": 2048,
                "cpu_allocation": 1.0,
                "use_address": "remote",
                "remote_ip": "10.0.200.1",
                "hostname": "testagent1",
                "version": None,
                "upgrade_to": None,
                "cpus": 16,
                "os_class": "windows",
                "os_fullname": "Windows 7 SP1",
                "cpu_name": "Zilog Z80",
                "ram_allocation": 0.8,
                "port": 64994,
                "time_offset": 0,
                "state": "running",
                "free_ram": 133,
                "id": id,
                "last_heard_from": last_heard_from})

    def test_create_agent(self):
        agents = [
            {"cpu_allocation": 1.0, "cpus": 16, "free_ram": 133, "systemid": 3,
             "hostname": "testagent2", "remote_ip": "10.0.200.2", "port": 64994,
             "ram": 2048, "ram_allocation": 0.8, "state": "running"},
            {"cpu_allocation": 1.0, "cpus": 16, "free_ram": 133, "systemid": 5,
             "hostname": "testagent2", "remote_ip": "10.0.200.2", "port": 64995,
             "ram": 2048, "ram_allocation": 0.8, "state": "running"},
            {"cpu_allocation": 1.0, "cpus": 16, "free_ram": 133, "systemid": 7,
             "hostname": "testagent2", "remote_ip": "10.0.200.2", "port": 64996,
             "ram": 2048, "ram_allocation": 0.8, "state": "running"}]
        expected_agents = [
            {"free_ram": 133, "ram_allocation": 0.8, "id": 1,
             "ram": 2048, "time_offset": 0, "systemid": 3, "cpu_allocation": 1.0,
             "state": "running", "port": 64994, "cpus": 16, "cpu_name": None,
             "hostname": "testagent2", "version": None, "upgrade_to": None,
             "use_address": "remote", "remote_ip": "10.0.200.2",
             "os_class": None, "os_fullname": None,},
            {"free_ram": 133, "ram_allocation": 0.8, "id": 2,
             "ram": 2048, "time_offset": 0, "systemid": 5, "cpu_allocation": 1.0,
             "state": "running", "port": 64995, "cpus": 16, "cpu_name": None,
             "hostname": "testagent2", "version": None, "upgrade_to": None,
             "use_address": "remote", "remote_ip": "10.0.200.2",
             "os_class": None, "os_fullname": None,},
            {"free_ram": 133, "ram_allocation": 0.8, "id": 3,
             "ram": 2048, "time_offset": 0, "systemid": 7, "cpu_allocation": 1.0,
             "state": "running", "port": 64996, "cpus": 16, "cpu_name": None,
             "hostname": "testagent2", "version": None, "upgrade_to": None,
             "use_address": "remote", "remote_ip": "10.0.200.2",
             "os_class": None, "os_fullname": None,}]

        created_agents = []
        for agent in agents:
            response = self.client.post(
                "/api/v1/agents/",
                content_type="application/json",
                data=dumps(agent))
            self.assert_created(response)
            self.assertIn("last_heard_from", response.json)
            del response.json["last_heard_from"]
            created_agents.append(response.json)

        self.assert_contents_equal(created_agents, expected_agents)

    def test_post_agents(self):
        response1 = self.client.post(
            "/api/v1/agents/",
            content_type="application/json",
            data=dumps({
                "systemid": 3,
                "cpu_allocation": 1.0,
                "cpus": 16,
                "os_class": "linux",
                "os_fullname": "Linux-3.17.4-glibc-2.2",
                "cpu_name": "Zilog Z80",
                "free_ram": 133,
                "hostname": "testagent3",
                "remote_ip": "10.0.200.3",
                "port": 64994,
                "ram": 2048,
                "ram_allocation": 0.8,
                "state": "running"}))
        self.assert_created(response1)
        id = response1.json["id"]

        # Using this endpoint, we should be able to change everything about an
        # agent except its id
        response2 = self.client.post(
            "/api/v1/agents/%d" % id,
            content_type="application/json",
            data=dumps({
                "systemid": 3,
                "cpu_allocation": 1.2,
                "ram": 8192,
                "use_address": "hostname",
                "remote_ip": "10.0.200.4",
                "hostname": "testagent3-1",
                "cpus": 64,
                "os_class": "mac",
                "os_fullname": "Mac OS X 10.10",
                "cpu_name": "6502",
                "ram_allocation": 0.2,
                "port": 64995,
                "time_offset": 5,
                "state": "running",
                "free_ram": 4096}))
        self.assert_ok(response2)
        self.assertIn("last_heard_from", response2.json)
        last_heard_from = response2.json["last_heard_from"]

        # See if we get the updated data back
        response3 = self.client.get("/api/v1/agents/%d" % id)
        self.assert_ok(response3)
        self.assertEqual(response3.json, {
            "systemid": 3,
            "ram": 8192,
            "cpu_allocation": 1.2,
            "use_address": "hostname",
            "remote_ip": "10.0.200.4",
            "hostname": "testagent3-1",
            "version": None,
            "upgrade_to": None,
            "cpus": 64,
            "os_class": "mac",
            "os_fullname": "Mac OS X 10.10",
            "cpu_name": "6502",
            "ram_allocation": 0.2,
            "port": 64995,
            "time_offset": 5,
            "state": "running",
            "free_ram": 4096,
            "id": id,
            "last_heard_from": last_heard_from})

    def test_agent_delete(self):
        agent_id = uuid.uuid4()
        response1 = self.client.post(
            "/api/v1/agents/",
            content_type="application/json",
            data=dumps({
                "id": agent_id,
                "cpu_allocation": 1.0,
                "cpus": 16,
                "free_ram": 133,
                "hostname": "testagent4",
                "remote_ip": "10.0.200.5",
                "port": 64994,
                "ram": 2048,
                "ram_allocation": 0.8,
                "state": "running"}))
        self.assert_created(response1)
        id = response1.json["id"]

        response2 = self.client.delete("/api/v1/agents/%d" % id)
        self.assert_no_content(response2)
        response3 = self.client.delete("/api/v1/agents/%d" % id)
        self.assert_no_content(response3)
        response4 = self.client.get("/api/v1/agents/%d" % id)
        self.assert_not_found(response4)


class TestAgentAPIFilter(BaseTestCase):
    def setup_app(self):
        super(TestAgentAPIFilter, self).setup_app()
        self.api = get_api_blueprint()
        self.app.register_blueprint(self.api)
        load_api(self.app, self.api)

    def setUp(self):
        super(TestAgentAPIFilter, self).setUp()
        self.assert_created(self.client.post(
            "/api/v1/agents/",
            content_type="application/json",
            data=dumps({
                "systemid": 1,
                "cpu_allocation": 1.0,
                "cpus": 8,
                "free_ram": 133,
                "hostname": "lowcpu-lowram",
                "remote_ip": "10.0.200.6",
                "port": 64994,
                "ram": 1024,
                "ram_allocation": 0.8,
                "state": "running"})))

        self.assert_created(self.client.post(
            "/api/v1/agents/",
            content_type="application/json",
            data=dumps({
                "systemid": 3,
                "cpu_allocation": 1.0,
                "cpus": 8,
                "free_ram": 133,
                "hostname": "lowcpu-highram",
                "remote_ip": "10.0.200.7",
                "port": 64994,
                "ram": 4096,
                "ram_allocation": 0.8,
                "state": "running"})))

        self.assert_created(self.client.post(
            "/api/v1/agents/",
            content_type="application/json",
            data=dumps({
                "systemid": 5,
                "cpu_allocation": 1.0,
                "cpus": 16,
                "free_ram": 133,
                "hostname": "highcpu-lowram",
                "remote_ip": "10.0.200.8",
                "port": 64994,
                "ram": 1024,
                "ram_allocation": 0.8,
                "state": "running"})))

        self.assert_created(self.client.post(
            "/api/v1/agents/",
            content_type="application/json",
            data=dumps({
                "systemid": 7,
                "cpu_allocation": 1.0,
                "cpus": 16,
                "free_ram": 133,
                "hostname": "highcpu-highram",
                "remote_ip": "10.0.200.9",
                "port": 64994,
                "ram": 4096,
                "ram_allocation": 0.8,
                "state": "running"})))

        self.assert_created(self.client.post(
            "/api/v1/agents/",
            content_type="application/json",
            data=dumps({
                "systemid": 9,
                "cpu_allocation": 1.0,
                "cpus": 12,
                "free_ram": 133,
                "hostname": "middlecpu-middleram",
                "remote_ip": "10.0.200.10",
                "port": 64994,
                "ram": 2048,
                "ram_allocation": 0.8,
                "state": "running"})))

    def test_bad_arguments(self):
        response = self.client.get("/api/v1/agents/?min_ram=!")
        self.assert_bad_request(response)
        response = self.client.get("/api/v1/agents/?max_ram=!")
        self.assert_bad_request(response)
        response = self.client.get("/api/v1/agents/?min_cpus=!")
        self.assert_bad_request(response)
        response = self.client.get("/api/v1/agents/?max_cpus=!")
        self.assert_bad_request(response)
        response = self.client.get("/api/v1/agents/?hostname=!")
        self.assert_bad_request(response)
        response = self.client.get("/api/v1/agents/?remote_ip=!")
        self.assert_bad_request(response)
        response = self.client.get("/api/v1/agents/?port=!")
        self.assert_bad_request(response)

    def test_no_results(self):
        response = self.client.get("/api/v1/agents/?min_cpus=1234567890")
        self.assert_ok(response)
        self.assertEqual(response.json, [])

    def test_hostname(self):
        response = self.client.get("/api/v1/agents/?hostname=highcpu-lowram")
        self.assert_ok(response)
        self.assert_contents_equal(response.json, [
            {"hostname": "highcpu-lowram", "remote_ip": "10.0.200.8",
             "id": 3, "port": 64994}])

    def test_ip(self):
        response = self.client.get("/api/v1/agents/?remote_ip=10.0.200.8")
        self.assert_ok(response)
        self.assert_contents_equal(response.json, [
            {"hostname": "highcpu-lowram", "id": 3,
             "port": 64994, "remote_ip": "10.0.200.8"}])

    def test_port(self):
        response = self.client.get("/api/v1/agents/?port=64994")
        self.assert_ok(response)
        self.assert_contents_equal(response.json, [
            {"port": 64994, "remote_ip": "10.0.200.9",
             "hostname": "highcpu-highram", "id": 4},
            {"port": 64994, "remote_ip": "10.0.200.8",
             "hostname": "highcpu-lowram", "id": 3},
            {"port": 64994, "remote_ip": "10.0.200.7",
             "hostname": "lowcpu-highram", "id": 2},
            {"port": 64994, "remote_ip": "10.0.200.6",
             "hostname": "lowcpu-lowram", "id": 1},
            {"port": 64994, "remote_ip": "10.0.200.10",
             "hostname": "middlecpu-middleram", "id": 5}])

    def test_min_cpus(self):
        response = self.client.get("/api/v1/agents/?min_cpus=9")
        self.assert_ok(response)
        self.assert_contents_equal(response.json, [
            {"id": 3, "port": 64994,
             "hostname": "highcpu-lowram", "remote_ip": "10.0.200.8"},
            {"id": 4, "port": 64994,
             "hostname": "highcpu-highram", "remote_ip": "10.0.200.9"},
            {"id": 5, "port": 64994,
             "hostname": "middlecpu-middleram", "remote_ip": "10.0.200.10"}])

        response = self.client.get("/api/v1/agents/?min_cpus=8")
        self.assert_ok(response)
        self.assert_contents_equal(response.json, [
            {"port": 64994, "remote_ip": "10.0.200.6",
             "id": 1, "hostname": "lowcpu-lowram"},
            {"port": 64994, "remote_ip": "10.0.200.7",
             "id": 2, "hostname": "lowcpu-highram"},
            {"port": 64994, "remote_ip": "10.0.200.8",
             "id": 3, "hostname": "highcpu-lowram"},
            {"port": 64994, "remote_ip": "10.0.200.9",
             "id": 4, "hostname": "highcpu-highram"},
            {"port": 64994, "remote_ip": "10.0.200.10",
             "id": 5, "hostname": "middlecpu-middleram"}])

    def test_max_cpus(self):
        response = self.client.get("/api/v1/agents/?max_cpus=12")
        self.assert_ok(response)
        self.assert_contents_equal(response.json, [
            {"id": 1, "hostname": "lowcpu-lowram",
             "remote_ip": "10.0.200.6", "port": 64994},
            {"id": 2, "hostname": "lowcpu-highram",
             "remote_ip": "10.0.200.7", "port": 64994},
            {"id": 5, "hostname": "middlecpu-middleram",
             "remote_ip": "10.0.200.10", "port": 64994}])

        response = self.client.get(
            "/api/v1/agents/?min_cpus=10&max_cpus=14")
        self.assert_ok(response)
        self.assertEqual(response.json, [
            {"remote_ip": "10.0.200.10", "hostname": "middlecpu-middleram",
             "id": 5, "port": 64994}])

    def test_min_ram(self):
        response = self.client.get("/api/v1/agents/?min_ram=1024")
        self.assert_ok(response)
        self.assert_contents_equal(response.json, [
            {"hostname": "lowcpu-lowram", "id": 1,
             "remote_ip": "10.0.200.6", "port": 64994},
            {"hostname": "lowcpu-highram", "id": 2,
             "remote_ip": "10.0.200.7", "port": 64994},
            {"hostname": "highcpu-lowram", "id": 3,
             "remote_ip": "10.0.200.8", "port": 64994},
            {"hostname": "highcpu-highram", "id": 4,
             "remote_ip": "10.0.200.9", "port": 64994},
            {"hostname": "middlecpu-middleram", "id": 5,
             "remote_ip": "10.0.200.10", "port": 64994}])

        response = self.client.get("/api/v1/agents/?min_ram=2048")
        self.assert_ok(response)
        self.assert_contents_equal(response.json, [
            {"hostname": "lowcpu-highram", "remote_ip": "10.0.200.7",
             "port": 64994, "id": 2},
            {"hostname": "highcpu-highram", "remote_ip": "10.0.200.9",
             "port": 64994, "id": 4},
            {"hostname": "middlecpu-middleram", "remote_ip": "10.0.200.10",
             "port": 64994, "id": 5}])

    def test_max_ram(self):
        response = self.client.get("/api/v1/agents/?max_ram=2048")
        self.assert_ok(response)
        self.assert_contents_equal(response.json, [
            {"hostname": "lowcpu-lowram", "remote_ip": "10.0.200.6",
             "port": 64994, "id": 1},
            {"hostname": "highcpu-lowram", "remote_ip": "10.0.200.8",
             "port": 64994, "id": 3},
            {"hostname": "middlecpu-middleram", "remote_ip": "10.0.200.10",
             "port": 64994, "id": 5}])

        response = self.client.get(
            "/api/v1/agents/?min_ram=1025&max_ram=2049")
        self.assert_ok(response)
        self.assert_contents_equal(response.json, [
            {"hostname": "middlecpu-middleram", "remote_ip": "10.0.200.10",
             "port": 64994, "id": 5}])

    def test_min_ram_and_min_cpus(self):
        response = self.client.get(
            "/api/v1/agents/?min_ram=2048&min_cpus=16")
        self.assert_ok(response)
        self.assert_contents_equal(response.json, [
            {"hostname": "highcpu-highram",
             "remote_ip": "10.0.200.9", "port": 64994, "id": 4}])
