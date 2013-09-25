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

from utcore import ModelTestCase
from pyfarm.core.config import cfg
from pyfarm.core.enums import WorkState
from pyfarm.master.application import db
from pyfarm.models.core.cfg import TABLE_PREFIX
from pyfarm.models.core.mixins import StateChangedMixin, WorkValidationMixin

rand_state = lambda: choice(list(WorkState))


class ValidationModel(db.Model, WorkValidationMixin):
    __tablename__ = "%s_validation_mixin_test" % TABLE_PREFIX
    STATE_ENUM = WorkState
    id = db.Column(Integer, primary_key=True, autoincrement=True)
    state = db.Column(Integer)
    attempts = db.Column(Integer)
    priority = db.Column(Integer)


class StateChangedModel(db.Model, StateChangedMixin):
    __tablename__ = "%s_state_change_test" % TABLE_PREFIX
    STATE_ENUM = WorkState
    id = db.Column(Integer, primary_key=True, autoincrement=True)
    state = db.Column(Integer)
    attempts = db.Column(Integer)
    time_started = db.Column(DateTime)
    time_finished = db.Column(DateTime)

event.listen(
    StateChangedModel.state, "set", StateChangedModel.stateChangedEvent)


class TestMixins(ModelTestCase):
    def test_state_validation(self):
        model = ValidationModel()
        with self.assertRaises(ValueError):
            model.state = None
        with self.assertRaises(ValueError):
            model.state = -1
        state = rand_state()
        model.state = state
        self.assertEqual(model.state, state)

    def test_priority_validation(self):
        min_priority = cfg.get("job.min_priority")
        max_priority = cfg.get("job.max_priority")
        model = ValidationModel()
        for value in (min_priority-1, max_priority+1):
            with self.assertRaises(ValueError):
                model.priority = value
        model.priority = min_priority
        self.assertEqual(model.priority, min_priority)
        model.priority = max_priority
        self.assertEqual(model.priority, max_priority)

    def test_attempts_validation(self):
        model = ValidationModel()
        with self.assertRaises(ValueError):
            model.attempts = 0
        model.attempts = 1
        self.assertEqual(model.attempts, 1)

    def test_state_changed_event(self):
        model = StateChangedModel()
        self.assertIsNone(model.time_started)
        self.assertIsNone(model.time_finished)
        self.assertIsNone(model.time_finished)
        self.assertIsNone(model.attempts)
        model.state = model.STATE_ENUM.RUNNING
        self.assertEqual(model.state, model.STATE_ENUM.RUNNING)
        self.assertEqual(model.attempts, 1)
        self.assertLessEqual(model.time_started, datetime.now())
        first_started = model.time_started
        self.assertIsNone(model.time_finished)
        model.state = model.STATE_ENUM.DONE
        self.assertIsNotNone(model.time_finished)
        self.assertLessEqual(model.time_finished, datetime.now())
        first_finished = model.time_finished
        model.state = model.STATE_ENUM.RUNNING
        self.assertEqual(model.state, model.STATE_ENUM.RUNNING)
        self.assertIsNone(model.time_finished)
        self.assertNotEqual(model.time_started, first_started)
        self.assertEqual(model.attempts, 2)
        model.state = model.STATE_ENUM.DONE
        self.assertNotEqual(model.time_finished, first_finished)
        self.assertLessEqual(model.time_finished, datetime.now())