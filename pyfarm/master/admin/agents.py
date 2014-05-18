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

from wtforms import TextField, SelectField
from sqlalchemy import not_

from pyfarm.core.enums import AgentState, UseAgentAddress
from pyfarm.models.agent import Agent
from pyfarm.models.software import Software
from pyfarm.models.tag import Tag
from pyfarm.master.application import SessionMixin
from pyfarm.master.admin.baseview import SQLModelView
from pyfarm.master.admin.core import (
    validate_resource, validate_hostname, AjaxLoader, BaseFilter)


def repr_agent(model):
    """
    Returns a string which translates the class into a human readable
    form
    """
    return repr(model)


class AgentRolesMixin(object):
    """
    Mixin which declares what role(s) are allowed access to
    :class:`AgentView`
    """
    access_roles = ("admin.db.agent", )


class FilterTagsContains(BaseFilter):
    """
    Filter for :class:`AgentView` which allows specific tags
    to be included from the view.
    """
    operation_text = "includes"

    def apply(self, query, value):
        if value.strip():
            return query.filter(Agent.tags.any(tag=value))
        return query


class FilterTagsNotContains(BaseFilter):
    """
    Filter for :class:`AgentView` which allows specific tags
    to be excluded from the view.
    """
    operation_text = "excludes"

    def apply(self, query, value):
        if value.strip():
            return query.filter(not_(Agent.tags.any(tag=value)))
        return query


class FilterState(BaseFilter):
    operation_text = "equals"

    def apply(self, query, value):
        return query.filter(Agent.state == value)


class AgentView(SessionMixin, AgentRolesMixin, SQLModelView):
    """
    Administrative view which allows users to view, create, or edit agents.
    """
    model = Agent

    # column setup
    column_searchable_list = ("hostname",)
    column_filters = (
        "hostname", "ram", "free_ram", "cpus",
        FilterState(Agent.state, "State", options=[(_, _)for _ in AgentState]),
        FilterTagsContains(Agent.tags, "Tag"),
        FilterTagsNotContains(Agent.tags, "Tag"))

    # all states except 'running' allowed (only the agent can set this)
    column_choices = {
        "state": [
            (_, _) for _ in AgentState if _ != "running"],
        "use_address": [(_, _) for _ in UseAgentAddress]}

    # columns the form should display
    form_columns = (
        "state", "hostname", "port", "cpus", "ram", "free_ram",
        "tags", "software_versions", "ip", "use_address", "ram_allocation",
        "cpu_allocation")

    # custom type columns need overrides
    form_overrides = {
        "ip": TextField,
        "state": SelectField,
        "use_address": SelectField}

    # more human readable labels
    column_labels = {
        "ram": "RAM",
        "free_ram": "RAM (free)",
        "cpus": "CPUs",
        "ram_allocation": "RAM Allocation",
        "cpu_allocation": "CPU Allocation"}

    # arguments to pass into the fields
    form_args = {
        "state": {
            "description": "Stores the current state of the host.  This value "
                           "can be changed either by a master telling the host "
                           "to do something with a task or from the host via "
                           "REST api.",
            "default": "online",
            "choices": column_choices["state"]},
        "hostname": {
            "validators": [validate_hostname],
            "description": Agent.hostname.__doc__},
        "port": {
            "validators": [validate_resource],
            "description": Agent.port.__doc__},
        "cpus": {
            "validators": [validate_resource],
            "description": Agent.cpus.__doc__},
        "ram": {
            "validators": [validate_resource],
            "description": Agent.ram.__doc__},
        "free_ram": {
            "description": Agent.free_ram.__doc__},
        "use_address": {
            "description": Agent.use_address.__doc__,
            "default": "remote",
            "choices": column_choices["use_address"]},
        "tags": {
            "description": Agent.tags.__doc__},
        "software_versions": {
            "description": Agent.software_versions.__doc__},
        "ram_allocation": {
            "description": Agent.ram_allocation.__doc__},
        "cpu_allocation": {
            "description": Agent.cpu_allocation.__doc__}}

    # create ajax loaders for the relationships
    form_ajax_refs = {
        "tags": AjaxLoader("tags", Tag,
                           fields=("tag", ), fmt=lambda model: model.tag)}
