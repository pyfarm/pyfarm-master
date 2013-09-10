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
from uuid import uuid4
from random import randint, choice
from binascii import b2a_hex
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.types import Integer, BigInteger, CHAR
from sqlalchemy.exc import StatementError
from netaddr.ip import IPAddress

from utcore import ModelTestCase, unittest
from pyfarm.models.core.cfg import TABLE_PREFIX
from pyfarm.models.core.app import db
from pyfarm.models.core.types import (
    IPv4Address as IPv4AddressType,
    JSONDict as JSONDictType,
    JSONList as JSONListType,
    JSONSerializable, IDColumn, GUID,
    IDTypeWork, IDTypeAgent, IDTypeTag)


class JSONDictModel(db.Model):
    __tablename__ = "%s_jsondict_model_test" % TABLE_PREFIX
    id = db.Column(Integer, primary_key=True, autoincrement=True)
    data = db.Column(JSONDictType)


class JSONListModel(db.Model):
    __tablename__ = "%s_jsonlist_model_test" % TABLE_PREFIX
    id = db.Column(Integer, primary_key=True, autoincrement=True)
    data = db.Column(JSONListType)


class IPv4AddressModel(db.Model):
    __tablename__ = "%s_ipaddress_model_test" % TABLE_PREFIX
    id = db.Column(Integer, primary_key=True, autoincrement=True)
    data = db.Column(IPv4AddressType)


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

                model = JSONDictModel()
                model.data = test_data
                self.assertIsInstance(model.data, test_type)
                db.session.add(model)
                db.session.commit()
                insert_id = model.id
                db.session.remove()
                result = JSONDictModel.query.filter_by(id=insert_id).first()
                self.assertIsNot(model, result)
                self.assertIsInstance(model.data, dict)
                self.assertDictEqual(model.data, result.data)

    def test_dict_error(self):
        data = JSONDictModel()
        data.data = []
        db.session.add(data)

        with self.assertRaises(StatementError):
            db.session.commit()

    def test_list(self):
        for test_type in JSONListType.serialize_types:
            for i in xrange(10):
                test_data = test_type(
                    [b2a_hex(urandom(1024)), -1024, 1024, True, None])

                model = JSONListModel()
                model.data = test_data
                self.assertIsInstance(model.data, test_type)
                db.session.add(model)
                db.session.commit()
                insert_id = model.id
                db.session.remove()
                result = JSONListModel.query.filter_by(id=insert_id).first()
                self.assertIsNot(model, result)
                self.assertIsInstance(model.data, list)
                self.assertListEqual(model.data, result.data)

    def test_list_error(self):
        data = JSONListModel()
        data.data = {}
        db.session.add(data)

        with self.assertRaises(StatementError):
            db.session.commit()


class TestIPAddressType(ModelTestCase):
    def test_implementation(self):
        # IP addrs are a spec, we need to be specific
        self.assertIs(IPv4AddressType.impl, BigInteger)
        self.assertEqual(IPv4AddressType.MAX_INT, 4294967295)

        with self.assertRaises(ValueError):
            instance = IPv4AddressType()
            instance.checkInteger(-1)

        with self.assertRaises(ValueError):
            instance = IPv4AddressType()
            instance.checkInteger(IPv4AddressType.MAX_INT + 1)

    def test_insert_int(self):
        ipvalue = int(IPAddress("192.168.1.1"))
        model = IPv4AddressModel()
        model.data = ipvalue
        self.assertEqual(model.data, ipvalue)
        db.session.add(model)
        db.session.commit()
        insert_id = model.id
        db.session.remove()
        result = IPv4AddressModel.query.filter_by(id=insert_id).first()
        self.assertIsInstance(result.data, IPAddress)
        self.assertEqual(int(result.data), ipvalue)

    def test_insert_string(self):
        ipvalue = "192.168.1.1"
        model = IPv4AddressModel()
        model.data = ipvalue
        self.assertEqual(model.data, ipvalue)
        db.session.add(model)
        db.session.commit()
        insert_id = model.id
        db.session.remove()
        result = IPv4AddressModel.query.filter_by(id=insert_id).first()
        self.assertIsInstance(result.data, IPAddress)
        self.assertEqual(str(result.data), ipvalue)

    def test_insert_ipclass(self):
        ipvalue = IPAddress("192.168.1.1")
        model = IPv4AddressModel()
        model.data = ipvalue
        self.assertEqual(model.data, ipvalue)
        db.session.add(model)
        db.session.commit()
        insert_id = model.id
        db.session.remove()
        result = IPv4AddressModel.query.filter_by(id=insert_id).first()
        self.assertIsInstance(result.data, IPAddress)
        self.assertEqual(result.data, ipvalue)

    def test_insert_float(self):
        ipvalue = 3.14
        model = IPv4AddressModel()
        model.data = ipvalue
        self.assertEqual(model.data, ipvalue)
        db.session.add(model)
        with self.assertRaises(StatementError):
            db.session.commit()


class TestIDColumn(ModelTestCase):
    def test_integer(self):
        column = IDColumn(db.Integer)
        self.assertIsInstance(column.type, db.Integer)
        self.assertTrue(column.primary_key)
        self.assertTrue(column.unique)
        self.assertFalse(column.nullable)
        self.assertTrue(column.autoincrement)

    def test_id_types(self):
        self.assertIs(IDTypeWork, GUID)
        self.assertIs(IDTypeAgent, db.Integer)
        self.assertIs(IDTypeTag, db.Integer)


class TestGUIDImpl(unittest.TestCase):
    def _dialect(self, name, driver):
        """
        constructs a fake dialect object that replicates a
        sqlalchemy dialect
        """
        return type("FakeDialect", (object, ), {
                    "name": name,
                    "driver": driver,
                    "type_descriptor": lambda self, value: value})()

    def _short(self, value):
        return str(value).replace("-", "")

    def test_id_column(self):
        column = IDColumn(GUID)
        self.assertIsInstance(column.type, GUID)
        self.assertTrue(column.primary_key)
        self.assertTrue(column.unique)
        self.assertFalse(column.nullable)
        self.assertTrue(column.default.is_callable)
        self.assertTrue(column.autoincrement)

    def test_driver_psycopg2(self):
        guid = GUID()
        dialect = self._dialect("postgresql", "psycopg2")
        impl = guid.load_dialect_impl(dialect)
        self.assertIsInstance(impl, UUID)

    def test_driver_pg8000(self):
        guid = GUID()
        dialect = self._dialect("postgresql", "pg8000")
        impl = guid.load_dialect_impl(dialect)
        self.assertIsInstance(impl, CHAR)

    def test_driver_mysql(self):
        guid = GUID()
        dialect = self._dialect("mysql", None)
        impl = guid.load_dialect_impl(dialect)
        self.assertIsInstance(impl, CHAR)
        self.assertEqual(impl.length, 32)

    def test_bind_param(self):
        guid = GUID()
        self.assertIsNone(guid.process_bind_param(None, None))
        dialect = self._dialect("postgresql", None)
        uid = uuid4()
        short_uid = self._short(uid)
        self.assertEqual(
            guid.process_bind_param(uid, dialect), short_uid)
        dialect = self._dialect(None, None)
        self.assertEqual(
            guid.process_bind_param(uid, dialect), short_uid)
        self.assertEqual(
            guid.process_bind_param(str(uid), dialect), short_uid)
        self.assertEqual(
            guid.process_bind_param(self._short(str(uid)), dialect), short_uid)
