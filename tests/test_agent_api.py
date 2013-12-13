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

import os
from utcore import ModelTestCase
from pyfarm.master.utility import dumps
try:
    from json import loads
except ImportError:
    from simplejson import loads

class TestAgentAPI(ModelTestCase):
    def test_agents_schema(self):
        response = self.client.get("/api/v1/agents/schema")
        self.assert200(response)
        self.assertEquals(response.json, {"ram": "INTEGER",
                                          "free_ram": "INTEGER",
                                          "use_address": "INTEGER",
                                          "ip": "IPv4Address",
                                          "hostname": "VARCHAR(255)",
                                          "cpus": "INTEGER",
                                          "port": "INTEGER",
                                          "state": "INTEGER",
                                          "ram_allocation": "FLOAT",
                                          "cpu_allocation": "FLOAT",
                                          "id": "INTEGER",
                                          "remote_ip": "IPv4Address"})

    def test_agent_read_write(self):
        response1 = self.client.post("/api/v1/agents",
                                    content_type="application/json",
                                    data = dumps({"cpu_allocation": 1.0,
                                        "cpus": 16,
                                        "free_ram": 133,
                                        "hostname": "testagent1",
                                        "ip": "10.0.200.1",
                                        "port": 64994,
                                        "ram": 2048,
                                        "ram_allocation": 0.8,
                                        "state": 8
                                        }))
        self.assertStatus(response1, 201)
        id = loads(response1.data)['id']

        response2 = self.client.get("/api/v1/agents/%d" % id)
        self.assert200(response2)
        agent_data = loads(response2.data)
        assert len(agent_data) == 12
        assert response2.json == {
                                    "ram": 2048,
                                    "cpu_allocation": 1.0,
                                    "use_address": 22,
                                    "ip": "10.0.200.1",
                                    "hostname": "testagent1",
                                    "cpus": 16,
                                    "ram_allocation": 0.8,
                                    "port": 64994,
                                    "state": 8,
                                    "free_ram": 133,
                                    "id": id,
                                    "remote_ip": None
                                    }
        # TODO Test updating an agent
