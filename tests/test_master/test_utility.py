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

from json import dumps
from functools import partial

try:
    from httplib import OK, BAD_REQUEST
except ImportError:
    from http.client import OK, BAD_REQUEST

from flask import g, request
from voluptuous import Schema

# test class must be loaded first
from pyfarm.master.testutil import BaseTestCase
BaseTestCase.build_environment()

from pyfarm.core.enums import PY3, NOTSET
from pyfarm.models.core.mixins import UtilityMixins
from pyfarm.master.entrypoints import load_error_handlers, load_admin
from pyfarm.master.application import db, get_admin
from pyfarm.models.core.cfg import TABLE_PREFIX
from pyfarm.master.utility import (
    validate_with_model, error_handler, assert_mimetypes, inside_request,
    get_g, validate_json, jsonify, get_request_argument)


class ColumnSetTest(db.Model):
    __tablename__ = "%s_column_set_test" % TABLE_PREFIX
    a = db.Column(db.Integer, primary_key=True)
    b = db.Column(db.Integer, nullable=True)
    c = db.Column(db.Integer, nullable=False)
    d = db.Column(db.Integer, nullable=False, default=0)


class ValidationTestModel(db.Model, UtilityMixins):
    __tablename__ = "%s_validate_with_model_test" % TABLE_PREFIX
    id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    a = db.Column(db.Integer, nullable=False)
    b = db.Column(db.Integer, nullable=False, default=1)


class FakeRequest(object):
    def __init__(self, data, raise_error=False):
        self.data = data
        self.raise_error = raise_error

    def get_json(self):
        if self.raise_error:
            raise ValueError("FAILED")
        return self.data


class UtilityTestCase(BaseTestCase):
    def setup_app(self):
        super(UtilityTestCase, self).setup_app()
        load_error_handlers(self.app)
        admin = get_admin(app=self.app)
        load_admin(admin)

    def setUp(self):
        super(UtilityTestCase, self).setUp()
        self.post = partial(
            self.client.post, headers={"Content-Type": "application/json"})
        self.get = partial(
            self.client.get, headers={"Content-Type": "application/json"})

    def add_route(self, function, methods=None):
        assert callable(function)

        @self.app.route("/", methods=methods or ("GET", "POST"))
        def view():
            return function()


