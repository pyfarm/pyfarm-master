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

from sqlalchemy.exc import DatabaseError
from utcore import ModelTestCase
from pyfarm.models.core.app import db
from pyfarm.models.job import JobTagsModel, JobSoftwareModel, JobModel


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