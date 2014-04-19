# No shebang line, this module is meant to be imported
#
# Copyright 2014 Oliver Palmer
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

from datetime import datetime

# test class must be loaded first
from pyfarm.master.testutil import BaseTestCase
BaseTestCase.build_environment()

from pyfarm.core.enums import WorkState
from pyfarm.master.application import db
from pyfarm.models.task import Task


class TestTask(BaseTestCase):
    def test_insert(self):
        now = datetime.utcnow()
        task = Task(
            state=WorkState.DONE,
            priority=404,
            time_started=now,
            frame=1,
            last_error="foobar")
        db.session.add(task)
        db.session.commit()
        task_id = task.id
        db.session.remove()
        searched = Task.query.filter_by(id=task_id).first()
        self.assertIsNotNone(searched)
        self.assertEqual(searched.state, WorkState.DONE)
        self.assertEqual(searched.priority, 404)
        self.assertEqual(searched.time_started, now)
        self.assertEqual(searched.attempts, 0)
        self.assertEqual(searched.frame, 1)

    def test_increment_attempts(self):
        task = Task(frame=1)
        db.session.add(task)
        db.session.commit()
        self.assertEqual(task.attempts, 0)
        task.state = WorkState.RUNNING
        task.state = WorkState.DONE
        self.assertEqual(task.attempts, 1)
        task.state = WorkState.RUNNING
        task.state = WorkState.FAILED
        self.assertEqual(task.attempts, 2)
        task.state = WorkState.RUNNING
        task.state = WorkState.FAILED
        task.state = WorkState.RUNNING
        self.assertEqual(task.attempts, 4)
        task.state = WorkState.RUNNING
        task.state = WorkState.RUNNING
        self.assertEqual(task.attempts, 4)

    def test_clear_last_error(self):
        task = Task(frame=1, last_error="foobar")
        db.session.add(task)
        db.session.commit()
        db.session.add(task)
        task.state = WorkState.DONE
        self.assertIsNone(task.last_error)
