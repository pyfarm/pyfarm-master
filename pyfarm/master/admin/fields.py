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

import socket
from functools import partial
from flask import flash
from wtforms.validators import StopValidation
from wtforms.fields import SelectField
from pyfarm.models.agent import AgentModel


class EnumList(SelectField):
    """
    Custom list field which is meant to handle enums objects

    :param enum:
        the enum to read data

    :type values:
    :param values:
        if provided, only these keys will be provided as choices
        in the html list widget
    """
    def __init__(self, *args, **kwargs):
        processed_choices = []
        enum = kwargs.pop("enum")
        values = kwargs.pop("values")

        for key, value in enum._asdict().iteritems():
            if value in values:
                processed_choices.append((value, key.title()))

        super(EnumList, self).__init__(
            choices=processed_choices, coerce=int, **kwargs)


def validate_model_field(form, field, function=None):
    """
    Wraps a call to an underlying function to perform field validation.
    Typically,  this is done using a partial function

    >>> from functools import partial
    >>> from pyfarm.models.agent import AgentModel
    >>> validate_state = partial(validate_model_field,
    ...     function=AgentModel.validate_state)
    """
    try:
        return function(field.name, field.data)
    except ValueError, e:
        raise StopValidation(str(e))

# resource validation wrappers
validate_address = partial(
    validate_model_field, function=AgentModel.validate_ip_address)
validate_hostname = partial(
    validate_model_field, function=AgentModel.validate_hostname)
validate_resource = partial(
    validate_model_field, function=AgentModel.validate_resource)


def check_dns_mapping(form, field):
    """
    When a form is submitted check to see if the ip address provided matches
    the hostname.  If not, flash a warning message.
    """
    hostname = form.hostname.data
    try:
        ipaddress = socket.gethostbyname(hostname)
    except socket.error:
        ipaddress = None

    if ipaddress and ipaddress != field.data:
        args = (hostname, field.data)
        msg = "`%s` resolved to %s which does not match address provided" % args
        flash(msg, category="warning")


def validate_network_fields_provided(form, field):
    """
    When the form is submitted ensure that if either the IP or sub
    """