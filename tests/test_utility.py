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

try:
    from json import loads
except ImportError:
    from simplejson import loads

from werkzeug.datastructures import ImmutableDict

from .utcore import ModelTestCase, TestCase
from pyfarm.master.utility import (
    get_column_sets, ReducibleDictionary, TemplateDictionary)
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
