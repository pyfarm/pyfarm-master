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
Development Entry Points
========================

These are internal entry points used for development only.

.. warning::
    These entry pints should **never** be deployed or used in production.
"""


def dbdata():
    """creates some fake internal data for use in testing.agent_names"""
    if raw_input(
        "WARNING: THIS WILL REPLACE ALL DATABASE DATA.  DO NOT USE IN "
        "PRODUCTION.  CONTINUE [Y/n]? ") != "Y":
        print "Quit!"
        return
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument("--host-count", "-c", type=int, default=20)
    parsed = parser.parse_args()

    from random import randint
    from pyfarm.master.application import db
    from pyfarm.models.project import Project
    from pyfarm.models.core.cfg import TABLES
    from pyfarm.models.task import Task, TaskDependencies
    from pyfarm.models.job import Job, JobTag, JobDependencies
    from pyfarm.models.jobtype import JobType
    from pyfarm.models.agent import (
        Agent, AgentSoftware, AgentTag,
        AgentSoftwareDependency, AgentSoftwareDependency)
    from pyfarm.models.user import User, Role

    print "recreating tables"
    db.drop_all()
    db.create_all()

    print "creating administrator"
    admin_user = User.create("a", "a")
    admin_user.roles.append(Role.create("admin"))
    db.session.add(admin_user)
    print "   user: a"
    print "   pass: a"
    db.session.commit()

    print "creating agent tags"
    tag_agents_all = AgentTag()
    tag_agents_even = AgentTag()
    tag_agents_odd = AgentTag()
    tag_agents_all.tag = "all"
    tag_agents_even.tag = "even"
    tag_agents_odd.tag = "odd"

    print "creating agent software"
    software_any = AgentSoftware()
    software_any.software = "any"
    software_any.version = "any"
    software_any1 = AgentSoftware()
    software_any1.software = "any"
    software_any1.version = "1.0.0"
    software_ping = AgentSoftware()
    software_ping.software = "ping"
    software_ping.version = "1.0.0"

    print "creating agents"
    first_two = AgentTag()
    first_two.tag = "two"
    first_four = AgentTag()
    first_four.tag = "four"
    first_eight = AgentTag()
    first_eight.tag = "eight"

    for i in xrange(1, parsed.host_count):
        agent_name = "agent%s" % i
        print "   %s:" % agent_name
        agent = Agent()
        agent.hostname = agent_name
        agent.ip = ".".join(map(
            str, (10, randint(0, 255), randint(0, 255), randint(0, 255))))
        agent.remote_ip = agent.ip
        agent.ram = randint(2048, 4096)
        agent.free_ram = randint(0, 4096)
        agent.cpus = randint(2, 24)
        agent.port = randint(1024, 65535)
        agent.tags.append(tag_agents_all)
        agent.software.append(software_any)

        if i <= 2:
            agent.tags.append(first_two)

        if i <= 4:
            agent.tags.append(first_four)

        if i <= 8:
            agent.tags.append(first_eight)

        if i % 2:
            agent.tags.append(tag_agents_odd)
            agent.software.append(software_ping)
        else:
            agent.tags.append(tag_agents_even)
            agent.software.append(software_any1)

        print "        ip: %s" % agent.ip
        print "      cpus: %s" % agent.cpus
        print "       ram: %s" % agent.ram
        print "      port: %s" % agent.port
        print "      tags: %s" % list(tag.tag for tag in agent.tags)
        print "  software: %s" % list(tag.software for tag in agent.software)
        db.session.add(agent)
    db.session.commit()