class TestValidateWithModel(UtilityTestCase):
    def test_no_data_to_decode(self):
        @validate_with_model(ValidationTestModel)
        def test():
            return ""

        self.add_route(test)
        response = self.post("/")
        self.assertIn("error", response.json)
        self.assertEqual(response.json["error"], "no data to decode")

    def test_invalid_type(self):
        @validate_with_model(ValidationTestModel)
        def test():
            return ""

        self.add_route(test)
        response = self.post("/", data=dumps(["foo", "bar"]))
        self.assertIn("error", response.json)
        self.assertEqual(
            response.json["error"], "dictionary expected but got list instead")

    def test_fields_dont_exist(self):
        @validate_with_model(ValidationTestModel)
        def test():
            return ""

        self.add_route(test)
        response = self.post("/", data=dumps({"foobar": True}))
        self.assertIn("error", response.json)
        if PY3:
            error_message = "request contains field(s) that do not exist: " \
                            "{'foobar'}"
        else:
            error_message = "request contains field(s) that do not exist: " \
                            "set([u'foobar'])"
        self.assertEqual(response.json["error"], error_message)

    def test_missing_required_fields(self):
        @validate_with_model(ValidationTestModel)
        def test():
            return ""

        self.add_route(test)
        response = self.post("/", data=dumps({"b": 1}))
        self.assertIn("error", response.json)
        if PY3:
            error_message = "request is missing field(s): {'a'}"
        else:
            error_message = "request is missing field(s): set(['a'])"
        self.assertEqual(response.json["error"], error_message)

    def test_type_check(self):
        @validate_with_model(ValidationTestModel)
        def test():
            return ""

        self.add_route(test)
        response = self.post("/", data=dumps({"a": "foobar"}))
        self.assertIn("error", response.json)
        if PY3:
            error_message = "field 'a' has type <class 'str'> but we " \
                            "expected type(s) <class 'int'>"
        else:
            error_message = "field 'a' has type <type 'unicode'> " \
                            "but we expected type(s) (<type 'int'>, " \
                            "<type 'long'>)"
        self.assertEqual(response.json["error"], error_message)

    def test_custom_type_check_false(self):
        with self.assertRaises(AssertionError):
            @validate_with_model(ValidationTestModel, type_checks=["a"])
            def test():
                return ""

        def a_type_check(value):
            return False

        @validate_with_model(
            ValidationTestModel, type_checks={"a": a_type_check})
        def test():
            return ""

        self.add_route(test)
        response = self.post("/", data=dumps({"a": 1}))
        self.assert_bad_request(response)

    def test_custom_type_check_true(self):
        with self.assertRaises(AssertionError):
            @validate_with_model(ValidationTestModel, type_checks=["a"])
            def test():
                return ""

        def a_type_check(value):
            return True

        @validate_with_model(
            ValidationTestModel, type_checks={"a": a_type_check})
        def test():
            return ""

        self.add_route(test)
        response = self.post("/", data=dumps({"a": 1}))
        self.assert_ok(response)

    def test_custom_type_check_with_custom_error(self):
        with self.assertRaises(AssertionError):
            @validate_with_model(ValidationTestModel, type_checks=["a"])
            def test():
                return ""

        def a_type_check(value):
            g.error = "bad"
            return False

        @validate_with_model(
            ValidationTestModel, type_checks={"a": a_type_check})
        def test():
            return ""

        self.add_route(test)
        response = self.post("/", data=dumps({"a": 1}))
        self.assert_bad_request(response)
        self.assertEqual(response.json, {"error": "bad"})

    def test_custom_type_check_invalid_output(self):
        with self.assertRaises(AssertionError):
            @validate_with_model(ValidationTestModel, type_checks=["a"])
            def test():
                return ""

        def a_type_check(value):
            return None

        @validate_with_model(
            ValidationTestModel, type_checks={"a": a_type_check})
        def test():
            return ""

        self.add_route(test)
        response = self.post("/", data=dumps({"a": 1}))
        self.assert_internal_server_error(response)
        self.assertEqual(
            response.json,
            {"error": "expected custom type check function for "
                      "'a' to return True or False"})

    def test_accepts_json_only(self):
        @validate_with_model(ValidationTestModel)
        def test():
            return ""

        self.add_route(test)
        response = self.post(
            "/", headers={"Content-Type": "foo"})
        self.assert_unsupported_media_type(response)
        self.assertIn(
            "Unsupported Media Type",
            response.data.decode())

    def test_disallowed_in_request(self):
        @validate_with_model(ValidationTestModel, disallow=("a", ))
        def test():
            return ""

        self.add_route(test)
        response = self.post("/", data=dumps({"a": 1}))
        self.assert_bad_request(response)
        self.assertIn(
            "column(s) not allowed for this request:", response.json["error"])
        self.assertIn("'a'", response.json["error"])


