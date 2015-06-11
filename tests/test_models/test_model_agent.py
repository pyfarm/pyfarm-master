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

from __future__ import with_statement
import uuid

from sqlalchemy.exc import DatabaseError


from pyfarm.master.testutil import BaseTestCase
BaseTestCase.build_environment()

from pyfarm.core.enums import AgentState, UseAgentAddress
from pyfarm.master.application import db
from pyfarm.models.software import Software, SoftwareVersion
from pyfarm.models.tag import Tag
from pyfarm.models.agent import Agent

try:
    from itertools import product
except ImportError:
    from pyfarm.core.backports import product


class AgentTestCase(BaseTestCase):
    hostnamebase = "foobar"
    ports = (Agent.MIN_PORT, Agent.MAX_PORT)
    cpus = (Agent.MIN_CPUS, Agent.MAX_CPUS)
    ram = (Agent.MIN_RAM, Agent.MAX_RAM)
    states = (AgentState.ONLINE, AgentState.OFFLINE)
    ram_allocation = (0, .5, 1)
    cpu_allocation = (0, .5, 1)

    # General list of addresses we should test
    # against.  This covered the start and end
    # points for all private network ranges.
    addresses = (
        "10.0.0.0",
        "172.16.0.0",
        "192.168.0.0",
        "10.255.255.255",
        "172.31.255.255",
        "192.168.255.255")

    def modelArguments(self, limit=None):
        generator = product(
            self.addresses, self.ports, self.cpus, self.ram, self.states,
            self.ram_allocation, self.cpu_allocation)

        count = 0
        for (ip, port, cpus, ram, state,
             ram_allocation, cpu_allocation) in generator:
            if limit is not None and count >= limit:
                break

            yield (
                "%s%02d" % (self.hostnamebase, count), ip, port,
                cpus, ram, state, ram_allocation, cpu_allocation)
            count += 1

    def models(self, limit=None):
        """
        Iterates over the class level variables and produces an agent
        model.  This is done so that we test endpoints in the extreme ranges.
        """
        generator = self.modelArguments(limit=limit)
        for (hostname, ip, port, cpus, ram, state,
             ram_allocation, cpu_allocation) in generator:
            agent = Agent()
            agent.hostname = hostname
            agent.remote_ip = ip
            agent.port = port
            agent.cpus = cpus
            agent.free_ram = agent.ram = ram
            agent.state = state
            agent.ram_allocation = ram_allocation
            agent.cpu_allocation = cpu_allocation
            yield agent


class TestAgentSoftware(AgentTestCase, BaseTestCase):
    def test_software(self):
        for agent_foobar in self.models(limit=1):
            db.session.add(agent_foobar)

            # create some software version tags
            software_version_objects = []
            for software_name in ("foo", "bar", "baz"):
                software = Software()
                software.agents = [agent_foobar]
                software.software = software_name
                software_version = SoftwareVersion()
                software_version.software = software
                software_version.version = "1"
                software_version.rank = 1
                software_version_objects.append((software.software,
                                                 software_version.version))
                agent_foobar.software_versions.append(software_version)

            db.session.commit()
            agent_id = agent_foobar.id
            db.session.remove()

            agent = Agent.query.filter_by(id=agent_id).first()
            self.assertIsNotNone(agent)

            agent_software_versions = list(
                (str(i.software.software), str(i.version))
                for i in agent.software_versions)
            software_version_objects.sort()
            agent_software_versions.sort()
            self.assertListEqual(agent_software_versions,
                                 software_version_objects)

    def test_software_unique(self):
        for agent_foobar in self.models(limit=1):
            softwareA = Software()
            softwareA.agent = [agent_foobar]
            softwareA.software = "foo"
            softwareA.version = "1.0.0"
            softwareB = Software()
            softwareB.agent = [agent_foobar]
            softwareB.software = "foo"
            softwareB.version = "1.0.0"
            db.session.add_all([softwareA, softwareB])

            with self.assertRaises(DatabaseError):
                db.session.commit()
            db.session.rollback()


class TestAgentTags(AgentTestCase, BaseTestCase):
    def test_tags_validation(self):
        for agent_foobar in self.models(limit=1):
            tag = Tag()
            tag.agent = [agent_foobar]
            tag.tag = "foo123"
            db.session.add(tag)
            db.session.commit()
            self.assertEqual(tag.tag, "foo123")

    def test_tags_validation_error(self):
        for agent_foobar in self.models(limit=1):
            tag = Tag()
            tag.agents = [agent_foobar]
            tag.tag = None

        with self.assertRaises(DatabaseError):
            db.session.add(tag)
            db.session.commit()

    def test_tags(self):
        for agent_foobar in self.models(limit=1):
            db.session.add(agent_foobar)

            tags = []
            rand = lambda: uuid.uuid4().hex
            for tag_name in (rand(), rand(), rand()):
                tag = Tag()
                tag.tag = tag_name
                tags.append(tag_name)
                agent_foobar.tags.append(tag)

            db.session.commit()
            agent_id = agent_foobar.id
            db.session.remove()
            agent = Agent.query.filter_by(id=agent_id).first()
            self.assertIsNotNone(agent)
            tags.sort()
            agent_tags = list(str(tag.tag) for tag in agent.tags)
            agent_tags.sort()
            self.assertListEqual(agent_tags, tags)


