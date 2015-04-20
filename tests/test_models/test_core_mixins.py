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

from random import choice
from datetime import datetime

from sqlalchemy import event
from sqlalchemy.types import Integer, DateTime

# test class must be loaded first
from pyfarm.master.testutil import BaseTestCase
BaseTestCase.build_environment()

from pyfarm.core.enums import _WorkState, WorkState, DBWorkState
from pyfarm.master.application import db
from pyfarm.master.config import config
from pyfarm.models.core.types import IPv4Address, WorkStateEnum
from pyfarm.models.core.mixins import (
    WorkStateChangedMixin, ValidatePriorityMixin, UtilityMixins,
    ValidateWorkStateMixin)


rand_state = lambda: choice(list(WorkState))


class ValidationModel(db.Model, ValidateWorkStateMixin, ValidatePriorityMixin):
    __tablename__ = "%s_validation_mixin_test" % config.get("table_prefix")
    STATE_ENUM = WorkState
    id = db.Column(Integer, primary_key=True, autoincrement=True)
    state = db.Column(WorkStateEnum)
    attempts = db.Column(Integer)
    priority = db.Column(Integer)


class WorkStateChangedModel(db.Model, WorkStateChangedMixin):
    __tablename__ = "%s_state_change_test" % config.get("table_prefix")
    id = db.Column(Integer, primary_key=True, autoincrement=True)
    state = db.Column(WorkStateEnum)
    attempts = db.Column(Integer, nullable=False, default=0)
    time_started = db.Column(DateTime)
    time_finished = db.Column(DateTime)

event.listen(
    WorkStateChangedModel.state, "set", WorkStateChangedModel.state_changed)


MixinModelRelation1 = db.Table(
    "%s_mixin_rel_test1" % config.get("table_prefix"), db.metadata,
    db.Column("mixin_id", db.Integer,
              db.ForeignKey(
                  "%s.id" % "%s_mixin_test" % config.get("table_prefix")),
              primary_key=True))

MixinModelRelation2 = db.Table(
    "%s_mixin_rel_test2" % config.get("table_prefix"), db.metadata,
    db.Column("mixin_id", db.Integer,
              db.ForeignKey(
                  "%s.id" % "%s_mixin_test" % config.get("table_prefix")),
              primary_key=True))

class MixinModel(db.Model, UtilityMixins):
    __tablename__ = "%s_mixin_test" % config.get("table_prefix")
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    a = db.Column(db.Integer)
    b = db.Column(db.String(512))
    c = db.Column(IPv4Address)
    d = db.Column(db.Integer, nullable=False)
    e = db.relationship("MixinModel", secondary=MixinModelRelation1)
    f = db.relationship("MixinModel", secondary=MixinModelRelation2)


class TestMixins(BaseTestCase):
    def test_state_validation(self):
        model = ValidationModel()
        db.session.add(model)
        with self.assertRaises(ValueError):
            model.state = None
        with self.assertRaises(ValueError):
            model.state = -1
        state = rand_state()
        model.state = state
        self.assertEqual(model.state, state)
        db.session.commit()

    def test_priority_validation_min(self):
        model = ValidationModel(priority=ValidatePriorityMixin.MIN_PRIORITY)
        db.session.add(model)
        db.session.commit()

    def test_priority_validation_max(self):
        model = ValidationModel(priority=ValidatePriorityMixin.MAX_PRIORITY)
        db.session.add(model)
        db.session.commit()

    def test_priority_validation_max_plus_one(self):
        with self.assertRaises(ValueError):
            ValidationModel(priority=ValidatePriorityMixin.MAX_PRIORITY + 1)

    def test_priority_validation_min_minus_one(self):
        with self.assertRaises(ValueError):
            ValidationModel(priority=ValidatePriorityMixin.MIN_PRIORITY -1)

    def test_priority_validating_null(self):
        model = ValidationModel()
        model.priority = None
        self.assertIsNone(model.priority)
        db.session.add(model)
        db.session.commit()

    def test_attempts_validation(self):
        model = ValidationModel()
        with self.assertRaises(ValueError):
            model.attempts = -1
        model.attempts = 1
        self.assertEqual(model.attempts, 1)
        db.session.add(model)
        db.session.commit()

    def test_state_changed_event(self):
        for state_enum in (WorkState, _WorkState, DBWorkState):
            model = WorkStateChangedModel()
            db.session.add(model)
            self.assertIsNone(model.time_started)
            self.assertIsNone(model.time_finished)
            self.assertIsNone(model.time_finished)
            model.state = state_enum.RUNNING
            self.assertEqual(model.state, state_enum.RUNNING)
            self.assertLessEqual(model.time_started, datetime.utcnow())
            first_started = model.time_started
            self.assertIsNone(model.time_finished)
            model.state = state_enum.DONE
            self.assertIsNotNone(model.time_finished)
            self.assertLessEqual(model.time_finished, datetime.utcnow())
            first_finished = model.time_finished
            model.state = state_enum.RUNNING
            self.assertEqual(model.state, state_enum.RUNNING)
            self.assertIsNone(model.time_finished)
            self.assertNotEqual(model.time_started, first_started)
            model.state = state_enum.DONE
            self.assertNotEqual(model.time_finished, first_finished)
            self.assertLessEqual(model.time_finished, datetime.utcnow())
            db.session.add(model)
            db.session.commit()

    def test_to_dict(self):
        model = MixinModel(a=1, b="hello", d=0)
        db.session.add(model)
        db.session.commit()
        self.assertEqual(
            {"a": model.a, "b": model.b, "id": model.id, "c": None,
             "e": [], "d": model.d, "f": []},
            model.to_dict())

    def to_dict_no_relationships(self):
        model = MixinModel(a=1, b="hello", d=0)
        db.session.add(model)
        db.session.commit()
        self.assertEqual(
            {"a": model.a, "b": model.b, "id": model.id, "c": None,
             "d": model.d},
            model.to_dict(unpack_relationships=False))

    def to_dict_some_relationships(self):
        model = MixinModel(a=1, b="hello", d=0)
        db.session.add(model)
        db.session.commit()
        self.assertEqual(
            {"a": model.a, "b": model.b, "id": model.id, "c": None,
             "d": model.d, "f": []},
            model.to_dict(unpack_relationships=("f", )))

    def test_to_schema(self):
        model = MixinModel(a=1, b="hello", d=0)
        db.session.add(model)
        db.session.commit()
        self.assertDictEqual(
            {"a": "INTEGER", "b": "VARCHAR(512)",
             "id": "INTEGER", "c": "IPv4Address",
             "d": "INTEGER"},
            model.to_schema())

    def test_types(self):
        types = MixinModel.types()
        self.assertEqual(types.primary_keys, set(["id"]))
        self.assertEqual(types.columns, set(["b", "c", "a", "id", "d"]))
        self.assertEqual(types.required, set(["id", "d"]))
        self.assertEqual(types.relationships, set(["e", "f"]))
