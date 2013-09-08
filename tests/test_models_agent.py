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
from sqlalchemy.exc import IntegrityError
from pg8000.errors import DatabaseError
from utcore import ModelTestCase, db
from pyfarm.core.enums import AgentState
from pyfarm.core.config import cfg
from pyfarm.models.agent import Agent, AgentSoftware, AgentTag

try:
    from itertools import product
except ImportError:
    from pyfarm.core.backports import product


class AgentTestCase(ModelTestCase):
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
        for args in self.modelArguments(limit=limit):
            yield Agent(*args)


class TestAgentSoftware(AgentTestCase):
    def test_software(self):
        for agent_foobar in self.models(limit=1):
            db.session.add(agent_foobar)
            db.session.commit()

            # create some software tags
            software_objects = []
            for software_name in ("foo", "bar", "baz"):
                software = AgentSoftware(agent_foobar, software_name)
                software_objects.append(software)
                db.session.add(software)

            db.session.commit()
            agent_id = agent_foobar.id
            db.session.remove()

            agent = Agent.query.filter_by(id=agent_id).first()
            self.assertEqual(
                set(i.software for i in agent.software),
                set(("foo", "bar", "baz")))

    def test_software_unique(self):
        for agent_foobar in self.models(limit=1):
            db.session.add(agent_foobar)
            db.session.commit()
            software = AgentSoftware(agent_foobar, "foo", version="1.0.0")
            db.session.add(software)
            software = AgentSoftware(agent_foobar, "foo", version="1.0.0")
            db.session.add(software)

            with self.assertRaises((IntegrityError, DatabaseError)):
                db.session.commit()
            db.session.rollback()


class TestAgentTags(AgentTestCase):
    def test_tags_validation(self):
        for agent_foobar in self.models(limit=1):
            db.session.add(agent_foobar)
            db.session.commit()

            tag = AgentTag(agent_foobar, 0)
            db.session.add(tag)
            self.assertEqual(tag.tag, str(0))

    def test_tags_validation_error(self):
        for agent_foobar in self.models(limit=1):
            db.session.add(agent_foobar)
            db.session.commit()

            # create some software tags
            with self.assertRaises(ValueError):
                AgentTag(agent_foobar, None)

    def test_tags(self):
        for agent_foobar in self.models(limit=1):
            db.session.add(agent_foobar)
            db.session.commit()

            # create some software tags
            tag_objects = []
            for tag_name in ("foo", "bar", "baz"):
                tag = AgentTag(agent_foobar, tag_name)
                tag_objects.append(tag)
                db.session.add(tag)

            db.session.commit()
            agent = Agent.query.filter_by(id=agent_foobar.id).first()

            # agent.software == software_objects
            self.assertEqual(
                set(i.id for i in agent.tags.all()),
                set(i.id for i in tag_objects))

            # same as above, asking from the software table side
            self.assertEqual(
                set(i.id for i in AgentTag.query.filter_by(agent=agent).all()),
                set(i.id for i in tag_objects))


class TestAgentModel(AgentTestCase):
    def test_basic_insert(self):
        for (hostname, ip, subnet, port, cpus, ram, state,
             ram_allocation, cpu_allocation) in self.modelArguments():
            model = Agent(hostname, ip, subnet, port, cpus, ram,
                          state=state, ram_allocation=ram_allocation,
                          cpu_allocation=cpu_allocation)
            db.session.add(model)
            self.assertEqual(model.hostname, hostname)
            self.assertEqual(model.ip, ip)
            self.assertEqual(model.subnet, subnet)
            self.assertEqual(model.port, port)
            self.assertEqual(model.cpus, cpus)
            self.assertEqual(model.ram, ram)
            self.assertIsNone(model.id)
            db.session.commit()
            model_id = model.id
            db.session.remove()
            result = Agent.query.filter_by(id=model_id).first()
            self.assertEqual(model.hostname, result.hostname)
            self.assertEqual(model.ip, result.ip)
            self.assertEqual(model.subnet, result.subnet)
            self.assertEqual(model.port, result.port)
            self.assertEqual(model.cpus, result.cpus)
            self.assertEqual(model.ram, result.ram)
            self.assertEqual(result.id, model.id)

    def test_basic_insert_nonunique(self):
        for (hostname, ip, subnet, port, cpus, ram, state,
             ram_allocation, cpu_allocation) in self.modelArguments(limit=1):
            modelA = Agent(hostname, ip, subnet, port, cpus, ram)
            modelB = Agent(hostname, ip, subnet, port, cpus, ram)
            db.session.add(modelA)
            db.session.add(modelB)

            with self.assertRaises((IntegrityError, DatabaseError)):
                db.session.commit()

            db.session.rollback()

    def test_hostname_validation(self):
        for (hostname, ip, subnet, port, cpus, ram, state,
             ram_allocation, cpu_allocation) in self.modelArguments(limit=1):
            with self.assertRaises(ValueError):
                Agent("foo/bar", ip, subnet, port, cpus, ram)

            with self.assertRaises(ValueError):
                Agent("", ip, subnet, port, cpus, ram)

    def test_ip_validation(self):
        fail_addresses = (
            "0.0.0.0",
            "169.254.0.0", "169.254.254.255",  # link local
            "127.0.0.1", "127.255.255.255",  # loopback
            "224.0.0.0", "255.255.255.255",  # multi/broadcast
            "255.0.0.0", "255.255.0.0", "x.x.x.x")

        for (hostname, ip, subnet, port, cpus, ram, state,
             ram_allocation, cpu_allocation) in self.modelArguments(limit=1):
            for address in fail_addresses:
                with self.assertRaises(ValueError):
                    Agent(hostname, address, subnet, port, cpus, ram)

    def test_subnet_validation(self):
        fail_subnets = (
            "0.0.0.0",
            "169.254.0.0", "169.254.254.255",  # link local
            "127.0.0.1", "127.255.255.255",  # loopback
            "224.0.0.0", "255.255.255.255",  # multi/broadcast
            "10.56.0.1", "172.16.0.1")

        for (hostname, ip, subnet, port, cpus, ram, state,
             ram_allocation, cpu_allocation) in self.modelArguments(limit=1):
            for subnet in fail_subnets:
                with self.assertRaises(ValueError):
                    Agent(hostname, ip, subnet, port, cpus, ram)

    def test_resource_validation(self):
        for (hostname, ip, subnet, port, cpus, ram, state,
             ram_allocation, cpu_allocation) in self.modelArguments(limit=1):
            model = Agent(hostname, ip, subnet, port, cpus, ram)
            db.session.add(model)
            db.session.commit()

            # port value test
            if port == cfg.get("agent.min_port"):
                with self.assertRaises(ValueError):
                    Agent(hostname, ip, subnet, port-1, cpus, ram)
            else:
                with self.assertRaises(ValueError):
                    Agent(hostname, ip, subnet, port+1, cpus, ram)

            # cpu value test
            if cpus == cfg.get("agent.min_cpus"):
                with self.assertRaises(ValueError):
                    Agent(hostname, ip, subnet, port, cpus-1, ram)
            else:
                with self.assertRaises(ValueError):
                    Agent(hostname, ip, subnet, port, cpus+1, ram)

            # ram value test
            if ram == cfg.get("agent.min_ram"):
                with self.assertRaises(ValueError):
                    Agent(hostname, ip, subnet, port, cpus, ram-1)
            else:
                with self.assertRaises(ValueError):
                    Agent(hostname, ip, subnet, port, cpus, ram+1)
