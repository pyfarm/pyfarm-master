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

try:
    from httplib import OK, BAD_REQUEST
except ImportError:
    from http.client import OK, BAD_REQUEST

from flask import g
from werkzeug.datastructures import ImmutableDict

# test class must be loaded first
from pyfarm.master.testutil import BaseTestCase
BaseTestCase.build_environment()

from pyfarm.core.enums import NOTSET
from pyfarm.master.utility import (
    get_column_sets, ReducibleDictionary, TemplateDictionary, json_required,
    jsonify)
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


class TestUtilityDB(BaseTestCase):
    def test_get_column_sets(self):
        all_columns, required_columns = get_column_sets(ColumnSetTest)
        self.assertSetEqual(all_columns, set(["b", "c", "d"]))
        self.assertSetEqual(required_columns, set(["c"]))


class TestUtility(BaseTestCase):
    def setUp(self):
        super(TestUtility, self).setUp()
        g.error = NOTSET
        g.json = NOTSET

    def test_reducible_dictionary(self):
        source = {"a": None}
        data = ReducibleDictionary(source)
        self.assertTrue(issubclass(ReducibleDictionary, dict))
        self.assertDictEqual(data, source)
        data.reduce()
        self.assertDictEqual(data, {})
        self.assertDictEqual(source, {"a": None})

    def test_template_dictionary(self):
        template = TemplateDictionary()
        self.assertIsInstance(template, ImmutableDict)
        self.assertIsInstance(template(), ReducibleDictionary)
        self.assertIsInstance(template(reducible=False), dict)

    def test_json_required_error(self):
        g.error = 1
        @json_required(NOTSET)
        def foo():
            return
        self.assertEqual(foo(), 1)

    def test_json_required_json_notset(self):
        @json_required(NOTSET)
        def foo():
            return

        with self.assertRaises(RuntimeError):
            self.assertEqual(foo(), 1)

    def test_json_required_no_instance_check(self):
        g.json = {}

        @json_required(NOTSET)
        def foo():
            return

        self.assertIsNone(foo())

    def test_json_required_type_check(self):
        g.json = {}

        @json_required(dict)
        def foo():
            return

        self.assertIsNone(foo())

        @json_required(int)
        def foo():
            return

        response, code = foo()
        self.assertIn("int", response.get_data().decode("utf-8"))
        self.assertIn("expected", response.get_data().decode("utf-8"))
        self.assertEqual(code, BAD_REQUEST)
