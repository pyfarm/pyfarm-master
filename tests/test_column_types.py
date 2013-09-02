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

from os import urandom
from random import randint, choice
from binascii import b2a_hex
from sqlalchemy.types import Integer
from sqlalchemy.exc import StatementError

from utcore import ModelTestCase
from pyfarm.models.core.cfg import TABLE_PREFIX
from pyfarm.models.core.app import db
from pyfarm.models.core.types import (
    JSONDict as JSONDictType,
    JSONList as JSONListType,
    JSONSerializable)


class JSONDictModel(db.Model):
    __tablename__ = "%s_jsondict_model_test" % TABLE_PREFIX
    id = db.Column(Integer, primary_key=True, autoincrement=True)
    data = db.Column(JSONDictType)


class JSONListModel(db.Model):
    __tablename__ = "%s_jsonlist_model_test" % TABLE_PREFIX
    id = db.Column(Integer, primary_key=True, autoincrement=True)
    data = db.Column(JSONListType)


class JSONDict(JSONDictModel):
    def __init__(self, data):
        self.data = data


class JSONList(JSONListModel):
    def __init__(self, data):
        self.data = data


class TestJsonTypes(ModelTestCase):
    def test_types_notimplemented(self):
        class TestType(JSONSerializable):
            pass

        with self.assertRaises(NotImplementedError):
            TestType()

    def test_dict(self):
        for test_type in JSONDictType.serialize_types:
            for i in xrange(10):
                test_data = test_type({
                    "str": b2a_hex(urandom(1024)),
                    "int": randint(-1024, 1024),
                    "list": [
                        b2a_hex(urandom(1024)), -1024, 1024, True, None],
                    "bool": choice([True, False]), "none": None,
                    "dict": {
                        "str": b2a_hex(urandom(1024)),
                        "true": True, "false": False,
                        "int": randint(-1024, 1024),
                        "list": [
                            b2a_hex(urandom(1024)), -1024, 1024, True, None]}})

                model = JSONDict(test_data)
                self.assertIsInstance(model.data, test_type)
                db.session.add(model)
                db.session.commit()
                insert_id = model.id
                db.session.remove()
                result = JSONDict.query.filter_by(id=insert_id).first()
                self.assertIsNot(model, result)
                self.assertIsInstance(model.data, dict)
                self.assertDictEqual(model.data, result.data)

    def test_dict_error(self):
        data = JSONDict([])
        db.session.add(data)

        with self.assertRaises(StatementError):
            db.session.commit()

    def test_list(self):
        for test_type in JSONListType.serialize_types:
            for i in xrange(10):
                test_data = test_type(
                    [b2a_hex(urandom(1024)), -1024, 1024, True, None])

                model = JSONList(test_data)
                self.assertIsInstance(model.data, test_type)
                db.session.add(model)
                db.session.commit()
                insert_id = model.id
                db.session.remove()
                result = JSONList.query.filter_by(id=insert_id).first()
                self.assertIsNot(model, result)
                self.assertIsInstance(model.data, list)
                self.assertListEqual(model.data, result.data)

    def test_list_error(self):
        data = JSONList({})
        db.session.add(data)

        with self.assertRaises(StatementError):
            db.session.commit()