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
import uuid
from textwrap import dedent
from datetime import datetime

from sqlalchemy import or_
from sqlalchemy.schema import UniqueConstraint
from sqlalchemy.orm import validates
from netaddr import AddrFormatError, IPAddress

from pyfarm.core.enums import (
    AgentState, STRING_TYPES, UseAgentAddress, INTEGER_TYPES, WorkState)
from pyfarm.core.config import read_env_number, read_env_int, read_env
from pyfarm.master.application import db, app
from pyfarm.models.core.functions import repr_ip
from pyfarm.models.core.mixins import (
    ValidatePriorityMixin, UtilityMixins, ReprMixin, ValidateWorkStateMixin)
from pyfarm.models.core.types import (
    id_column, IPv4Address, IDTypeAgent, UseAgentAddressEnum,
    OperatingSystemEnum, AgentStateEnum, MACAddress)
from pyfarm.models.core.cfg import (
    TABLE_AGENT, TABLE_SOFTWARE_VERSION, TABLE_TAG, TABLE_AGENT_MAC_ADDRESS,
    TABLE_AGENT_TAG_ASSOC, MAX_HOSTNAME_LENGTH, MAX_CPUNAME_LENGTH,
    TABLE_AGENT_SOFTWARE_VERSION_ASSOC, MAX_OSNAME_LENGTH, TABLE_GPU_IN_AGENT,
    TABLE_GPU)
from pyfarm.models.jobtype import JobTypeVersion
from pyfarm.models.job import Job


__all__ = ("Agent", )

REGEX_HOSTNAME = re.compile("^(?!-)[A-Z\d-]{1,63}(?<!-)"
                            "(\.(?!-)[A-Z\d-]{1,63}(?<!-))*\.?$",
                            re.IGNORECASE)


AgentSoftwareVersionAssociation = db.Table(
    TABLE_AGENT_SOFTWARE_VERSION_ASSOC, db.metadata,
    db.Column("agent_id", IDTypeAgent,
              db.ForeignKey("%s.id" % TABLE_AGENT), primary_key=True),
    db.Column("software_version_id", db.Integer,
              db.ForeignKey("%s.id" % TABLE_SOFTWARE_VERSION), primary_key=True))


AgentTagAssociation = db.Table(
    TABLE_AGENT_TAG_ASSOC, db.metadata,
    db.Column("agent_id", IDTypeAgent,
              db.ForeignKey("%s.id" % TABLE_AGENT), primary_key=True),
    db.Column("tag_id", db.Integer,
              db.ForeignKey("%s.id" % TABLE_TAG), primary_key=True))


GPUInAgent = db.Table(
    TABLE_GPU_IN_AGENT, db.metadata,
    db.Column("agent_id", IDTypeAgent,
              db.ForeignKey("%s.id" % TABLE_AGENT), primary_key=True),
    db.Column("gpu_id", db.Integer,
              db.ForeignKey("%s.id" % TABLE_GPU), primary_key=True))


class AgentTaggingMixin(object):
    """
    Mixin used which provides some common structures to
    :class:`.AgentTag` and :class:`.AgentSoftware`
    """
    @validates("tag", "software")
    def validate_string_column(self, key, value):
        """
        Ensures `value` is a string or something that can be converted
        to a string.
        """
        if isinstance(value, INTEGER_TYPES):
            value = str(value)
        elif not isinstance(value, STRING_TYPES):
            raise ValueError("expected a string for `%s`" % key)

        return value


class AgentMacAddress(db.Model):
    __tablename__ = TABLE_AGENT_MAC_ADDRESS
    __table_args__ = (UniqueConstraint("agent_id", "mac_address"), )

    agent_id = db.Column(IDTypeAgent, db.ForeignKey("%s.id" % TABLE_AGENT),
                         primary_key=True, nullable=False)
    mac_address = db.Column(MACAddress, primary_key=True, nullable=False,
                            autoincrement=False)


