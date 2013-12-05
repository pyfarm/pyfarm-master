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
Projects
========

Top level table used as a grouping mechanism for many components of PyFarm
 including jobs, tasks, agents, users, and more.
"""

from pyfarm.master.application import db
from pyfarm.models.core.types import id_column
from pyfarm.models.core.cfg import TABLE_PROJECT, MAX_PROJECT_NAME_LENGTH
from pyfarm.models.core.mixins import ReprMixin


class Project(db.Model, ReprMixin):
    """
    Stores the top level projects which jobs, tasks, users, roles, etc
    can attach to.
    """
    __tablename__ = TABLE_PROJECT
    REPR_COLUMNS = ("id", "name")

    id = id_column()
    name = db.Column(
        db.String(MAX_PROJECT_NAME_LENGTH), doc="the name of the project")

    @classmethod
    def get(cls, name, create=True):
        """
        Returns a :class:`.Project` object matching ``name``.

        :param str name:
            the name of the project to look for

        :param bool create:
            if True and a project by ``name`` does not exist, create it
            before returning
        """
        assert isinstance(name, basestring), "expected string for `name`"
        project = cls.query.filter_by(name=name).first()

        # create the project if necessary
        if project is None and create:
            commit = db.session.dirty
            project = cls(name=name)
            db.session.add(project)

            # only commit if there are not any
            # other pending operations
            if commit:
                db.session.commit()

        return project