class TestErrorHandler(BaseTestCase):
    def setup_app(self):
        super(TestErrorHandler, self).setup_app()
        admin = get_admin(app=self.app)
        load_admin(admin)

        if hasattr(request, "_parsed_content_type"):
            self.original_content_type = request._parsed_content_type
        else:
            self.original_content_type = None

    def setUp(self):
        super(TestErrorHandler, self).setUp()
        g.error = None

        if self.original_content_type:
            request._parsed_content_type = self.original_content_type

    def test_invalid_code_type(self):
        with self.assertRaises(AssertionError):
            error_handler(None, code="")

    def test_invalid_code(self):
        with self.assertRaises(AssertionError):
            error_handler(None, code=9999)

    def test_invalid_error_type(self):
        with self.assertRaises(AssertionError):
            error_handler(None, code=BAD_REQUEST, default=None, title="")

    def test_invalid_title_type(self):
        with self.assertRaises(AssertionError):
            error_handler(None, code=BAD_REQUEST, default="", title=1)

    def test_callable_default(self):
        response, code = error_handler(
            None, code=BAD_REQUEST, default=lambda: "foobar", title="")
        self.assertIn("foobar", response.json["error"])

    def test_defaults_to_http_message(self):
        response, code = error_handler(
            None, code=BAD_REQUEST, default=lambda: "foobar")
        self.assertIn("foobar", response.json["error"])

    def test_response_code(self):
        response, code = error_handler(
            None, code=BAD_REQUEST, default=lambda: "foobar", title="")
        self.assertEqual(code, BAD_REQUEST)

    def test_json_response(self):
        setattr(request, "_parsed_content_type", ["application/json"])
        response, code = error_handler(
            None, code=BAD_REQUEST, default=lambda: "foobar", title="")
        self.assertEqual(response.json, {"error": "foobar"})

    def test_custom_g_error(self):
        g.error = "custom error"
        response, code = error_handler(
            None, code=BAD_REQUEST, default=lambda: "foobar", title="")
        self.assertIn("custom error", response.json["error"])


class TestRequestFunctions(UtilityTestCase):
    def test_assert_good_mimetypes(self):
        def test():
            assert_mimetypes(request, ["foo"])
            return ""

        self.add_route(test)
        response = self.post("/", headers={"Content-Type": "foo"})
        self.assert_ok(response)

    def test_assert_bad_mimetypes(self):
        def test():
            assert_mimetypes(request, [""])
            return ""

        self.add_route(test)
        response = self.post("/", headers={"Content-Type": "foo"})
        self.assert_unsupported_media_type(response)

    def test_inside_request(self):
        # Due to how the application is setup in the global
        # scope of tests, we can't test the condition where
        # this returns False.
        self.assertTrue(inside_request())

    def test_get_g(self):
        def test():
            g.foo = True
            self.assertTrue(get_g("foo", bool))
            return ""

        self.add_route(test)
        response = self.post("/", headers={"Content-Type": ""})
        self.assert_ok(response)

    def test_get_g_missing(self):
        def test():
            self.assertTrue(get_g("foo", bool))
            return ""

        self.add_route(test)
        response = self.post("/", headers={"Content-Type": ""})
        self.assert_internal_server_error(response)
        self.assertIn("`g` is lacking the `foo`", response.data.decode())

    def test_g_notset(self):
        def test():
            g.foo = NOTSET
            self.assertTrue(get_g("foo", bool))
            return ""

        self.add_route(test)
        response = self.post("/", headers={"Content-Type": ""})
        self.assert_internal_server_error(response)
        self.assertIn("`g.foo` has not been set", response.data.decode())

    def test_g_type_error(self):
        def test():
            g.foo = 1
            self.assertTrue(get_g("foo", bool))
            return ""

        self.add_route(test)
        response = self.post("/", headers={"Content-Type": ""})
        self.assert_bad_request(response)
        self.assertIn(
            "expected an instance of object but got", response.data.decode())

    def test_validate_json_unknown_input(self):
        @validate_json(None)
        def test():
            return ""

        self.add_route(test)
        response = self.post("/", data=dumps({"foo": True}))
        self.assert_internal_server_error(response)
        self.assertEqual(
            response.json,
            {"error": "Only know how to handle callable objects or instances "
                      "of instances of voluptuous.Schema."})

    def test_validate_json_callable_no_return_data(self):
        def validate(data):
            self.assertEqual(data, {"foo": True})

        @validate_json(validate)
        def test():
            return ""

        self.add_route(test)

        response = self.post("/", data=dumps({"foo": True}))
        self.assert_internal_server_error(response)
        self.assertEqual(
            response.json,
            {"error": "Output from callable validator should be a "
                      "string or boolean."})

    def test_validate_json_callable_internal_error(self):
        def validate(data):
            self.assertEqual(data, {"foo": True})
            raise Exception("FOOBAR")

        @validate_json(validate)
        def test():
            return ""

        self.add_route(test)
        response = self.post("/", data=dumps({"foo": True}))
        self.assert_internal_server_error(response)
        self.assertEqual(
            response.json,
            {"error": "Error while running validator: FOOBAR"})

    def test_validate_json_callable_returns_error(self):
        def validate(data):
            self.assertEqual(data, {"foo": True})
            return "FOOBAR"

        @validate_json(validate)
        def test():
            return ""

        self.add_route(test)
        response = self.post("/", data=dumps({"foo": True}))
        self.assert_bad_request(response)
        self.assertEqual(response.json, {"error": "FOOBAR"})

    def test_validate_json_callable_ok(self):
        def validate(data):
            self.assertEqual(data, {"foo": True})
            return True

        @validate_json(validate)
        def test():
            self.assertEqual(g.json, {"foo": True})
            return jsonify(g.json)

        self.add_route(test)
        response = self.post("/", data=dumps({"foo": True}))
        self.assert_ok(response)
        self.assertEqual({"foo": True}, response.json)

    def test_validate_json_schema_success(self):
        schema = Schema({"foo": bool})

        @validate_json(schema)
        def test():
            self.assertEqual(g.json, {"foo": True})
            return jsonify(g.json)

        self.add_route(test)
        response = self.post("/", data=dumps({"foo": True}))
        self.assert_ok(response)
        self.assertEqual({"foo": True}, response.json)

    def test_validate_json_schema_failure(self):
        schema = Schema({"foo": str})

        @validate_json(schema)
        def test():
            self.assertEqual(g.json, {"foo": True})
            return jsonify(g.json)

        self.add_route(test)
        response = self.post("/", data=dumps({"foo": True}))
        self.assert_bad_request(response)

        if PY3:
            error = {"error": "expected str for dictionary value @ data['foo']"}

        else:
            error = {
                u"error": u"expected str for dictionary value @ data[u'foo']"}

        self.assertEqual(response.json, error)


