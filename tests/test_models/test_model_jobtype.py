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
from hashlib import sha1

# test class must be loaded first
from pyfarm.master.testutil import BaseTestCase
BaseTestCase.build_environment()

from pyfarm.master.application import db
from pyfarm.models.jobtype import JobType


class JobTypeTest(BaseTestCase):
    def produce_jobtype(self):
        text = lambda: hexlify(urandom(4)).decode("utf-8")
        jobtype = JobType(name=text(), description=text(), classname=text())
        jobtype.classname = "f%s" % jobtype.classname  # make a valid classname
        code = dedent("""
                class %s(JobType):
                    pass""" % jobtype.classname).strip()
        jobtype.code = code
        return jobtype

    def get_sha1_for_jobtype(self, jobtype):
        try:
            return sha1(jobtype.code).hexdigest()
        except TypeError:
            return sha1(jobtype.code.encode("utf-8")).hexdigest()

    def test_basic_insert(self):
        jobtype = self.produce_jobtype()
        db.session.add(jobtype)
        db.session.commit()

        # store id and remove the session
        jobtypeid = jobtype.id
        name = jobtype.name
        desc = jobtype.description
        classname = jobtype.classname
        code = jobtype.code
        sha1 = jobtype.sha1
        db.session.remove()

        jobtype = JobType.query.filter_by(id=jobtypeid).first()
        self.assertEqual(jobtype.name, name)
        self.assertEqual(jobtype.description, desc)
        self.assertEqual(jobtype.classname, classname)
        self.assertEqual(jobtype.code, code)
        self.assertEqual(jobtype.sha1, sha1)

    def test_validate_batch(self):
        jobtype = self.produce_jobtype()
        with self.assertRaises(ValueError):
            jobtype.max_batch = 0

    def test_sha1_default_correct(self):
        jobtype = self.produce_jobtype()
        self.assertEqual(jobtype.sha1, self.get_sha1_for_jobtype(jobtype))

    def test_sha1_correct_after_code_change(self):
        jobtype = self.produce_jobtype()
        self.assertEqual(jobtype.sha1, self.get_sha1_for_jobtype(jobtype))
        jobtype.code = ""
        self.assertEqual(jobtype.sha1, self.get_sha1_for_jobtype(jobtype))

    def test_sha1_correction_on_insert(self):
        jobtype = self.produce_jobtype()
        self.assertEqual(jobtype.sha1, self.get_sha1_for_jobtype(jobtype))
        jobtype.sha1 = ""
        db.session.add(jobtype)
        db.session.commit()
        self.assertEqual(jobtype.sha1, self.get_sha1_for_jobtype(jobtype))
