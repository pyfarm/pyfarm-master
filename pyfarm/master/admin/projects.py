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
Project
=======

Objects and classes for working with the project models.
"""


from pyfarm.master.admin.baseview import SQLModelView
from pyfarm.master.application import SessionMixin
from pyfarm.models.project import Project


class ProjectRolesMixin(object):
    access_roles = ("admin.db.project", )


class ProjectView(SessionMixin, ProjectRolesMixin, SQLModelView):
    model = Project
    column_searchable_list = ("name", )
    column_filters = ("name", )
