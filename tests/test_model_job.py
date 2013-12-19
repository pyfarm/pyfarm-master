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

from textwrap import dedent

from datetime import datetime
from sqlalchemy.exc import DatabaseError

from utcore import ModelTestCase, unittest
from pyfarm.core.enums import WorkState
from pyfarm.master.application import db
from pyfarm.models.agent import Agent
from pyfarm.models.job import JobTag, JobSoftware, Job
from pyfarm.core.enums import JobTypeLoadMode
from pyfarm.models.jobtype import JobType


class TestTags(ModelTestCase):
    def test_insert(self):
        # A job can not be created without a jobtype, create one first
        jobtype = JobType()
        jobtype.name = "foo"
        jobtype.description = "this is a job type"
        jobtype.classname = "Foobar"
        jobtype.code = unicode(dedent("""
        class Foobar(JobType):
            pass"""))
        jobtype.mode = JobTypeLoadMode.OPEN
        db.session.add(jobtype)

        job = Job()
        job.job_type = jobtype
        tag = JobTag()
        tag.job = job
        tag.tag = "foo"
        db.session.add_all([tag, job])
        db.session.commit()
        model_id = tag.id
        job_id = job.id
        db.session.remove()
        result = JobTag.query.filter_by(id=model_id).first()
        self.assertEqual(result.tag, "foo")
        self.assertEqual(result.job.id, job_id)

    def test_null(self):
        with self.assertRaises(DatabaseError):
            model = JobTag()
            db.session.add(model)
            db.session.commit()

        db.session.remove()

        with self.assertRaises(DatabaseError):
            tag = JobTag()
            tag.tag = "foo"
            db.session.add(model)
            db.session.commit()

    def test_unique(self):
        job = Job()
        tagA = JobTag()
        tagB = JobTag()
        tagA.job = job
        tagA.tag = "foo"
        tagB.job = job
        tagB.tag = "foo"
        db.session.add_all([job, tagA, tagB])

        with self.assertRaises(DatabaseError):
            db.session.commit()


class TestSoftware(ModelTestCase):
    def test_insert(self):
        # A job can not be created without a jobtype, create one first
        jobtype = JobType()
        jobtype.name = "foo"
        jobtype.description = "this is a job type"
        jobtype.classname = "Foobar"
        jobtype.code = unicode(dedent("""
        class Foobar(JobType):
            pass"""))
        jobtype.mode = JobTypeLoadMode.OPEN
        db.session.add(jobtype)

        job = Job()
        job.job_type = jobtype
        software = JobSoftware()
        software.job = job
        software.software = "foo"
        db.session.add_all([job, software])
        db.session.commit()
        job_id = job.id
        software_id = software.id
        db.session.remove()
        software = JobSoftware.query.filter_by(id=software_id).first()
        self.assertEqual(software.job.id, job_id)
        self.assertEqual(software.software, "foo")
        self.assertEqual(software.version, "any")

    def test_null(self):
        with self.assertRaises(DatabaseError):
            model = JobSoftware()
            db.session.add(model)
            db.session.commit()

        db.session.remove()

        with self.assertRaises(DatabaseError):
            tag = JobSoftware()
            tag.software = "foo"
            db.session.add(model)
            db.session.commit()

    def test_unique(self):
        job = Job()
        softwareA = JobSoftware()
        softwareB = JobSoftware()
        softwareA.job = job
        softwareA.software = "foo"
        softwareB.job = job
        softwareB.software = "foo"
        db.session.add_all([job, softwareA, softwareB])

        with self.assertRaises(DatabaseError):
            db.session.commit()


class TestJobEventsAndValidation(unittest.TestCase):
    def test_ram(self):
        model = Job()
        model.ram = Agent.MIN_RAM
        model.ram = Agent.MAX_RAM

        with self.assertRaises(ValueError):
            model.ram = Agent.MIN_RAM - 10
        with self.assertRaises(ValueError):
            model.ram = Agent.MAX_RAM + 10

    def test_cpus(self):
        model = Job()
        model.cpus = Agent.MIN_CPUS
        model.cpus = Agent.MAX_CPUS
        with self.assertRaises(ValueError):
            model.cpus = Agent.MIN_CPUS - 10
        with self.assertRaises(ValueError):
            model.cpus = Agent.MAX_CPUS + 10

    def test_priority(self):
        model = Job()
        model.priority = Job.MIN_PRIORITY
        model.priority = Job.MAX_PRIORITY
        with self.assertRaises(ValueError):
            model.priority = Job.MIN_PRIORITY - 10

        with self.assertRaises(ValueError):
            model.priority = Job.MAX_PRIORITY + 10

    def test_state_change_event(self):
        model = Job()
        self.assertIsNone(model.time_started)
        self.assertIsNone(model.attempts)
        model.state = WorkState.RUNNING
        self.assertIsInstance(model.time_started, datetime)
        self.assertEqual(model.attempts, 1)
