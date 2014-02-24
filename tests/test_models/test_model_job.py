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

# test class must be loaded first
from pyfarm.master.testutil import BaseTestCase
BaseTestCase.build_environment()

from pyfarm.core.enums import WorkState
from pyfarm.master.application import db
from pyfarm.models.tag import Tag
from pyfarm.models.software import Software, JobSoftwareRequirement
from pyfarm.models.agent import Agent
from pyfarm.models.job import Job
from pyfarm.models.jobtype import JobType, JobTypeVersion


class TestTags(BaseTestCase):
    def test_insert(self):
        # A job can not be created without a jobtype, create one first
        jobtype = JobType()
        jobtype.name = "foo"
        jobtype.description = "this is a job type"
        jobtype_version = JobTypeVersion()
        jobtype_version.jobtype = jobtype
        jobtype_version.version = 1
        jobtype_version.classname = "Foobar"
        jobtype_version.code = ("""
            class Foobar(JobType):
                pass""").encode("utf-8")
        db.session.add(jobtype_version)

        job = Job()
        job.job_type_version = jobtype_version

        tag = Tag()
        tag.jobs = [job]
        tag.tag = "foo456"
        db.session.add_all([tag, job])
        db.session.commit()
        model_id = tag.id
        job_id = job.id
        db.session.remove()
        result = Tag.query.filter_by(id=model_id).first()
        self.assertEqual(result.tag, "foo456")
        self.assertEqual(result.jobs[0].id, job_id)

    def test_null(self):
        with self.assertRaises(DatabaseError):
            model = Tag()
            db.session.add(model)
            db.session.commit()

        db.session.remove()

        with self.assertRaises(DatabaseError):
            tag = Tag()
            tag.tag = "foo789"
            db.session.add(model)
            db.session.commit()

    def test_unique(self):
        job = Job()
        tagA = Tag()
        tagB = Tag()
        tagA.jobs = [job]
        tagA.tag = "foo0"
        tagB.jobs = [job]
        tagB.tag = "foo1"
        db.session.add_all([job, tagA, tagB])

        with self.assertRaises(DatabaseError):
            db.session.commit()


class TestSoftwareRequirement(BaseTestCase):
    def test_insert(self):
        # A job can not be created without a jobtype, create one first
        jobtype = JobType()
        jobtype.name = "foo"
        jobtype.description = "this is a job type"
        jobtype_version = JobTypeVersion()
        jobtype_version.jobtype = jobtype
        jobtype_version.version = 1
        jobtype_version.classname = "Foobar"
        jobtype_version.code = ("""
            class Foobar(JobType):
                pass""").encode("utf-8")
        db.session.add(jobtype_version)

        job = Job()
        job.job_type_version = jobtype_version

        # Software requirement needs a software first
        software = Software()
        software.software = "foo"
        requirement = JobSoftwareRequirement()
        requirement.job = job
        requirement.software = software
        db.session.add(job)
        db.session.commit()
        job_id = job.id
        requirement_id = requirement.id
        requirement2 = JobSoftwareRequirement.query.\
            filter_by(id=requirement_id).first()
        self.assertEqual(requirement.job.id, job_id)
        self.assertEqual(requirement2.software.software, "foo")
        self.assertEqual(requirement2.min_version, None)
        self.assertEqual(requirement2.max_version, None)

    def test_null(self):
        with self.assertRaises(DatabaseError):
            model = JobSoftwareRequirement()
            db.session.add(model)
            db.session.commit()

        db.session.remove()

        with self.assertRaises(DatabaseError):
            software = Software()
            software.software = "foo"
            requirement = JobSoftwareRequirement()
            requirement.software = software
            db.session.add(requirement)
            db.session.commit()

    def test_unique(self):
        # A job can not be created without a jobtype, create one first
        jobtype = JobType()
        jobtype.name = "foo"
        jobtype.description = "this is a job type"
        jobtype.classname = "Foobar"
        jobtype.code = dedent("""
        class Foobar(JobType):
            pass""").encode("utf-8")
        db.session.add(jobtype)

        job = Job()
        job.job_type = jobtype

        software = Software()
        software.software = "foo"

        requirementA = JobSoftwareRequirement()
        requirementB = JobSoftwareRequirement()
        requirementA.job = job
        requirementA.software = software
        requirementB.job = job
        requirementB.software = software
        db.session.add_all([job, requirementA, requirementB])

        with self.assertRaises(DatabaseError):
            db.session.commit()


class TestJobEventsAndValidation(BaseTestCase):
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
