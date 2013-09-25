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
from sqlalchemy.exc import DatabaseError
from utcore import ModelTestCase, unittest
from pyfarm.core.enums import AgentState
from pyfarm.core.config import cfg
from pyfarm.master.application import db
from pyfarm.models.agent import AgentModel, AgentSoftwareModel, AgentTagsModel


try:
    from itertools import product
except ImportError:
    from pyfarm.core.backports import product


class AgentTestCase(unittest.TestCase):
    hostnamebase = "foobar"
    ports = (cfg.get("agent.min_port"), cfg.get("agent.max_port"))
    cpus = (cfg.get("agent.min_cpus"), cfg.get("agent.max_cpus"))
    ram = (cfg.get("agent.min_ram"), cfg.get("agent.max_ram"))
    states = (AgentState.ONLINE, AgentState.OFFLINE)
    ram_allocation = (0, .5, 1)
    cpu_allocation = (0, .5, 1)

    # General list of addresses we should test
    # against.  This covered the start and end
    # points for all private network ranges.
    addresses = (
        ("10.0.0.0", "255.0.0.0"),
        ("172.16.0.0", "255.240.0.0"),
        ("192.168.0.0", "255.255.255.0"),
        ("10.255.255.255", "255.0.0.0"),
        ("172.31.255.255", "255.240.0.0"),
        ("192.168.255.255", "255.255.255.0"))

    def modelArguments(self, limit=None):
        generator = product(
            self.addresses, self.ports, self.cpus, self.ram, self.states,
            self.ram_allocation, self.cpu_allocation)

        count = 0
        for (address, port, cpus, ram, state,
             ram_allocation, cpu_allocation) in generator:
            if limit is not None and count > limit:
                break

            ip, subnet = address
            yield (
                "%s%02d" % (self.hostnamebase, count), ip, subnet, port,
                cpus, ram, state, ram_allocation, cpu_allocation)
            count += 1

    def models(self, limit=None):
        """
        Iterates over the class level variables and produces an agent
        model.  This is done so that we test endpoints in the extreme ranges.
        """
        generator = self.modelArguments(limit=limit)
        for (hostname, ip, subnet, port, cpus, ram, state,
             ram_allocation, cpu_allocation) in generator:
            agent = AgentModel()
            agent.hostname = hostname
            agent.ip = ip
            agent.subnet = subnet
            agent.port = port
            agent.cpus = cpus
            agent.ram = ram
            agent.state = state
            agent.ram_allocation = ram_allocation
            agent.cpu_allocation = cpu_allocation
            yield agent


class TestAgentSoftware(AgentTestCase, ModelTestCase):
    def test_software(self):
        for agent_foobar in self.models(limit=1):
            # create some software tags
            software_objects = []
            for software_name in ("foo", "bar", "baz"):
                software = AgentSoftwareModel()
                software.agent = agent_foobar
                software.software = software_name
                software_objects.append(software)
                db.session.add(software)

            db.session.commit()
            agent_id = agent_foobar.id
            db.session.remove()

            agent = AgentModel.query.filter_by(id=agent_id).first()
            self.assertEqual(
                set(i.software for i in agent.software),
                set(("foo", "bar", "baz")))

    def test_software_unique(self):
        for agent_foobar in self.models(limit=1):
            softwareA = AgentSoftwareModel()
            softwareA.agent = agent_foobar
            softwareA.software = "foo"
            softwareA.version = "1.0.0"
            softwareB = AgentSoftwareModel()
            softwareB.agent = agent_foobar
            softwareB.software = "foo"
            softwareB.version = "1.0.0"
            db.session.add_all([softwareA, softwareB])

            with self.assertRaises(DatabaseError):
                db.session.commit()
            db.session.rollback()