class TestAgentModel(AgentTestCase, BaseTestCase):
    def test_basic_insert(self):
        agents = list(self.models())
        db.session.add_all(agents)
        try:
            db.session.commit()
        except OverflowError:
            if db.engine.name == "sqlite":
                self.skipTest("Cannot test with sqlite, integer Overflow")

        agents = dict(
            (Agent.query.filter_by(id=agent.id).first(), agent)
            for agent in agents)

        for result, agent, in agents.items():
            self.assertEqual(result.hostname, agent.hostname)
            self.assertEqual(result.port, agent.port)
            self.assertEqual(result.cpus, agent.cpus)
            self.assertEqual(result.ram, agent.ram)
            self.assertEqual(result.state, agent.state)
            self.assertEqual(result.cpu_allocation, agent.cpu_allocation)
            self.assertEqual(result.ram_allocation, agent.ram_allocation)

    def test_basic_insert_nonunique(self):
        for (hostname, ip, port, cpus, ram, state,
             ram_allocation, cpu_allocation) in \
                self.modelArguments(limit=1):
            model_id = uuid.uuid4()
            modelA = Agent()
            modelA.hostname = hostname
            modelA.port = port
            modelA.id = model_id
            modelB = Agent()
            modelB.hostname = hostname
            modelB.port = port
            modelB.id = model_id
            db.session.add(modelA)
            db.session.add(modelB)

            with self.assertRaises(DatabaseError):
                db.session.commit()

            db.session.rollback()

    def test_api_url_remote(self):
        model = Agent(
            hostname="foo", port=12345, remote_ip="10.56.0.1",
            ram=1024, free_ram=128, cpus=4,
            use_address=UseAgentAddress.REMOTE)

        self.assertEqual(
            model.api_url(),
            model.URL_TEMPLATE.format(
                host=model.remote_ip,
                port=model.port
            )
        )

    def test_api_url_hostname(self):
        model = Agent(
            hostname="foo", port=12345, remote_ip="10.56.0.1",
            ram=1024, free_ram=128, cpus=4,
            use_address=UseAgentAddress.HOSTNAME)

        self.assertEqual(
            model.api_url(),
            model.URL_TEMPLATE.format(
                host=model.hostname,
                port=model.port
            )
        )

    def test_api_url_passive(self):
        model = Agent(
            hostname="foo", port=12345, remote_ip="10.56.0.1",
            ram=1024, free_ram=128, cpus=4,
            use_address=UseAgentAddress.PASSIVE)

        # Shouldn't have access to api_url if we're operating under PASSIVE
        with self.assertRaises(ValueError):
            model.api_url()


class TestModelValidation(AgentTestCase):
    def test_hostname(self):
        for model in self.models(limit=1):
            break

        with self.assertRaises(ValueError):
            model.hostname = "foo/bar"

        with self.assertRaises(ValueError):
            model.hostname = ""

    def test_ip(self):
        fail_addresses = (
            "0.0.0.0",
            "169.254.0.0", "169.254.254.255",  # link local
            "127.0.0.1", "127.255.255.255",  # loopback
            "224.0.0.0", "255.255.255.255",  # multi/broadcast
            "255.0.0.0", "255.255.0.0", "x.x.x.x")

        for agent in self.models(limit=1):
            break

        for address in fail_addresses:
            with self.assertRaises(ValueError):
                agent.remote_ip = address

    def test_port_validation(self):
        for model in self.models(limit=1):
            break

        model.port = Agent.MIN_PORT
        model.port = Agent.MAX_PORT

        with self.assertRaises(ValueError):
            model.port = Agent.MIN_PORT - 10

        with self.assertRaises(ValueError):
            model.port = Agent.MAX_PORT + 10

    def test_cpu_validation(self):
        for model in self.models(limit=1):
            break

        model.cpus = Agent.MIN_CPUS
        model.cpus = Agent.MAX_CPUS

        with self.assertRaises(ValueError):
            model.cpus = Agent.MIN_CPUS - 10

        with self.assertRaises(ValueError):
            model.cpus = Agent.MAX_CPUS + 10

    def test_ram_validation(self):
        for model in self.models(limit=1):
            break

        model.ram = Agent.MIN_RAM
        model.ram = Agent.MAX_RAM

        with self.assertRaises(ValueError):
            model.ram = Agent.MIN_RAM - 10

        with self.assertRaises(ValueError):
            model.ram = Agent.MAX_RAM + 10
