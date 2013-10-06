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

from wtforms import TextField
from flask.ext.admin.contrib.sqla.ajax import QueryAjaxModelLoader
from pyfarm.core.enums import AgentState
from pyfarm.models.agent import AgentTagsModel, AgentSoftwareModel, AgentModel
from pyfarm.master.application import SessionMixin, db
from pyfarm.master.admin.base import BaseModelView
from pyfarm.master.admin.fields import (
    EnumList, validate_resource, validate_address, validate_hostname,
    check_dns_mapping)


class AgentTagsDisplay(AgentTagsModel):
    def __repr__(self):
        return self.tag


class AgentSoftwareDisplay(AgentSoftwareModel):
    def __repr__(self):
        return "%s (%s)" % (self.software, self.version)


class AgentModelDisplay(AgentModel):
    def __repr__(self):
        if self.ip:
            return "%s (%s)" % (self.hostname, self.ip)
        else:
            return self.hostname


class AgentRolesMixin(object):
    access_roles = ("admin.db.agent", )



class AgentModelView(SessionMixin, AgentRolesMixin, BaseModelView):
    model = AgentModel

    # column setup
    column_searchable_list = ("hostname",)
    column_filters = ("hostname", "ram", "cpus", "state")
    column_choices = {
        "state": [(value, key.title()) for key, value in
                  AgentState._asdict().items()]}

    # columns the form should display
    form_columns = (
        "state", "hostname", "port", "cpus", "ram",
        "tags", "software", "ip", "ram_allocation", "cpu_allocation")

    # custom type columns need overrides
    form_overrides = {
        "ip": TextField,
        "state": EnumList}

    # more human readable labels
    column_labels = {
        "ip": "IPv4 Address",
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
            "validators": [validate_address, check_dns_mapping],
            "description": AgentModel.ip.__doc__},
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
                                     AgentTagsDisplay,
                                     fields=("tag", )),
        "software": QueryAjaxModelLoader("software", db.session,
                                         AgentSoftwareDisplay,
                                         fields=("software", "version"))}


class AgentTagsModelView(SessionMixin, AgentRolesMixin, BaseModelView):
    model = AgentTagsModel

    # column setup
    column_searchable_list = ("tag", )
    column_filters = ("tag", )

    # arguments to pass into the fields
    form_args = {
        "tag": {
            "description": AgentTagsModel.tag.__doc__},
        "agents": {
            "description": "Agents(s) which are tagged with this string"}}

    # create ajax loaders for the relationships
    form_ajax_refs = {
        "agents": QueryAjaxModelLoader("agents", db.session,
                                       AgentModelDisplay,
                                       fields=("hostname", ))}


class AgentSoftwareModelView(SessionMixin, AgentRolesMixin, BaseModelView):
    model = AgentSoftwareModel

    # search setup
    column_searchable_list = ("software", "version")
    column_filters = ("software", "version")

    # arguments to pass into the fields
    form_args = {
        "software": {
            "description": AgentSoftwareModel.software.__doc__},
        "version": {
            "description": AgentSoftwareModel.version.__doc__},
        "agents": {
            "description": "Agent(s) which are tagged with this software"}}

    # create ajax loaders for the relationships
    form_ajax_refs = {
        "agents": QueryAjaxModelLoader("agents", db.session,
                                       AgentModelDisplay,
                                       fields=("hostname", ))}