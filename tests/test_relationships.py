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

from utcore import ModelTestCase
from pyfarm.models.core.app import db
from pyfarm.models.job import JobModel


class TestRelationships(ModelTestCase):
    def test_liner(self):
        # test A -> B -> C

        # build relationships
        a = JobModel()
        b = JobModel()
        c = JobModel()
        # c.parents.append(b)
        # b.parents.append(a)
        b.parents.append(a)
        b.children.append(c)
        # b.parents.append(a)
        # a.parents.append(a)
        #
        # insert
        db.session.add_all([a, b, c])
        db.session.commit()
        id_a = a.id
        id_b = b.id
        id_c = c.id
        db.session.remove()
        a = JobModel.query.filter_by(id=id_a).first()
        b = JobModel.query.filter_by(id=id_b).first()
        c = JobModel.query.filter_by(id=id_c).first()
        print b.parents, b.children, b.children[0].parents
