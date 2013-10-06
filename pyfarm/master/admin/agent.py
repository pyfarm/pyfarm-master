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

from functools import partial
from wtforms import IntegerField, TextField, FloatField
from wtforms.validators import Required
from flask.ext.wtf import Form
from pyfarm.core.enums import AgentState
from pyfarm.models.agent import AgentTagsModel, AgentSoftwareModel, AgentModel
from pyfarm.master.admin.base import BaseModelView
from pyfarm.master.admin.forms.fields import EnumList
from pyfarm.master.application import SessionMixin


def construct_field(field_type, column, label=None, required=True, **kwargs):
    if required:
        validators = kwargs.setdefault("validators", [])
        validators.append(Required())

    kwargs["description"] = column.__doc__
    if label:
        kwargs["label"] = label

    if column.default:
        kwargs.setdefault("default", column.default.arg)

    return field_type(**kwargs)

#subnet

txt_field = partial(construct_field, TextField)
int_field = partial(construct_field, IntegerField)
float_field = partial(construct_field, FloatField)


class AgentModelForm(Form):
    """
    Constructs the form for adding
    """
    state = EnumList(AgentState,
                     default=AgentState.ONLINE,
                     choices=(AgentState.ONLINE, AgentState.DISABLED,
                              AgentState.OFFLINE),
                     description="Current the state of the agent, see the docs "
                                 "for more information.")

    hostname = txt_field(AgentModel.hostname)
    cpus = int_field(AgentModel.cpus, "CPU Count")
    ram = int_field(AgentModel.ram, "RAM")
    port = int_field(AgentModel.port)
    ram_allocation = float_field(AgentModel.ram_allocation, "RAM Allocation",
                                 required=False)
    cpu_allocation = float_field(AgentModel.cpu_allocation, "CPU Allocation",
                                 required=False)
    ip = txt_field(AgentModel.ip, "IPv4 Address", required=False)
    subnet = txt_field(AgentModel.subnet, "IPv4 Subnet", required=False)



class AgentRolesMixin(object):
    access_roles = ("admin.db.agent", )


# TODO: !!! add display override for STATE field
class AgentModelView(SessionMixin, AgentRolesMixin, BaseModelView):
    model = AgentModel
    form = AgentModelForm
    column_searchable_list = ("hostname", )
    column_filters = ("hostname", "ram", "cpus", "state")


class AgentTagsModelView(SessionMixin, AgentRolesMixin, BaseModelView):
    model = AgentTagsModel


class AgentSoftwareModelView(SessionMixin, AgentRolesMixin, BaseModelView):
    model = AgentSoftwareModel