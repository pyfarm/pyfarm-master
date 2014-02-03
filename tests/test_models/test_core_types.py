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

import uuid
from random import randint, choice

from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.types import BigInteger, CHAR
from sqlalchemy.exc import StatementError

# test class must be loaded first
from pyfarm.master.testutil import BaseTestCase
BaseTestCase.build_environment()

from pyfarm.core.enums import AgentState, DBAgentState
from pyfarm.master.application import db
from pyfarm.models.core.cfg import TABLE_PREFIX
from pyfarm.models.core.types import (
    IPv4Address, UseAgentAddressEnum, JSONDict, JSONList,
    JSONSerializable, id_column, AgentStateEnum,
    IDTypeWork, IDTypeAgent, IDTypeTag, IPAddress, WorkStateEnum)


class TypeModel(db.Model):
    __tablename__ = "%s_test_types" % TABLE_PREFIX
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    ipv4 = db.Column(IPv4Address)
    json_dict = db.Column(JSONDict)
    json_list = db.Column(JSONList)
    agent_addr = db.Column(UseAgentAddressEnum)
    agent_state = db.Column(AgentStateEnum)
    work_state = db.Column(WorkStateEnum)


class TestJsonTypes(BaseTestCase):
    def test_types_notimplemented(self):
        class TestType(JSONSerializable):
            pass

        with self.assertRaises(NotImplementedError):
            TestType()

    def test_dict(self):
        for test_type in JSONDict.serialize_types:
            for i in range(10):
                test_data = test_type({
                    "str": uuid.uuid4().hex,
                    "int": randint(-1024, 1024),
                    "list": [
                        uuid.uuid4().hex, -1024, 1024, True, None],
                    "bool": choice([True, False]), "none": None,
                    "dict": {
                        "str": uuid.uuid4().hex,
                        "true": True, "false": False,
                        "int": randint(-1024, 1024),
                        "list": [
                            uuid.uuid4().hex,
                            -1024, 1024, True, None]}})

                model = TypeModel(json_dict=test_data)
                self.assertIsInstance(model.json_dict, test_type)
                db.session.add(model)
                db.session.commit()
                insert_id = model.id
                db.session.remove()
                result = TypeModel.query.filter_by(id=insert_id).first()
                self.assertIsNot(model, result)
                self.assertIsInstance(model.json_dict, dict)
                self.assertEqual(model.json_dict, result.json_dict)

    def test_dict_error(self):
        model = TypeModel(json_dict=[])
        db.session.add(model)

        with self.assertRaises(StatementError):
            db.session.commit()

    def test_list(self):
        for test_type in JSONList.serialize_types:
            for i in range(10):
                test_data = test_type(
                    [uuid.uuid4().hex, -1024, 1024, True, None])

                model = TypeModel(json_list=test_data)
                self.assertIsInstance(model.json_list, test_type)
                db.session.add(model)
                db.session.commit()
                insert_id = model.id
                db.session.remove()
                result = TypeModel.query.filter_by(id=insert_id).first()
                self.assertIsNot(model, result)
                self.assertIsInstance(model.json_list, list)
                self.assertEqual(model.json_list, result.json_list)

    def test_list_error(self):
        data = TypeModel(json_list={})
        db.session.add(data)

        with self.assertRaises(StatementError):
            db.session.commit()


