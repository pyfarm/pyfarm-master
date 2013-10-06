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
from flask import flash
from wtforms import TextField
from wtforms.validators import ValidationError
from flask.ext.admin.contrib.sqla.ajax import QueryAjaxModelLoader
from pyfarm.core.enums import AgentState
from pyfarm.models.agent import AgentTagsModel, AgentSoftwareModel, AgentModel
from pyfarm.master.admin.base import BaseModelView
from pyfarm.master.admin.forms.fields import EnumList
from pyfarm.master.application import SessionMixin, db


class AgentRolesMixin(object):
    access_roles = ("admin.db.agent", )


class AgentTagsModelDisp(AgentTagsModel):
    def __repr__(self):
        return self.tag


class AgentSoftwareDisp(AgentSoftwareModel):
    def __repr__(self):
        return "%s (%s)" % (self.software, self.version)


def validate_model_field(form, field, function=None):
    try:
        return function(field.name, field.data)
    except ValueError, e:
        flash(e)
        raise ValidationError(e)

# resource validation wrappers
validate_address = partial(
    validate_model_field, function=AgentModel.validate_address)
validate_hostname = partial(
    validate_model_field, function=AgentModel.validate_hostname)
validate_resource = partial(
    validate_model_field, function=AgentModel.validate_resource)


class AgentModelView(SessionMixin, AgentRolesMixin, BaseModelView):
    model = AgentModel

    # search setup
    column_searchable_list = ("hostname",)
    column_filters = ("hostname", "ram", "cpus", "state")

    # columns the form should display
    form_columns = (
        "state", "hostname", "port", "cpus", "ram",
        "tags", "software", "ip", "subnet", "ram_allocation", "cpu_allocation")

    # custom type columns need overrides
    form_overrides = {
        "ip": TextField,
        "subnet": TextField,
        "state": EnumList}

    # more human readable labels
    column_labels = {
        "ip": "IPv4 Address",
        "subnet": "IPv4 Subnet",
        "ram_allocation": "RAM Allocation",
        "cpu_allocation": "CPU Allocation"}

    # arguments to pass into the fields
    form_args = {
        "state": {
            "enum": AgentState,
            "description": "Stores the current state of the host.  This value "
                           "can be changed either by a master telling the host "
                           "to do something with a task or from the host via "
                           "REST api.",
            "default": AgentState.ONLINE,
            "values": (AgentState.ONLINE, AgentState.DISABLED,
                       AgentState.OFFLINE)},
        "hostname": {
            "validators": [validate_hostname],
            "description": AgentModel.hostname.__doc__},
        "port": {
            "validators": [validate_resource],
            "description": AgentModel.port.__doc__},
        "cpus": {
            "validators": [validate_resource],
            "description": AgentModel.cpus.__doc__},
        "ram": {
            "validators": [validate_resource],
            "description": AgentModel.ram.__doc__},
        "ip": {
            "validators": [validate_address],
            "description": AgentModel.ip.__doc__},
        "subnet": {
            "validators": [validate_address],
            "description": AgentModel.subnet.__doc__},
        "tags": {
            "description": AgentModel.tags.__doc__},
        "software": {
            "description": AgentModel.software.__doc__},
        "ram_allocation": {
            "description": AgentModel.ram_allocation.__doc__},
        "cpu_allocation": {
            "description": AgentModel.cpu_allocation.__doc__}}

    # create ajax loaders for the relationships
    form_ajax_refs = {
        "tags": QueryAjaxModelLoader("tags", db.session,
                                     AgentTagsModelDisp,
                                     fields=("tag", )),
        "software": QueryAjaxModelLoader("software", db.session,
                                         AgentSoftwareDisp,
                                         fields=("software", "version"))}


# TODO: update form to use proper setup (see above)
class AgentTagsModelView(SessionMixin, AgentRolesMixin, BaseModelView):
    model = AgentTagsModel


# TODO: update form to use proper setup (see above)
class AgentSoftwareModelView(SessionMixin, AgentRolesMixin, BaseModelView):
    model = AgentSoftwareModel