class TestRequestArgumentParser(UtilityTestCase):
    def test_required(self):
        def test():
            return jsonify(
                get_request_argument("number", types=int, required=True))

        self.add_route(test)
        response = self.get("/")
        self.assert_bad_request(response)
        self.assertIn(
            "Required argument `number` is not present",
            response.json["error"])

    def test_type_conversion(self):
        def test():
            return jsonify(
                get_request_argument("number", types=int))

        self.add_route(test)
        response = self.get("/?number=1")
        self.assert_ok(response)
        self.assertEqual(response.json, 1)

    def test_failed_type_conversion(self):
        def test():
            return jsonify(
                get_request_argument("number", types=int))

        self.add_route(test)
        response = self.get("/?number=!")
        self.assert_bad_request(response)
        self.assertIn(
            "Failed to convert the url argument `number",
            response.json["error"])
        self.assertIn(
            "invalid literal for int() with base 10",
            response.json["error"])

    def test_fallback_on_default(self):
        def test():
            return jsonify(
                get_request_argument("number", 2, types=int))

        self.add_route(test)
        response = self.get("/")
        self.assert_ok(response)
        self.assertEqual(response.json, 2)

    def test_no_type_conversion(self):
        def test():
            return jsonify(
                get_request_argument("number"))

        self.add_route(test)
        response = self.get("/?number=1")
        self.assert_ok(response)
        self.assertEqual(response.json, u"1")

    def test_multiple_type_functions(self):
        def test():
            return jsonify(
                get_request_argument("number", types=(int, str)))

        self.add_route(test)
        response = self.get("/?number=!")
        self.assert_ok(response)
        self.assertEqual(response.json, u"!")

    def test_multiple_failures(self):
        def test():
            return jsonify(
                get_request_argument("number", types=(int, hex)))

        self.add_route(test)
        response = self.get("/?number=!")
        self.assert_bad_request(response)

        self.assertIn(
            "Failed to convert the url argument `number",
            response.json["error"])
        self.assertIn(
            "invalid literal for int() with base 10",
            response.json["error"])
