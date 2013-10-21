# No shebang line, this module is meant to be imported
#
# Copyright 2013 Oliver Palmer
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

from flask import abort
from utcore import TestCase
from pyfarm.master.errors import (
    ERROR_400_JSON, ERROR_401_JSON, ERROR_404_JSON, ERROR_500_JSON)
from pyfarm.master.entrypoints.master import load_error_handlers


class TestErrors(TestCase):
    def setUp(self):
        super(TestErrors, self).setUp()
        load_error_handlers(self.app)

    def test_400(self):
        self.app.add_url_rule("/test_error_400", view_func=lambda: abort(400))
        response = self.client.open(
            "/test_error_400",
            method="GET",
            headers=[("Content-Type", "application/json")])
        self.assert400(response)
        self.assertDictEqual(ERROR_400_JSON, response.json)
        response = self.client.get("/test_error_400")
        self.assert400(response)
        self.assertIn("<title>PyFarm - Bad Request</title>", response.data)
        self.assertTemplateUsed("pyfarm/errors/400.html")

    def test_401(self):
        self.app.add_url_rule("/test_error_401", view_func=lambda: abort(401))
        response = self.client.open(
            "/test_error_401",
            method="GET",
            headers=[("Content-Type", "application/json")])
        self.assert401(response)
        self.assertDictEqual(ERROR_401_JSON, response.json)
        response = self.client.get("/test_error_401")
        self.assert401(response)
        self.assertIn("<title>PyFarm - Access Denied</title>", response.data)
        self.assertTemplateUsed("pyfarm/errors/401.html")

    def test_404(self):
        self.app.add_url_rule("/test_error_404", view_func=lambda: abort(404))
        response = self.client.open(
            "/test_error_404",
            method="GET",
            headers=[("Content-Type", "application/json")])
        self.assert404(response)
        self.assertDictEqual(ERROR_404_JSON, response.json)
        response = self.client.get("/test_error_404")
        self.assert404(response)
        self.assertIn("<title>PyFarm - Not Found</title>", response.data)
        self.assertTemplateUsed("pyfarm/errors/404.html")

    def test_500(self):
        self.app.add_url_rule("/test_error_500", view_func=lambda: abort(500))
        response = self.client.open(
            "/test_error_500",
            method="GET",
            headers=[("Content-Type", "application/json")])
        self.assert500(response)
        self.assertDictEqual(ERROR_500_JSON, response.json)
        response = self.client.get("/test_error_500")
        self.assert500(response)
        self.assertIn("<title>PyFarm - Internal Server Error</title>",
                      response.data)
        self.assertTemplateUsed("pyfarm/errors/500.html")

