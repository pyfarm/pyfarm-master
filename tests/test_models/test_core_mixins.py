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
from pyfarm.models.core.cfg import TABLE_PREFIX
from pyfarm.models.core.types import IPv4Address, WorkStateEnum
from pyfarm.models.core.mixins import (
    WorkStateChangedMixin, ValidatePriorityMixin, UtilityMixins,
    ValidateWorkStateMixin)


rand_state = lambda: choice(list(WorkState))


class ValidationModel(db.Model, ValidateWorkStateMixin, ValidatePriorityMixin):
    __tablename__ = "%s_validation_mixin_test" % TABLE_PREFIX
    STATE_ENUM = WorkState
    id = db.Column(Integer, primary_key=True, autoincrement=True)
    state = db.Column(WorkStateEnum)
    attempts = db.Column(Integer)
    priority = db.Column(Integer)


class WorkStateChangedModel(db.Model, WorkStateChangedMixin):
    __tablename__ = "%s_state_change_test" % TABLE_PREFIX
    id = db.Column(Integer, primary_key=True, autoincrement=True)
    state = db.Column(WorkStateEnum)
    attempts = db.Column(Integer, default=0)
    time_started = db.Column(DateTime)
    time_finished = db.Column(DateTime)

event.listen(
    WorkStateChangedModel.state, "set", WorkStateChangedModel.stateChangedEvent)


MixinModelRelation = db.Table(
    "%s_mixin_rel_test" % TABLE_PREFIX, db.metadata,
    db.Column("mixin_id", db.Integer,
              db.ForeignKey("%s.id" % "%s_mixin_test" % TABLE_PREFIX),
              primary_key=True))


class MixinModel(db.Model, UtilityMixins):
    __tablename__ = "%s_mixin_test" % TABLE_PREFIX
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    a = db.Column(db.Integer)
    b = db.Column(db.String(512))
    c = db.Column(IPv4Address)
    d = db.Column(db.Integer, nullable=False)
    e = db.relationship("MixinModel", secondary=MixinModelRelation)


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

    def test_priority_validation(self):
        min_priority = ValidatePriorityMixin.MIN_PRIORITY
        max_priority = ValidatePriorityMixin.MAX_PRIORITY
        model = ValidationModel()
        db.session.add(model)
        for value in (min_priority-1, max_priority+1):
            with self.assertRaises(ValueError):
                model.priority = value
        model.priority = min_priority
        self.assertEqual(model.priority, min_priority)
        model.priority = max_priority
        self.assertEqual(model.priority, max_priority)
        db.session.commit()

    def test_attempts_validation(self):
        model = ValidationModel()
        with self.assertRaises(ValueError):
            model.attempts = 0
        model.attempts = 1
        self.assertEqual(model.attempts, 1)
        db.session.commit()

    def test_state_changed_event(self):
        for state_enum in (WorkState, _WorkState, DBWorkState):
            model = WorkStateChangedModel()
            db.session.add(model)
            self.assertIsNone(model.time_started)
            self.assertIsNone(model.time_finished)
            self.assertIsNone(model.time_finished)
            model.state = state_enum.RUNNING
            self.assertEqual(model.attempts, 1)
            self.assertEqual(model.state, state_enum.RUNNING)
            self.assertEqual(model.attempts, 1)
            self.assertLessEqual(model.time_started, datetime.now())
            first_started = model.time_started
            self.assertIsNone(model.time_finished)
            model.state = state_enum.DONE
            self.assertIsNotNone(model.time_finished)
            self.assertLessEqual(model.time_finished, datetime.now())
            first_finished = model.time_finished
            model.state = state_enum.RUNNING
            self.assertEqual(model.state, state_enum.RUNNING)
            self.assertIsNone(model.time_finished)
            self.assertNotEqual(model.time_started, first_started)
            self.assertEqual(model.attempts, 2)
            model.state = state_enum.DONE
            self.assertNotEqual(model.time_finished, first_finished)
            self.assertLessEqual(model.time_finished, datetime.now())
            db.session.commit()

    def test_to_dict(self):
        model = MixinModel(a=1, b="hello", d=0)
        db.session.add(model)
        db.session.commit()
        self.assertDictEqual(
            {"a": model.a, "b": model.b, "id": model.id, "c": None,
             "d": model.d},
            model.to_dict())

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
        self.assertEqual(types.primary_keys, {"id"})
        self.assertEqual(types.columns, {"b", "c", "a", "id", "d"})
        self.assertEqual(types.required, {"id", "d"})
        self.assertEqual(types.relationships, {"e"})
