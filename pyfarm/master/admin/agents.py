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
from sqlalchemy import not_
from pyfarm.core.enums import AgentState
from pyfarm.models.agent import (
    AgentTagsModel, AgentSoftwareModel, AgentModel)
from pyfarm.master.application import SessionMixin
from pyfarm.master.admin.baseview import SQLModelView
from pyfarm.master.admin.core import (
    EnumList, validate_resource, validate_address, validate_hostname,
    check_dns_mapping, AjaxLoader, BaseFilter)


def repr_agent(model):
    """
    Returns a string which translates the class into a human readable
    form
    """
    if model.ip:
        return "%s (%s)" % (model.hostname, model.ip)
    else:
        return model.hostname


class AgentRolesMixin(object):
    """
    Mixin which declares what role(s) are allowed access to
    :class:`AgentModelView`
    """
    access_roles = ("admin.db.agent", )


class FilterTagsContains(BaseFilter):
    """
    Filter for :class:`AgentModelView` which allows specific tags
    to be included from the view.
    """
    operation_text = "includes"

    def apply(self, query, value):
        if value.strip():
            return query.filter(AgentModel.tags.any(tag=value))
        return query


class FilterTagsNotContains(BaseFilter):
    """
    Filter for :class:`AgentModelView` which allows specific tags
    to be excluded from the view.
    """
    operation_text = "excludes"

    def apply(self, query, value):
        if value.strip():
            return query.filter(not_(AgentModel.tags.any(tag=value)))
        return query


class FilterSoftwareContains(BaseFilter):
    """
    Filter for :class:`AgentModelView` which allows specific software
    to be included in the view.
    """
    operation_text = "includes"

    def apply(self, query, value):
        if value.strip():
            return query.filter(AgentModel.software.any(software=value))
        return query


class FilterSoftwareNotContains(BaseFilter):
    """
    Filter for :class:`AgentModelView` which allows specific software
    to be excluded from the view.
    """
    operation_text = "excludes"

    def apply(self, query, value):
        if value.strip():
            return query.filter(not_(AgentModel.software.any(software=value)))
        return query


class FilterSoftwareContainsVersion(BaseFilter):
    """
    Filter for :class:`AgentModelView` which allows specific software versions
    to be included in the view.
    """
    operation_text = "includes version"

    def apply(self, query, value):
        if value.strip():
            return query.filter(AgentModel.software.any(version=value))
        return query


class FilterSoftwareNotContainsVersion(BaseFilter):
    """
    Filter for :class:`AgentModelView` which allows specific software versions
    to be excluded in the view.
    """
    operation_text = "excludes version"

    def apply(self, query, value):
        if value.strip():
            return query.filter(not_(AgentModel.software.any(version=value)))
        return query


class AgentModelView(SessionMixin, AgentRolesMixin, SQLModelView):
    """
    Administrative view which allows users to view, create, or edit agents.
    """
    model = AgentModel

    # column setup
    column_searchable_list = ("hostname",)
    column_filters = ("hostname", "ram", "freeram", "cpus", "state",
                      FilterTagsContains(AgentModel.tags, "Tag"),
                      FilterTagsNotContains(AgentModel.tags, "Tag"),
                      FilterSoftwareContains(AgentModel.software, "Software"),
                      FilterSoftwareNotContains(AgentModel.software, "Software"),
                      FilterSoftwareContainsVersion(AgentModel.software, "Software"),
                      FilterSoftwareNotContainsVersion(AgentModel.software, "Software"))

    column_choices = {
        "state": [(value, key.title()) for key, value in
                  AgentState._asdict().items()]}

    # columns the form should display
    form_columns = (
        "state", "hostname", "port", "cpus", "ram", "freeram",
        "tags", "software", "ip", "ram_allocation", "cpu_allocation")

    # custom type columns need overrides
    form_overrides = {
        "ip": TextField,
        "state": EnumList}

    # more human readable labels
    column_labels = {
        "ip": "IPv4 Address",
        "ram": "RAM",
        "freeram": "RAM (free)",
        "cpus": "CPUs",
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
        "freeram": {
            "description": AgentModel.freeram.__doc__},
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
        "tags": AjaxLoader("tags", AgentTagsModel,
                           fields=("tag", ), fmt=lambda model: model.tag),
        "software": AjaxLoader("software", AgentSoftwareModel,
                               fields=("software", "version"),
                               fmt=lambda model: "%s (%s)" % (
                                   model.software, model.version))}


class AgentTagsModelView(SessionMixin, AgentRolesMixin, SQLModelView):
    """
    Administrative view which allows users to view, create, or edit agent tags.
    """
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
        "agents": AjaxLoader("agents", AgentModel,
                             fields=("hostname", ), fmt=repr_agent)}


class AgentSoftwareModelView(SessionMixin, AgentRolesMixin, SQLModelView):
    """
    Administrative view which allows users to view, create, or edit agent
    software.
    """
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
        "agents": AjaxLoader("agents", AgentModel,
                             fields=("hostname", ), fmt=repr_agent)}
