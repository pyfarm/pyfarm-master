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

from uuid import uuid4
from sqlalchemy import Column, Integer, DateTime
from utcore import ModelTestCase
from pyfarm.models.core.types import IDTypeWork
from pyfarm.models.core.functions import (
    modelfor, getuuid, WorkColumns, split_and_extend)


class Foo(object):
    __tablename__ = "test"
    id = uuid4()


class TestFunctionsModule(ModelTestCase):
    def test_modelfor(self):
        class Foo(object):
            __tablename__ = "test"
        self.assertTrue(modelfor(Foo(), Foo.__tablename__))

    def test_getuuid(self):
        self.assertIsNone(getuuid(None, None, None, None))
        uuid = str(uuid4())
        self.assertEqual(getuuid(uuid, None, None, None), uuid)
        uuid = uuid4()
        self.assertEqual(getuuid(uuid, None, None, None), str(uuid))
        self.assertEqual(getuuid(Foo, Foo.__tablename__, "id", None), Foo.id)

    def test_getuuid_error(self):
        with self.assertRaises(ValueError):
            getuuid("foo", None, None, None)

        # test a few values which should never return anything
        for unknown_value in (1, 1.25, lambda: None):
            with self.assertRaises(ValueError):
                getuuid(unknown_value, None, None, None)

        with self.assertRaises(ValueError):
            getuuid(Foo, Foo.__tablename__, "none", None)

    def test_work_columns(self):
        columns = WorkColumns(0, 0)
        self.assertEqual(len(columns), 6)
        self.assertTrue(
            all(map(lambda column: isinstance(column, Column), columns)))

        id, state, priority, time_submitted, time_started, time_finished = \
            columns

        self.assertIsInstance(id.type, IDTypeWork)
        self.assertIsInstance(state.type, Integer)
        self.assertIsInstance(priority.type, Integer)
        self.assertIsInstance(time_submitted.type, DateTime)
        self.assertIsInstance(time_started.type, DateTime)
        self.assertIsInstance(time_finished.type, DateTime)

    def test_split_and_extend(self):
        self.assertSetEqual(
            split_and_extend(["a.b.c.d"]),
            set(["a", "a.b", "a.b.c", "a.b.c.d"]))
        self.assertIsNone(split_and_extend(None))