class TestIPAddressType(BaseTestCase):
    def test_implementation(self):
        # IP addrs are a spec, we need to be specific
        self.assertIs(IPv4Address.impl, BigInteger)
        self.assertEqual(IPv4Address.MAX_INT, 4294967295)

        with self.assertRaises(ValueError):
            instance = IPv4Address()
            instance.checkInteger(-1)

        with self.assertRaises(ValueError):
            instance = IPv4Address()
            instance.checkInteger(IPv4Address.MAX_INT + 1)

    def test_comparison(self):
        self.assertEqual(IPAddress("0.0.0.0"), "0.0.0.0")
        self.assertNotEqual(IPAddress("0.0.0.0"), "0.0.0.1")
        self.assertEqual(IPAddress("0.0.0.0"), int(IPAddress("0.0.0.0")))
        self.assertNotEqual(IPAddress("0.0.0.0"), int(IPAddress("0.0.0.1")))
        self.assertEqual(IPAddress("0.0.0.0"), IPAddress("0.0.0.0"))
        self.assertNotEqual(IPAddress("0.0.0.0"), IPAddress("0.0.0.1"))

    def test_insert_int(self):
        ipvalue = int(IPAddress("192.168.1.1"))
        model = TypeModel(ipv4=ipvalue)
        self.assertEqual(model.ipv4, ipvalue)
        db.session.add(model)
        db.session.commit()
        insert_id = model.id
        db.session.remove()
        result = TypeModel.query.filter_by(id=insert_id).first()
        self.assertIsInstance(result.ipv4, IPAddress)
        self.assertEqual(int(result.ipv4), ipvalue)

    def test_insert_string(self):
        ipvalue = "192.168.1.1"
        model = TypeModel(ipv4=ipvalue)
        self.assertEqual(model.ipv4, ipvalue)
        db.session.add(model)
        db.session.commit()
        insert_id = model.id
        db.session.remove()
        result = TypeModel.query.filter_by(id=insert_id).first()
        self.assertIsInstance(result.ipv4, IPAddress)
        self.assertEqual(str(result.ipv4), ipvalue)

    def test_insert_ipclass(self):
        ipvalue = IPAddress("192.168.1.1")
        model = TypeModel(ipv4=ipvalue)
        self.assertEqual(model.ipv4, ipvalue)
        db.session.add(model)
        db.session.commit()
        insert_id = model.id
        db.session.remove()
        result = TypeModel.query.filter_by(id=insert_id).first()
        self.assertIsInstance(result.ipv4, IPAddress)
        self.assertEqual(result.ipv4, ipvalue)

    def test_insert_float(self):
        ipvalue = 3.14
        model = TypeModel(ipv4=ipvalue)
        self.assertEqual(model.ipv4, ipvalue)
        db.session.add(model)
        with self.assertRaises(StatementError):
            db.session.commit()


class TestIDColumn(BaseTestCase):
    def test_integer(self):
        column = id_column(db.Integer)
        self.assertIsInstance(column.type, db.Integer)
        self.assertTrue(column.primary_key)
        self.assertFalse(column.nullable)
        self.assertTrue(column.autoincrement)

    def test_id_types(self):
        if db.engine.name == "sqlite":
            self.assertIs(IDTypeWork, db.Integer)
        else:
            self.assertIs(IDTypeWork, db.BigInteger)

        self.assertIs(IDTypeAgent, db.Integer)
        self.assertIs(IDTypeTag, db.Integer)


class TestAgentStateEnumTypes(BaseTestCase):
    def test_invalid(self):
        model = TypeModel(agent_state=1e10)
        db.session.add(model)

        with self.assertRaises(StatementError):
            db.session.commit()

        db.session.remove()

        model = TypeModel(agent_state=uuid.uuid4().hex)
        db.session.add(model)

        with self.assertRaises(StatementError):
            db.session.commit()

    def test_integer(self):
        for i in DBAgentState:
            model = TypeModel(agent_state=i)
            self.assertEqual(model.agent_state, i)
            db.session.add(model)
            db.session.commit()
            model_id = model.id
            db.session.remove()
            result = TypeModel.query.filter_by(id=model_id).first()
            self.assertEqual(result.agent_state, i)

    def test_string(self):
        for i in AgentState:
            model = TypeModel(agent_state=i)
            self.assertEqual(model.agent_state, i)
            db.session.add(model)
            db.session.commit()
            model_id = model.id
            db.session.remove()
            result = TypeModel.query.filter_by(id=model_id).first()
            self.assertEqual(result.agent_state, i)
