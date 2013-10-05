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
Agent
=====

Objects and classes for working with the agent models.
"""

from pyfarm.master.admin.base import BaseModelView
from pyfarm.master.application import SessionMixin
from pyfarm.models.agent import AgentTagsModel, AgentSoftwareModel, AgentModel


class AgentRolesMixin(object):
    access_roles = ("admin.db.agent", )


class AgentModelView(SessionMixin, AgentRolesMixin, BaseModelView):
    model = AgentModel


class AgentTagsModelView(SessionMixin, AgentRolesMixin, BaseModelView):
    model = AgentTagsModel


class AgentSoftwareModelView(SessionMixin, AgentRolesMixin, BaseModelView):
    model = AgentSoftwareModel