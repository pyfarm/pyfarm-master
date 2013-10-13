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
Agent Models
============

Models and interface classes related to the agent.
"""

import re
from textwrap import dedent

import netaddr
from sqlalchemy.schema import UniqueConstraint
from sqlalchemy.orm import validates
from netaddr import AddrFormatError
from pyfarm.core.enums import AgentState
from pyfarm.core.config import cfg
from pyfarm.master.application import db
from pyfarm.models.core.mixins import WorkValidationMixin, DictMixin
from pyfarm.models.core.types import (
    IDColumn, IPv4Address, IDTypeAgent, IDTypeTag)
from pyfarm.models.core.cfg import (
    TABLE_AGENT, TABLE_AGENT_TAGS, TABLE_AGENT_SOFTWARE,
    MAX_HOSTNAME_LENGTH, MAX_TAG_LENGTH, TABLE_AGENT_SOFTWARE_DEPENDENCIES,
    TABLE_AGENT_TAGS_DEPENDENCIES)


REGEX_HOSTNAME = re.compile("^(([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]*"
                            "[a-zA-Z0-9])\.)*([A-Za-z0-9]|[A-Za-z0-9]"
                            "[A-Za-z0-9\-]*[A-Za-z0-9])$")

AgentTagDependencies = db.Table(
    TABLE_AGENT_TAGS_DEPENDENCIES, db.metadata,
    db.Column("agent_id", db.Integer,
              db.ForeignKey("%s.id" % TABLE_AGENT), primary_key=True),
    db.Column("tag_id", db.Integer,
              db.ForeignKey("%s.id" % TABLE_AGENT_TAGS), primary_key=True))

AgentSoftwareDependencies = db.Table(
    TABLE_AGENT_SOFTWARE_DEPENDENCIES, db.metadata,
    db.Column("agent_id", db.Integer,
              db.ForeignKey("%s.id" % TABLE_AGENT), primary_key=True),
    db.Column("software_id", db.Integer,
              db.ForeignKey("%s.id" % TABLE_AGENT_SOFTWARE), primary_key=True))


class AgentTaggingMixin(object):
    """
    Mixin used which provides some common structures to
    :class:`.AgentTagsModel` and :class:`.AgentSoftwareModel`
    """
    @validates("tag", "software")
    def validate_string_column(self, key, value):
        """
        Ensures `value` is a string or something that can be converted
        to a string.
        """
        if isinstance(value, (int, long)):
            value = str(value)
        elif not isinstance(value, basestring):
            raise ValueError("expected a string for `%s`" % key)

        return value


class AgentTagsModel(db.Model, AgentTaggingMixin):
    """
    Table model used to store tags for an agent.

    .. note::
        This table enforces two forms of uniqueness.  The :attr:`id` column
        must be unique and the combination of these columns must also be
        unique to limit the frequency of duplicate data:
    """
    __tablename__ = TABLE_AGENT_TAGS
    id = IDColumn(IDTypeTag)
    tag = db.Column(db.String(MAX_TAG_LENGTH),
                    doc=dedent("""
                    A string value to tag an agent with. Generally this value
                    is used for grouping like resources together on the network
                    but could also be used by jobs as a sort of
                    requirement."""))


class AgentSoftwareModel(db.Model, AgentTaggingMixin):
    """
    Stores information about an the software installed on
    an agent.

    .. note::
        This table enforces two forms of uniqueness.  The :attr:`id` column
        must be unique and the combination of these columns must also be
        unique to limit the frequency of duplicate data:

            * :attr:`version`
            * :attr:`software`
    """
    __tablename__ = TABLE_AGENT_SOFTWARE
    __table_args__ = (UniqueConstraint("version", "software"), )
    id = IDColumn(IDTypeTag)
    software = db.Column(db.String(MAX_TAG_LENGTH), nullable=False,
                         doc=dedent("""
                         The name of the software installed.  No normalization
                         is performed prior to being stored in the database"""))
    version = db.Column(db.String(MAX_TAG_LENGTH),
                        default="any", nullable=False,
                        doc=dedent("""
                        The version of the software installed on a host.  This
                        value does not follow any special formatting rules
                        because the format depends on the 3rd party."""))


class AgentModel(db.Model, WorkValidationMixin, DictMixin):
    """
    Stores information about an agent include its network address,
    state, allocation configuration, etc.

    .. note::
        This table enforces two forms of uniqueness.  The :attr:`id` column
        must be unique and the combination of these columns must also be
        unique to limit the frequency of duplicate data:

            * :attr:`hostname`
            * :attr:`ip`
            * :attr:`port`

    """
    __tablename__ = TABLE_AGENT
    __table_args__ = (UniqueConstraint("hostname", "ip", "port"), )
    STATE_ENUM = AgentState
    STATE_DEFAULT = STATE_ENUM.ONLINE
    id = IDColumn(IDTypeAgent)

    # basic host attribute information
    hostname = db.Column(db.String(MAX_HOSTNAME_LENGTH), nullable=False,
                         doc=dedent("""
                         The hostname we should use to talk to this host.
                         Preferably this value will be the fully qualified
                         name instead of the base hostname alone."""))
    ip = db.Column(IPv4Address, nullable=True,
                   doc="The IPv4 network address this host resides on")
    ram = db.Column(db.Integer, nullable=False,
                    doc="The amount of ram installed on the agent in megabytes")
    freeram = db.Column(db.Integer, nullable=False,
                        doc="The amount of ram which was last considered free")
    cpus = db.Column(db.Integer, nullable=False,
                     doc="The number of cpus installed on the agent")
    port = db.Column(db.Integer, nullable=False,
                     doc="The port the agent is currently running on")

    # host state
    state = db.Column(db.Integer, default=STATE_DEFAULT, nullable=False,
                      doc=dedent("""
                      Stores the current state of the host.  This value can be
                      changed either by a master telling the host to do
                      something with a task or from the host via REST api.

                      .. csv-table:: **Values (from enum.yml:AgentState)**
                          :header: Integer, Description
                          :widths: 10, 50

                          16,Offline - host is unreachable
                          17,Online - ready to receive work
                          18,Disabled - same as online but cannot receive work
                          19,Running - currently processing work"""))

    # Max allocation of the two primary resources which `1.0` is 100%
    # allocation.  For `cpu_allocation` 100% allocation typically means
    # one task per cpu.
    ram_allocation = db.Column(db.Float,
                               default=cfg.get("agent.ram_allocation", .8),
                               doc=dedent("""
                               The amount of ram the agent is allowed to
                               allocate towards work.  A value of 1.0 would
                               mean to let the agent use all of the memory
                               installed on the system when assigning work."""))

    cpu_allocation = db.Column(db.Float,
                               default=cfg.get("agent.cpu_allocation", 1.0),
                               doc=dedent("""
                               The total amount of cpu space an agent is
                               allowed to process work in.  A value of 1.0
                               would mean an agent can handle as much work
                               as the system could handle given the
                               requirements of a task.  For example if an agent
                               has 8 cpus, cpu_allocation is .5, and a task
                               requires 4 cpus then only that task will run
                               on the system."""))

    # relationships
    tasks = db.relationship("TaskModel", backref="agent", lazy="dynamic",
                            doc=dedent("""
                            Relationship between an :class:`AgentModel`
                            and any :class:`pyfarm.models.TaskModel`
                            objects"""))
    tags = db.relationship("AgentTagsModel", secondary=AgentTagDependencies,
                            backref=db.backref("agents", lazy="dynamic"),
                            lazy="dynamic",
                            doc="Tag(s) assigned to this agent")
    software = db.relationship("AgentSoftwareModel",
                               secondary=AgentSoftwareDependencies,
                               backref=db.backref("agents", lazy="dynamic"),
                               lazy="dynamic",
                               doc="software this agent has installed or is "
                                   "configured for")

    @classmethod
    def validate_hostname(cls, key, value):
        """
        Ensures that the hostname provided by `value` matches a regular
        expression that expresses what a valid hostname is.
        """
        # ensure hostname does not contain characters we can't use
        if not REGEX_HOSTNAME.match(value):
            raise ValueError("%s is not valid for %s" % (value, key))

        return value

    @classmethod
    def validate_resource(cls, key, value):
        """
        Ensure the `value` provided for `key` is within an expected range as
        specified in `agent.yml`
        """
        min_value = cfg.get("agent.min_%s" % key)
        max_value = cfg.get("agent.max_%s" % key)

        # quick sanity check of the incoming config
        assert isinstance(min_value, int), "db.min_%s must be an integer" % key
        assert isinstance(max_value, int), "db.max_%s must be an integer" % key
        assert min_value >= 1, "db.min_%s must be > 0" % key
        assert max_value >= 1, "db.max_%s must be > 0" % key

        # check the provided input
        if min_value > value or value > max_value:
            msg = "value for `%s` must be between " % key
            msg += "%s and %s" % (min_value, max_value)
            raise ValueError(msg)

        return value

    @classmethod
    def validate_ip_address(cls, key, value):
        """
        Ensures the :attr:`ip` address is valid.  This checks to ensure
        that the value provided is:

            * not a hostmask
            * not link local (:rfc:`3927`)
            * not used for multicast (:rfc:`1112`)
            * not a netmask (:rfc:`4632`)
            * not reserved (:rfc:`6052`)
            * a private address (:rfc:`1918`)
        """
        if not value:
            return

        try:
            ip = netaddr.IPAddress(value)

        except (AddrFormatError, ValueError), e:
            raise ValueError(
                "%s is not a valid address format: %s" % (value, e))

        if not all([
            not ip.is_hostmask(), not ip.is_link_local(),
            not ip.is_loopback(), not ip.is_multicast(),
            not ip.is_netmask(), ip.is_private(),
            not ip.is_reserved()
        ]):
            raise ValueError("%s it not a private ip address" % value)

        return value

    @validates("ip")
    def validate_address_column(self, key, value):
        return self.validate_ip_address(key, value)

    @validates("hostname")
    def validate_hostname_column(self, key, value):
        return self.validate_hostname(key, value)

    @validates("ram", "cpus", "port")
    def validate_resource_column(self, key, value):
        return self.validate_resource(key, value)