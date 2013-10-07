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
Development Scripts
===================

These are internal scripts used for development only.  They should
**never be deployed or used in production**
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
    from pyfarm.models.core.cfg import TABLES
    from pyfarm.models.task import TaskModel, TaskDependencies
    from pyfarm.models.job import JobModel, JobTagsModel, JobDependencies
    from pyfarm.models.jobtype import JobTypeModel
    from pyfarm.models.agent import (
        AgentModel, AgentSoftwareModel, AgentTagsModel,
        AgentSoftwareDependencies, AgentTagDependencies)
    from pyfarm.models.users import User, Role

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
    tag_agents_all = AgentTagsModel()
    tag_agents_even = AgentTagsModel()
    tag_agents_odd = AgentTagsModel()
    tag_agents_all.tag = "all"
    tag_agents_even.tag = "even"
    tag_agents_odd.tag = "odd"

    print "creating agent software"
    software_any = AgentSoftwareModel()
    software_any.software = "any"
    software_any.version = "any"
    software_any1 = AgentSoftwareModel()
    software_any1.software = "any"
    software_any1.version = "1.0.0"
    software_ping = AgentSoftwareModel()
    software_ping.software = "ping"
    software_ping.version = "1.2.3"

    print "creating agents"
    for i in xrange(1, parsed.host_count):
        agent_name = "agent%s" % i
        print "   %s:" % agent_name
        agent = AgentModel()
        agent.hostname = agent_name
        agent.ip = ".".join(map(
            str, (10, randint(0, 255), randint(0, 255), randint(0, 255))))
        agent.ram = randint(128, 4069)
        agent.cpus = randint(2, 24)
        agent.port = randint(1024, 65535)
        agent.tags.append(tag_agents_all)
        agent.software.append(software_any)

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