class TestAgentTags(AgentTestCase, ModelTestCase):
    def test_tags_validation(self):
        for agent_foobar in self.models(limit=1):
            tag = AgentTagsModel()
            tag.agent = agent_foobar
            tag.tag = "foo"
            db.session.add(tag)
            db.session.commit()
            self.assertEqual(tag.tag, "foo")

    def test_tags_validation_error(self):
        for agent_foobar in self.models(limit=1):
            tag = AgentTagsModel()
            tag.agent = agent_foobar
            with self.assertRaises(ValueError):
                tag.tag = None

    def test_tags(self):
        for agent_foobar in self.models(limit=1):
            db.session.add(agent_foobar)
            db.session.commit()

            # create some software tags
            tag_objects = []
            for tag_name in ("foo", "bar", "baz"):
                tag = AgentTagsModel()
                tag.agent = agent_foobar
                tag.tag = tag_name
                tag_objects.append(tag)
                db.session.add(tag)

            db.session.commit()
            agent = AgentModel.query.filter_by(id=agent_foobar.id).first()

            # agent.software == software_objects
            self.assertEqual(
                set(i.id for i in agent.tags.all()),
                set(i.id for i in tag_objects))

            # same as above, asking from the software table side
            self.assertEqual(
                set(i.id for i in AgentTagsModel.query.filter_by(
                    agent=agent).all()),
                set(i.id for i in tag_objects))


class TestAgentModel(AgentTestCase, ModelTestCase):
    def test_basic_insert(self):
        agents = list(self.models())
        db.session.add_all(agents)
        db.session.commit()
        agents = dict(
            (AgentModel.query.filter_by(id=agent.id).first(), agent)
            for agent in agents)

        for result, agent, in agents.iteritems():
            self.assertEqual(result.hostname, agent.hostname)
            self.assertEqual(result.ip, agent.ip)
            self.assertEqual(result.subnet, agent.subnet)
            self.assertEqual(result.port, agent.port)
            self.assertEqual(result.cpus, agent.cpus)
            self.assertEqual(result.ram, agent.ram)
            self.assertEqual(result.state, agent.state)
            self.assertEqual(result.cpu_allocation, agent.cpu_allocation)
            self.assertEqual(result.ram_allocation, agent.ram_allocation)

    def test_basic_insert_nonunique(self):
        for (hostname, ip, subnet, port, cpus, ram, state,
             ram_allocation, cpu_allocation) in self.modelArguments(limit=1):
            modelA = AgentModel()
            modelA.hostname = hostname
            modelA.ip = ip
            modelA.subnet = subnet
            modelA.port = port
            modelB = AgentModel()
            modelB.hostname = hostname
            modelB.ip = ip
            modelB.subnet = subnet
            modelB.port = port
            db.session.add(modelA)
            db.session.add(modelB)

            with self.assertRaises(DatabaseError):
                db.session.commit()

            db.session.rollback()


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
                agent.ip = address

    def test_subnet(self):
        fail_subnets = (
            "0.0.0.0",
            "169.254.0.0", "169.254.254.255",  # link local
            "127.0.0.1", "127.255.255.255",  # loopback
            "224.0.0.0", "255.255.255.255",  # multi/broadcast
            "10.56.0.1", "172.16.0.1")

        for agent in self.models(limit=1):
            break

        for subnet in fail_subnets:
            with self.assertRaises(ValueError):
                agent.subnet = subnet

    def test_port_validation(self):
        for model in self.models(limit=1):
            break

        model.port = cfg.get("agent.min_port")
        model.port = cfg.get("agent.max_port")

        with self.assertRaises(ValueError):
            model.port = cfg.get("agent.min_port") - 10

        with self.assertRaises(ValueError):
            model.port = cfg.get("agent.max_port") + 10

    def test_cpu_validation(self):
        for model in self.models(limit=1):
            break

        model.cpus = cfg.get("agent.min_cpus")
        model.cpus = cfg.get("agent.max_cpus")

        with self.assertRaises(ValueError):
            model.cpus = cfg.get("agent.min_cpus") - 10

        with self.assertRaises(ValueError):
            model.cpus = cfg.get("agent.max_cpus") + 10

    def test_ram_validation(self):
        for model in self.models(limit=1):
            break

        model.ram = cfg.get("agent.min_ram")
        model.ram = cfg.get("agent.max_ram")

        with self.assertRaises(ValueError):
            model.ram = cfg.get("agent.min_ram") - 10

        with self.assertRaises(ValueError):
            model.ram = cfg.get("agent.max_ram") + 10
