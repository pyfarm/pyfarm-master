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

"""
Basic job model testing, the majority of testing for jobs is tested using
relationships.
"""

from datetime import datetime
from sqlalchemy.exc import DatabaseError
from utcore import ModelTestCase, unittest
from pyfarm.core.enums import WorkState
from pyfarm.core.config import cfg
from pyfarm.models.core.db import db
from pyfarm.models.job import (
    JobTagsModel, JobSoftwareModel, JobModel, getJobId)


class TestTags(ModelTestCase):
    def test_insert(self):
        job = JobModel()
        tag = JobTagsModel()
        tag.job = job
        tag.tag = "foo"
        db.session.add_all([tag, job])
        db.session.commit()
        model_id = tag.id
        job_id = job.id
        db.session.remove()
        result = JobTagsModel.query.filter_by(id=model_id).first()
        self.assertEqual(result.tag, "foo")
        self.assertEqual(result.job.id, job_id)

    def test_null(self):
        with self.assertRaises(DatabaseError):
            model = JobTagsModel()
            db.session.add(model)
            db.session.commit()

        db.session.remove()

        with self.assertRaises(DatabaseError):
            tag = JobTagsModel()
            tag.tag = "foo"
            db.session.add(model)
            db.session.commit()

    def test_unique(self):
        job = JobModel()
        tagA = JobTagsModel()
        tagB = JobTagsModel()
        tagA.job = job
        tagA.tag = "foo"
        tagB.job = job
        tagB.tag = "foo"
        db.session.add_all([job, tagA, tagB])

        with self.assertRaises(DatabaseError):
            db.session.commit()


class TestSoftware(ModelTestCase):
    def test_insert(self):
        job = JobModel()
        software = JobSoftwareModel()
        software.job = job
        software.software = "foo"
        db.session.add_all([job, software])
        db.session.commit()
        job_id = job.id
        software_id = software.id
        db.session.remove()
        software = JobSoftwareModel.query.filter_by(id=software_id).first()
        self.assertEqual(software.job.id, job_id)
        self.assertEqual(software.software, "foo")
        self.assertEqual(software.version, "any")

    def test_null(self):
        with self.assertRaises(DatabaseError):
            model = JobSoftwareModel()
            db.session.add(model)
            db.session.commit()

        db.session.remove()

        with self.assertRaises(DatabaseError):
            tag = JobSoftwareModel()
            tag.software = "foo"
            db.session.add(model)
            db.session.commit()

    def test_unique(self):
        job = JobModel()
        softwareA = JobSoftwareModel()
        softwareB = JobSoftwareModel()
        softwareA.job = job
        softwareA.software = "foo"
        softwareB.job = job
        softwareB.software = "foo"
        db.session.add_all([job, softwareA, softwareB])

        with self.assertRaises(DatabaseError):
            db.session.commit()


class TestJobEventsAndValidation(unittest.TestCase):
    def test_special_cases(self):
        special_keys = filter(
            lambda item: item.startswith("agent.special"), list(cfg))

        for full_name in special_keys:
            column = full_name.split("agent.special_")[-1]
            for special_value in cfg.get(full_name):

                model = JobModel()

                # set it to the special case
                setattr(model, column, special_value)
                self.assertEqual(getattr(model, column), special_value)

                # try something else
                if isinstance(special_value, int):
                    with self.assertRaises(ValueError):
                        setattr(model, column, -1)
                else:
                    self.fail("unhandled type %s" % type(special_value))

    def test_ram(self):
        model = JobModel()
        model.ram = cfg.get("agent.min_ram")
        model.ram = cfg.get("agent.max_ram")
        with self.assertRaises(ValueError):
            model.ram = cfg.get("agent.min_ram") - 10
        with self.assertRaises(ValueError):
            model.ram = cfg.get("agent.max_ram") + 10

    def test_cpus(self):
        model = JobModel()
        model.cpus = cfg.get("agent.min_cpus")
        model.cpus = cfg.get("agent.max_cpus")
        with self.assertRaises(ValueError):
            model.cpus = cfg.get("agent.min_cpus") - 10
        with self.assertRaises(ValueError):
            model.cpus = cfg.get("agent.max_cpus") + 10

    def test_priority(self):
        model = JobModel()
        model.priority = cfg.get("job.min_priority")
        model.priority = cfg.get("job.max_priority")
        with self.assertRaises(ValueError):
            model.priority = cfg.get("job.min_priority") - 10

        with self.assertRaises(ValueError):
            model.priority = cfg.get("job.max_priority") + 10

    def test_state_change_event(self):
        model = JobModel()
        self.assertIsNone(model.time_started)
        self.assertIsNone(model.attempts)
        model.state = WorkState.RUNNING
        self.assertIsInstance(model.time_started, datetime)
        self.assertEqual(model.attempts, 1)


class TestJob(ModelTestCase):
    def test_getid(self):
        self.assertNotEqual(getJobId(), getJobId())
        job_id = getJobId()
        job = JobModel.query.filter_by(id=job_id).first()
        self.assertEqual(job.state, WorkState.ALLOC)
        self.assertTrue(job.hidden)