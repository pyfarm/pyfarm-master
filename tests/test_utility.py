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

from httplib import OK, BAD_REQUEST

try:
    from json import loads
except ImportError:
    from simplejson import loads

from flask import Response
from werkzeug.datastructures import ImmutableDict
from utcore import ModelTestCase, TestCase
from pyfarm.core.enums import APIError
from pyfarm.master.utility import (
    dumps, get_column_sets, JSONResponse, ReducibleDictionary,
    json_from_request, TemplateDictionary)
from pyfarm.master.application import db
from pyfarm.models.core.cfg import TABLE_PREFIX


class ColumnSetTest(db.Model):
    __tablename__ = "%s_column_set_test" % TABLE_PREFIX
    a = db.Column(db.Integer, primary_key=True)
    b = db.Column(db.Integer, nullable=True)
    c = db.Column(db.Integer, nullable=False)
    d = db.Column(db.Integer, nullable=False, default=0)


class FakeRequest(object):
    def __init__(self, data, raise_error=False):
        self.data = data
        self.raise_error = raise_error

    def get_json(self):
        if self.raise_error:
            raise ValueError("FAILED")
        return self.data


class TestUtilityDB(ModelTestCase):
    def test_get_column_sets(self):
        all_columns, required_columns = get_column_sets(ColumnSetTest)
        self.assertSetEqual(all_columns, set(["b", "c", "d"]))
        self.assertSetEqual(required_columns, set(["c"]))


class TestUtility(TestCase):
    def test_dumps(self):
        data = {"a": 0, "b": 1, "c": 2, "d": 4}
        for indent in (2, 4, None):
            dumped = dumps(data, indent=indent)
            self.assertIsInstance(dumped, str)
            self.assertDictEqual(loads(dumped), data)

    def test_json_response(self):
        data = {"a": 0, "b": 1, "c": 2, "d": 4}
        self.assertTrue(issubclass(JSONResponse, Response))
        response = JSONResponse()
        self.assertEqual(response.content_type, "application/json")
        self.assertEqual(response.status_code, OK)
        response = JSONResponse(status=BAD_REQUEST)
        self.assertEqual(response.status_code, BAD_REQUEST)
        response = JSONResponse(data)
        self.assertDictEqual(loads(response.data), data)
        response = JSONResponse(ReducibleDictionary({"a": None}))
        self.assertDictEqual(loads(response.data), {})

    def test_reducible_dictionary(self):
        source = {"a": None}
        data = ReducibleDictionary(source)
        self.assertTrue(issubclass(ReducibleDictionary, dict))
        self.assertDictEqual(data, source)
        data.reduce()
        self.assertDictEqual(data, {})
        self.assertDictEqual(source, {"a": None})

    def test_json_from_request(self):
        request = FakeRequest({"a": None}, raise_error=True)
        response = json_from_request(request)
        self.assertIsInstance(response, JSONResponse)
        self.assertEqual(response.status_code, BAD_REQUEST)
        error_data = [
            APIError.JSON_DECODE_FAILED[0],
            "failed to decode any json data from the request: FAILED"]
        self.assertEqual(response.status_code, BAD_REQUEST)
        self.assertListEqual(loads(response.data), error_data)
        request = FakeRequest({"a": "a"})
        response = json_from_request(request)
        self.assertIsInstance(response, dict)
        self.assertDictEqual(response, {"a": "a"})
        request = FakeRequest({"a": "a"})
        response = json_from_request(request, required_keys=set(["c"]))
        self.assertIsInstance(response, JSONResponse)
        self.assertEqual(response.status_code, BAD_REQUEST)
        error_data = [
            APIError.MISSING_FIELDS[0],
            "one or more of the expected fields were missing in the request.  Missing fields are: ['c']"]
        self.assertListEqual(loads(response.data), error_data)
        request = FakeRequest({"a": "a"})
        response = json_from_request(request, all_keys=set(["z"]))
        self.assertIsInstance(response, JSONResponse)
        self.assertEqual(response.status_code, BAD_REQUEST)
        error_data = [
            APIError.EXTRA_FIELDS_ERROR[0],
            "an unexpected number of fields or columns were provided.  Extra fields were: ['a']"]
        self.assertListEqual(loads(response.data), error_data)
        request = FakeRequest({"a": "a"})
        response = json_from_request(request, disallowed_keys=set(["a"]))
        self.assertIsInstance(response, JSONResponse)
        self.assertEqual(response.status_code, BAD_REQUEST)
        error_data = [
            APIError.EXTRA_FIELDS_ERROR[0],
            "an unexpected number of fields or columns were provided.  Extra fields were: ['a']"]
        self.assertListEqual(loads(response.data), error_data)

    def test_template_dictionary(self):
        template = TemplateDictionary()
        self.assertIsInstance(template, ImmutableDict)
        self.assertIsInstance(template(), ReducibleDictionary)
        self.assertIsInstance(template(reducible=False), dict)
