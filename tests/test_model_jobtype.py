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

from textwrap import dedent
from utcore import ModelTestCase
from pyfarm.core.enums import JobTypeLoadMode
from pyfarm.models.core.db import db
from pyfarm.models.job import JobModel
from pyfarm.models.jobtype import JobTypeModel


class JobTypeTest(ModelTestCase):
    def test_validate_mode(self):
        jobtype = JobTypeModel()
        with self.assertRaises(ValueError):
            jobtype.mode = -1

    def test_basic_insert(self):
        value_name = "foo"
        value_description = "this is a job type"
        value_classname = "Foobar"
        value_code = unicode(dedent("""
        class %s(JobType):
            pass""" % value_classname))
        value_mode = JobTypeLoadMode.OPEN

        # create job
        job = JobModel()
        db.session.add(job)
        db.session.commit()

        # create jobtype
        jobtype = JobTypeModel()
        jobtype.job = job
        jobtype.name = value_name
        jobtype.description = value_description
        jobtype.classname = value_classname
        jobtype.code = value_code
        jobtype.mode = value_mode
        db.session.add(jobtype)
        db.session.commit()

        # store ids and remove the session
        jobid = job.id
        jobtypeid = jobtype.id
        db.session.remove()

        jobtype = JobTypeModel.query.filter_by(id=jobtypeid).first()
        self.assertEqual(jobtype.name, value_name)
        self.assertEqual(jobtype.description, value_description)
        self.assertEqual(jobtype.classname, value_classname)
        self.assertEqual(jobtype.code, value_code)
        self.assertEqual(jobtype.mode, value_mode)
        self.assertEqual(jobtype.jobid, jobid)
        self.assertEqual(jobtype.job.id, jobid)

    def test_before_insert_syntax(self):
        value_name = "foo"
        value_description = "this is a job type"
        value_classname = "Foobar"
        value_code = unicode(dedent("""
        class %s(JobType):
            a = True
                b = False""" % value_classname))

        # create job
        job = JobModel()
        db.session.add(job)
        db.session.commit()

        # create jobtype
        jobtype = JobTypeModel()
        jobtype.job = job
        jobtype.name = value_name
        jobtype.description = value_description
        jobtype.classname = value_classname
        jobtype.code = value_code
        jobtype.mode = JobTypeLoadMode.DOWNLOAD
        db.session.add(jobtype)

        with self.assertRaises(SyntaxError):
            db.session.commit()

    def test_before_insert_parent_class(self):
        value_name = "foo"
        value_description = "this is a job type"
        value_classname = "Foobar"
        value_code = unicode(dedent("""
        class %s(object):
            pass""" % value_classname))

        # create job
        job = JobModel()
        db.session.add(job)
        db.session.commit()

        # create jobtype
        jobtype = JobTypeModel()
        jobtype.job = job
        jobtype.name = value_name
        jobtype.description = value_description
        jobtype.classname = value_classname
        jobtype.code = value_code
        jobtype.mode = JobTypeLoadMode.DOWNLOAD
        db.session.add(jobtype)

        with self.assertRaises(SyntaxError):
            db.session.commit()
