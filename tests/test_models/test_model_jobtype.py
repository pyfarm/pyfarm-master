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

from binascii import hexlify
from os import urandom
from textwrap import dedent

# test class must be loaded first
from pyfarm.master.testutil import BaseTestCase
BaseTestCase.build_environment()

from pyfarm.master.application import db
from pyfarm.models.jobtype import JobType, JobTypeVersion


class JobTypeTest(BaseTestCase):
    def produce_jobtype(self):
        rnd_text = lambda: hexlify(urandom(4)).decode("utf-8")
        jobtype = JobType(name=rnd_text(), description=rnd_text())
        return jobtype

    def test_basic_insert(self):
        jobtype = self.produce_jobtype()
        db.session.add(jobtype)
        db.session.commit()

        # store id and remove the session
        jobtypeid = jobtype.id
        name = jobtype.name
        desc = jobtype.description

        jobtype = JobType.query.filter_by(id=jobtypeid).first()
        self.assertEqual(jobtype.name, name)
        self.assertEqual(jobtype.description, desc)


class JobTypeVersionTest(BaseTestCase):
    def test_validate_batch(self):
        jobtype_version = JobTypeVersion()
        with self.assertRaises(ValueError):
            jobtype_version.max_batch = 0