class Agent(db.Model, ValidatePriorityMixin, ValidateWorkStateMixin,
            UtilityMixins, ReprMixin):
    """
    Stores information about an agent include its network address,
    state, allocation configuration, etc.

    .. note::
        This table enforces two forms of uniqueness.  The :attr:`id` column
        must be unique and the combination of these columns must also be
        unique to limit the frequency of duplicate data:

            * :attr:`hostname`
            * :attr:`port`
            * :attr:`id`

    """
    __tablename__ = TABLE_AGENT
    __table_args__ = (UniqueConstraint("hostname", "port", "id"), )
    STATE_ENUM = AgentState
    STATE_DEFAULT = "online"
    REPR_COLUMNS = (
        "id", "hostname", "port", "state", "remote_ip",
        "cpus", "ram", "free_ram")
    REPR_CONVERT_COLUMN = {
        "remote_ip": repr_ip}

    MIN_PORT = read_env_int("PYFARM_AGENT_MIN_PORT", 1024)
    MAX_PORT = read_env_int("PYFARM_AGENT_MAX_PORT", 65535)
    MIN_CPUS = read_env_int("PYFARM_AGENT_MIN_CPUS", 1)
    MAX_CPUS = read_env_int("PYFARM_AGENT_MAX_CPUS", 256)
    MIN_RAM = read_env_int("PYFARM_AGENT_MIN_RAM", 16)
    MAX_RAM = read_env_int("PYFARM_AGENT_MAX_RAM", 262144)

    # quick check of the configured data
    assert MIN_PORT >= 1, "$PYFARM_AGENT_MIN_PORT must be > 0"
    assert MAX_PORT >= 1, "$PYFARM_AGENT_MAX_PORT must be > 0"
    assert MAX_PORT >= MIN_PORT, "MIN_PORT must be <= MAX_PORT"
    assert MIN_CPUS >= 1, "$PYFARM_AGENT_MIN_CPUS must be > 0"
    assert MAX_CPUS >= 1, "$PYFARM_AGENT_MAX_CPUS must be > 0"
    assert MAX_CPUS >= MIN_CPUS, "MIN_CPUS must be <= MAX_CPUS"
    assert MIN_RAM >= 1, "$PYFARM_AGENT_MIN_RAM must be > 0"
    assert MAX_RAM >= 1, "$PYFARM_AGENT_MAX_RAM must be > 0"
    assert MAX_RAM >= MIN_RAM, "MIN_RAM must be <= MAX_RAM"

    id = id_column(IDTypeAgent, default=uuid.uuid4, autoincrement=False)

    # basic host attribute information
    hostname = db.Column(db.String(MAX_HOSTNAME_LENGTH), nullable=False,
                         doc=dedent("""
                         The hostname we should use to talk to this host.
                         Preferably this value will be the fully qualified
                         name instead of the base hostname alone."""))
    remote_ip = db.Column(IPv4Address, nullable=True,
                          doc="the remote address which came in with the "
                              "request")
    use_address = db.Column(UseAgentAddressEnum, nullable=False,
                            default=UseAgentAddress.REMOTE,
                            doc="The address we should use when communicating "
                                "with the agent")
    # TODO Make non-nullable later
    os_class = db.Column(OperatingSystemEnum,
                         doc="The type of operating system running on the "
                             "agent; \"linux\", \"windows\", or \"mac\".")
    os_fullname = db.Column(db.String(MAX_OSNAME_LENGTH),
                            doc="The full human-readable name of the agent's "
                                "OS, as returned by platform.platform()")
    ram = db.Column(db.Integer, nullable=False,
                    doc="The amount of ram installed on the agent in megabytes")
    free_ram = db.Column(db.Integer, nullable=False,
                         doc="The amount of ram which was last considered free")
    cpus = db.Column(db.Integer, nullable=False,
                     doc="The number of logical CPU cores installed on the "
                         "agent")
    cpu_name = db.Column(db.String(MAX_CPUNAME_LENGTH),
                         doc="The make and model of CPUs in this agents")
    port = db.Column(db.Integer, nullable=False,
                     doc="The port the agent is currently running on")
    time_offset = db.Column(db.Integer, nullable=False, default=0,
                            doc="The offset in seconds the agent is from "
                                "an official time server")

    version = db.Column(db.String(16), nullable=True,
                        doc="The pyfarm version number this agent is running.")

    upgrade_to = db.Column(db.String(16), nullable=True,
                           doc="The version this agent should upgrade to.")

    restart_requested = db.Column(db.Boolean, default=False, nullable=False,
                                  doc="If True, the agent will be restarted")

    # host state
    state = db.Column(AgentStateEnum, default=AgentState.ONLINE,
                      nullable=False,
                      doc=dedent("""
                      Stores the current state of the host.  This value can be
                      changed either by a master telling the host to do
                      something with a task or from the host via REST api."""))

    last_heard_from = db.Column(db.DateTime,
                                default=datetime.utcnow,
                                doc="Time we last had contact with this agent")

    last_polled = db.Column(db.DateTime,
                            doc="Time we last tried to contact the agent")

    # Max allocation of the two primary resources which `1.0` is 100%
    # allocation.  For `cpu_allocation` 100% allocation typically means
    # one task per cpu.
    ram_allocation = db.Column(db.Float,
                               default=read_env_number(
                                   "PYFARM_AGENT_RAM_ALLOCATION", .8),
                               doc=dedent("""
                               The amount of ram the agent is allowed to
                               allocate towards work.  A value of 1.0 would
                               mean to let the agent use all of the memory
                               installed on the system when assigning work."""))

    cpu_allocation = db.Column(db.Float,
                               default=read_env_number(
                                   "PYFARM_AGENT_CPU_ALLOCATION", 1.0),
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
    tasks = db.relationship("Task", backref="agent", lazy="dynamic",
                            doc=dedent("""
                            Relationship between an :class:`Agent`
                            and any :class:`pyfarm.models.Task`
                            objects"""))
    tags = db.relationship("Tag", secondary=AgentTagAssociation,
                            backref=db.backref("agents", lazy="dynamic"),
                            lazy="dynamic",
                            doc="Tags associated with this agent")
    software_versions = db.relationship("SoftwareVersion",
                                       secondary=AgentSoftwareVersionAssociation,
                                       backref=db.backref("agents",
                                                          lazy="dynamic"),
                                       lazy="dynamic",
                                       doc="software this agent has installed "
                                           "or is configured for")
    mac_addresses = db.relationship("AgentMacAddress", backref="agent",
                                    lazy="dynamic",
                                    doc="The MAC addresses this agent has",
                                    cascade="save-update, merge, delete, "
                                            "delete-orphan")
    gpus = db.relationship("GPU",
                           secondary=GPUInAgent,
                           backref=db.backref("agents", lazy="dynamic"),
                           lazy="dynamic",
                           doc="The graphics cards that are installed in this "
                               "agent")

    def is_offline(self):
        return self.state == AgentState.OFFLINE

    def get_supported_types(self):
        try:
            return self.support_jobtype_versions
        except AttributeError:
            jobtype_versions_query = JobTypeVersion.query.filter(
                JobTypeVersion.jobs.any(
                    or_(Job.state == None, Job.state == WorkState.RUNNING)))

            self.support_jobtype_versions = []
            for jobtype_version in jobtype_versions_query:
                if self.satisfies_jobtype_requirements(jobtype_version):
                    self.support_jobtype_versions.append(jobtype_version.id)

            return self.support_jobtype_versions

    def satisfies_jobtype_requirements(self, jobtype_version):
        requirements_to_satisfy = list(jobtype_version.software_requirements)

        for software_version in self.software_versions:
            for requirement in list(requirements_to_satisfy):
                if (software_version.software == requirement.software and
                    (requirement.min_version == None or
                    requirement.min_version.rank <= software_version.rank) and
                    (requirement.max_version == None or
                    requirement.max_version.rank >= software_version.rank)):
                    requirements_to_satisfy.remove(requirement)

        return len(requirements_to_satisfy) == 0

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
        Ensure the ``value`` provided for ``key`` is within an expected
        range.  This classmethod retrieves the min and max values from
        the :class:`Agent` class directory using:

            >>> min_value = getattr(Agent, "MIN_%s" % key.upper())
            >>> max_value = getattr(Agent, "MAX_%s" % key.upper())
        """
        min_value = getattr(cls, "MIN_%s" % key.upper())
        max_value = getattr(cls, "MAX_%s" % key.upper())

        # check the provided input
        if not min_value <= value <= max_value:
            msg = "value for `%s` must be between " % key
            msg += "%s and %s" % (min_value, max_value)
            raise ValueError(msg)

        return value

    @classmethod
    def validate_ipv4_address(cls, _, value):
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
        if value is None:
            return value

        try:
            address = IPAddress(value)

        except (AddrFormatError, ValueError) as e:
            raise ValueError(
                "%s is not a valid address format: %s" % (value, e))

        if app.config.get("ALLOW_AGENT_LOOPBACK_ADDRESSES"):
            loopback = lambda: False
        else:
            loopback = address.is_loopback

        if any([address.is_hostmask(), address.is_link_local(),
                loopback(), address.is_multicast(),
                address.is_netmask(), address.is_reserved()]):
            raise ValueError("%s is not a valid address type" % value)

        return value

    def api_url(self,
            scheme=read_env("PYFARM_AGENT_API_SCHEME", "http"),
            version=read_env_int("PYFARM_AGENT_API_VERSION", 1)):
        """
        Returns the base url which should be used to access the api
        of this specific agent.

        :except ValueError:
            Raised if this function is called while the agent's
            :attr:`use_address` column is set to ``PASSIVE``
        """
        assert scheme in ("http", "https")
        assert isinstance(version, int)

        if self.use_address == UseAgentAddress.REMOTE:
            return "%s://%s:%d/api/v%d" % (
                scheme, self.remote_ip, self.port, version)

        elif self.use_address == UseAgentAddress.HOSTNAME:
            return "%s://%s:%d/api/v%d" % (
                scheme, self.hostname, self.port, version)

        else:
            raise ValueError(
                "Cannot construct an agent API url using mode %r "
                "`use_address`" % self.use_address)

    @validates("hostname")
    def validate_hostname_column(self, key, value):
        """Validates the hostname column"""
        return self.validate_hostname(key, value)

    @validates("ram", "cpus", "port")
    def validate_numeric_column(self, key, value):
        """
        Validates several numerical columns.  Columns such as ram, cpus
        and port a are validated with this method.
        """
        return self.validate_resource(key, value)

    @validates("remote_ip")
    def validate_remote_ip(self, key, value):
        """Validates the remote_ip column"""
        return self.validate_ipv4_address(key, value)
