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

import os
import uuid

try:
    from httplib import BAD_REQUEST, UNSUPPORTED_MEDIA_TYPE
except ImportError:
    from http.client import BAD_REQUEST, UNSUPPORTED_MEDIA_TYPE

from flask import Flask, Blueprint, g
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.login import LoginManager
from itsdangerous import URLSafeTimedSerializer
from werkzeug.routing import BaseConverter, ValidationError

# test class must be loaded first
from pyfarm.master.testutil import BaseTestCase
BaseTestCase.build_environment()

from pyfarm.master.utility import jsonify
from pyfarm.master.application import (
    UUIDConverter, get_application, get_api_blueprint,
    get_sqlalchemy, get_login_manager, get_login_serializer)


class TestApplicationFunctions(BaseTestCase):
    def test_get_application(self):
        app = get_application(SOME_VARIABLE=True)
        self.assertIsInstance(app, Flask)
        self.assertTrue(app.config["SOME_VARIABLE"])
        self.assertEqual(app.name, "pyfarm.master")
        import pyfarm.master
        static_folder = os.path.join(
            os.path.dirname(pyfarm.master.__file__), "static")
        self.assertEqual(app.static_folder, static_folder)

    def test_get_api_blueprint(self):
        api = get_api_blueprint(url_prefix="/foo")
        self.assertIsInstance(api, Blueprint)
        self.assertEqual(api.url_prefix, "/foo")
        self.assertEqual(api.name, "api")
        self.assertEqual(api.import_name, "pyfarm.master.api")

    def test_get_sqlalchemy(self):
        self.assertIsInstance(get_sqlalchemy(app=self.app), SQLAlchemy)

    def test_get_login_manager(self):
        lm = get_login_manager()
        self.assertIsInstance(lm, LoginManager)
        self.assertEqual(lm.login_view, "/login/")
        lm = get_login_manager(login_view="/new_login_view/")
        self.assertEqual(lm.login_view, "/new_login_view/")

    def test_get_login_serializer(self):
        secret_key = os.urandom(32)
        ls = get_login_serializer(secret_key)
        self.assertIsInstance(ls, URLSafeTimedSerializer)
        self.assertEqual(ls.secret_key, secret_key)

    def test_request_handler(self):
        @self.app.route("/", methods=("POST", ))
        def test_api():
            return jsonify(success=True)

        response = self.client.post(
            "/", headers={"Content-Type": "application/json2"}, data={})
        self.assert_ok(response)
        self.assertEqual(response.json, {"success": True})
        self.assertIsNotNone(g.json)


class TestUUIDConverter(BaseTestCase):
    def test_instance(self):
        instance = UUIDConverter(self.app.url_map)
        self.assertIsInstance(instance, BaseConverter)

    def test_to_python_uuid(self):
        value = uuid.uuid4()
        instance = UUIDConverter(self.app.url_map)
        self.assertIs(instance.to_python(value), value)

    def test_to_python_hex(self):
        value = uuid.uuid4()
        instance = UUIDConverter(self.app.url_map)
        self.assertEqual(value, instance.to_python(value.hex))

    def test_to_python_error(self):
        instance = UUIDConverter(self.app.url_map)
        with self.assertRaises(ValidationError):
            instance.to_python("")

    def test_to_url_string(self):
        value = uuid.uuid4()
        instance = UUIDConverter(self.app.url_map)
        self.assertEqual(instance.to_url(value.hex), str(value))

    def test_to_url_bytes(self):
        value = uuid.uuid4()
        instance = UUIDConverter(self.app.url_map)
        self.assertEqual(instance.to_url(value.bytes), str(value))

    def test_to_url_error(self):
        instance = UUIDConverter(self.app.url_map)
        with self.assertRaises(ValidationError):
            instance.to_url("")
