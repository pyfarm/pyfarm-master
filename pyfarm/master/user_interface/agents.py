# No shebang line, this module is meant to be imported
#
# Copyright 2014 Ambient Entertainment GmbH & Co. KG
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

try:
    from httplib import BAD_REQUEST, NOT_FOUND, SEE_OTHER
except ImportError:  # pragma: no cover
    from http.client import BAD_REQUEST, NOT_FOUND, SEE_OTHER

from flask import render_template, request, url_for, redirect, flash
from sqlalchemy import or_

from pyfarm.core.enums import WorkState
from pyfarm.scheduler.tasks import restart_agent, assign_tasks_to_agent
from pyfarm.models.agent import Agent
from pyfarm.models.tag import Tag
from pyfarm.models.task import Task
from pyfarm.models.software import Software, SoftwareVersion
from pyfarm.master.application import db

def agents():
    agents_query = Agent.query

    filters = {}
    if "tags" in request.args:
        filters["tags"] = request.args.get("tags")
        tags = request.args.get("tags").split(",")
        tags = [x for x in tags if not x == ""]
        if tags:
            agents_query = agents_query.filter(Agent.tags.any(Tag.tag.in_(tags)))

    if "state" in request.args:
        state = request.args.get("state")
        filters["state"] = state
        # TODO Use the actual AgentState enum here
        if state not in ["online", "offline", "disabled", "running", ""]:
            return (render_template(
                "pyfarm/error.html", error="unknown state"), BAD_REQUEST)
        if state != "":
            agents_query = agents_query.filter(Agent.state == state)

    if "hostname" in request.args:
        hostname = request.args.get("hostname")
        filters["hostname"] = hostname
        if hostname != "":
            agents_query = agents_query.filter(
                Agent.hostname.ilike("%%%s%%" % hostname))

    order_dir = "asc"
    order_by = "hostname"
    if "order_by" in request.args:
        order_by = request.args.get("order_by")
        if order_by not in ["hostname", "remote_ip", "state"]:
            return (render_template(
                "pyfarm/error.html", error="unknown order key"), BAD_REQUEST)
        if "order_dir" in request.args:
            order_dir = request.args.get("order_dir")
            if order_dir not in ["asc", "desc"]:
                return (render_template(
                "pyfarm/error.html", error="unknown order dir"), BAD_REQUEST)

    agents_query = agents_query.order_by("%s %s" % (order_by, order_dir))

    agents = agents_query.all()
    return render_template("pyfarm/user_interface/agents.html",
                           agents=agents, filters=filters, order_by=order_by,
                           order_dir=order_dir,
                           order={"order_by": order_by, "order_dir": order_dir})

def single_agent(agent_id):
    agent = Agent.query.filter_by(id=agent_id).first()
    if not agent:
        return (render_template(
                    "pyfarm/error.html", error="Agent %s not found" % agent_id),
                NOT_FOUND)

    tasks = Task.query.filter(Task.agent == agent,
                              or_(Task.state == None,
                                  Task.state == WorkState.RUNNING)).\
                                      order_by(Task.job_id, Task.frame)

    return render_template("pyfarm/user_interface/agent.html", agent=agent,
                           tasks=tasks, software_items=Software.query)

def restart_single_agent(agent_id):
    agent = Agent.query.filter_by(id=agent_id).first()
    if not agent:
        return (render_template(
                    "pyfarm/error.html", error="Agent %s not found" % agent_id),
                NOT_FOUND)

    agent.restart_requested = True
    db.session.add(agent)
    db.session.commit()

    restart_agent.delay(agent.id)

    flash("Agent %s will be restarted" % agent.hostname)

    return redirect(url_for("agents_index_ui"), SEE_OTHER)

def delete_single_agent(agent_id):
    agent = Agent.query.filter_by(id=agent_id).first()
    if not agent:
        return (render_template(
                    "pyfarm/error.html", error="Agent %s not found" % agent_id),
                NOT_FOUND)

    db.session.delete(agent)
    db.session.commit()

    flash("Agent %s has been deleted" % agent.hostname)

    return redirect(url_for("agents_index_ui"), SEE_OTHER)

def agent_add_software(agent_id):
    agent = Agent.query.filter_by(id=agent_id).first()
    if not agent:
        return (render_template(
                    "pyfarm/error.html", error="Agent %s not found" % agent_id),
                NOT_FOUND)

    software = Software.query.filter_by(id=int(request.form["software"])).first()
    if not software:
        return (render_template(
                    "pyfarm/error.html", error="Software %s not found" %
                    request.form["software"]), NOT_FOUND)

    version = SoftwareVersion.query.filter_by(
        id=int(request.form["version"]), software=software).first()
    if not version:
         return (render_template(
                    "pyfarm/error.html", error="Software version %s not found" %
                    request.form["version"]), NOT_FOUND)

    agent.software_versions.append(version)
    db.session.add(agent)
    db.session.add(version)
    db.session.commit()

    assign_tasks_to_agent.delay(agent.id)

    flash("Software %s %s has been added to agent %s" %
          (software.software, version.version, agent.hostname))

    return redirect(url_for("single_agent_ui", agent_id=agent.id), SEE_OTHER)

def agent_delete_software(agent_id, version_id):
    agent = Agent.query.filter_by(id=agent_id).first()
    if not agent:
        return (render_template(
                    "pyfarm/error.html", error="Agent %s not found" % agent_id),
                NOT_FOUND)

    version = SoftwareVersion.query.filter_by(id=version_id).first()
    if not version:
         return (render_template(
                    "pyfarm/error.html", error="Software version %s not found" %
                    version_id), NOT_FOUND)

    agent.software_versions.remove(version)
    db.session.add(agent)
    db.session.commit()

    flash("Software %s %s removed from agent %s" %
          (version.software.software, version.version, agent.hostname))

    return redirect(url_for("single_agent_ui", agent_id=agent.id), SEE_OTHER)
