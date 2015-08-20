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
from sqlalchemy import or_, desc

from pyfarm.core.enums import WorkState, AgentState
from pyfarm.scheduler.tasks import (
    restart_agent, assign_tasks_to_agent, check_all_software_on_agent,
    poll_agent)
from pyfarm.models.agent import Agent
from pyfarm.models.tag import Tag
from pyfarm.models.task import Task
from pyfarm.models.tasklog import TaskLog, TaskTaskLogAssociation
from pyfarm.models.software import Software, SoftwareVersion
from pyfarm.master.application import db

try:
    range_ = xrange # pylint: disable=undefined-variable
except NameError: # pragma: no cover
    range_ = range

def agents():
    agents_query = Agent.query

    filters = {}
    if "tags" in request.args:
        filters["tags"] = request.args.get("tags")
        tags = request.args.get("tags").split(" ")
        tags = [x for x in tags if not x == ""]
        if tags:
            agents_query = agents_query.filter(Agent.tags.any(Tag.tag.in_(tags)))

    filters["state_online"] = ("state_online" in request.args and
                               request.args["state_online"].lower() == "true")
    filters["state_offline"] = ("state_offline" in request.args and
                               request.args["state_offline"].lower() == "true")
    filters["state_running"] = ("state_running" in request.args and
                                request.args["state_running"].lower() == "true")
    filters["state_disabled"] = ("state_disabled" in request.args and
                             request.args["state_disabled"].lower() == "true")
    no_state_filters = True
    if (filters["state_online"] or
        filters["state_offline"] or
        filters["state_running"] or
        filters["state_disabled"]):
        no_state_filters = False
        wanted_states = []
        if filters["state_online"]:
            wanted_states.append(AgentState.ONLINE)
        if filters["state_offline"]:
            wanted_states.append(AgentState.OFFLINE)
        if filters["state_running"]:
            wanted_states.append(AgentState.RUNNING)
        if filters["state_disabled"]:
            wanted_states.append(AgentState.DISABLED)
        agents_query = agents_query.filter(Agent.state.in_(wanted_states))

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
        if order_by not in ["hostname", "remote_ip", "state", "version",
                            "last_heard_from", "cpus", "ram"]:
            return (render_template(
                "pyfarm/error.html", error="unknown order key"), BAD_REQUEST)
        if "order_dir" in request.args:
            order_dir = request.args.get("order_dir")
            if order_dir not in ["asc", "desc"]:
                return (render_template(
                "pyfarm/error.html", error="unknown order dir"), BAD_REQUEST)

    agents_query = agents_query.order_by("%s %s" % (order_by, order_dir))
    agents_query = agents_query.order_by(Agent.id)

    agents_count = agents_query.count()
    online_agents_count = agents_query.filter(
        Agent.state == AgentState.ONLINE).count()
    offline_agents_count = agents_query.filter(
        Agent.state == AgentState.OFFLINE).count()
    running_agents_count = agents_query.filter(
        Agent.state == AgentState.RUNNING).count()
    disabled_agents_count = agents_query.filter(
        Agent.state == AgentState.DISABLED).count()

    per_page = int(request.args.get("per_page", 100))
    page = int(request.args.get("page", 1))
    filters["per_page"] = per_page
    filters["page"] = page
    num_pages = 1
    all_pages = []
    if per_page > 0:
        agents_query = agents_query.offset((page - 1) * per_page).limit(per_page)
        num_pages = int(agents_count / per_page)
        if agents_count % per_page > 0:
            num_pages = num_pages + 1
        all_pages = range_(0, num_pages)

    filters_and_order = filters.copy()
    filters_and_order.update({"order_by": order_by, "order_dir": order_dir})
    filters_and_order_wo_pagination = filters_and_order.copy()
    del filters_and_order_wo_pagination["per_page"]
    del filters_and_order_wo_pagination["page"]
    agents = agents_query.all()
    return render_template("pyfarm/user_interface/agents.html",
                           agents=agents, filters=filters, order_by=order_by,
                           order_dir=order_dir,
                           order={"order_by": order_by, "order_dir": order_dir},
                           per_page=per_page, page=page, num_pages=num_pages,
                           all_pages=all_pages, agents_count=agents_count,
                           filters_and_order_wo_pagination=
                           filters_and_order_wo_pagination,
                           no_state_filters=no_state_filters,
                           filters_and_order=filters_and_order,
                           online_agents_count=online_agents_count,
                           offline_agents_count=offline_agents_count,
                           running_agents_count=running_agents_count,
                           disabled_agents_count=disabled_agents_count)

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

    tasklogs = TaskLog.query.filter_by(agent=agent).\
        order_by(desc(TaskLog.created_on)).limit(10).all()
    for tasklog in tasklogs:
        assocation = TaskTaskLogAssociation.query.filter_by(log=tasklog).first()
        if assocation:
            tasklog.task = assocation.task
            tasklog.attempt = assocation.attempt
        else:
            tasklog.task = None

    return render_template("pyfarm/user_interface/agent.html", agent=agent,
                           tasks=tasks, software_items=Software.query,
                           tasklogs=tasklogs)

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

def restart_multiple_agents():
    agent_ids = request.form.getlist("agent_id")

    agents = []
    for agent_id in agent_ids:
        agent = Agent.query.filter_by(id=agent_id).first()
        if not agent:
            return (render_template(
                        "pyfarm/error.html",
                        error="Agent %s not found" % agent_id),
                    NOT_FOUND)

        agent.restart_requested = True
        db.session.add(agent)
        agents.append(agent)

    db.session.commit()

    for agent in agents:
        restart_agent.delay(agent.id)

    flash("Selected agents will be restarted.")

    if "next" in request.args:
        return redirect(request.args.get("next"), SEE_OTHER)
    else:
        return redirect(url_for("agents_index_ui"), SEE_OTHER)

def disable_single_agent(agent_id):
    agent = Agent.query.filter_by(id=agent_id).first()
    if not agent:
        return (render_template(
                    "pyfarm/error.html",
                    error="Agent %s not found" % agent_id),
                NOT_FOUND)

    agent.state = AgentState.DISABLED
    db.session.add(agent)
    db.session.commit()

    flash("Agent %s is now disabled." % agent.hostname)

    if "next" in request.args:
        return redirect(request.args.get("next"), SEE_OTHER)
    else:
        return redirect(url_for("agents_index_ui"), SEE_OTHER)

def enable_single_agent(agent_id):
    agent = Agent.query.filter_by(id=agent_id).first()
    if not agent:
        return (render_template(
                    "pyfarm/error.html",
                    error="Agent %s not found" % agent_id),
                NOT_FOUND)

    agent.state = AgentState.OFFLINE
    db.session.add(agent)
    db.session.commit()

    poll_agent.delay(agent.id)

    flash("Agent %s is now enabled." % agent.hostname)

    if "next" in request.args:
        return redirect(request.args.get("next"), SEE_OTHER)
    else:
        return redirect(url_for("agents_index_ui"), SEE_OTHER)

def disable_multiple_agents():
    agent_ids = request.form.getlist("agent_id")

    for agent_id in agent_ids:
        agent = Agent.query.filter_by(id=agent_id).first()
        if not agent:
            return (render_template(
                        "pyfarm/error.html",
                        error="Agent %s not found" % agent_id),
                    NOT_FOUND)

        agent.state = AgentState.DISABLED
        db.session.add(agent)

    db.session.commit()

    flash("Selected agents are now disabled.")

    if "next" in request.args:
        return redirect(request.args.get("next"), SEE_OTHER)
    else:
        return redirect(url_for("agents_index_ui"), SEE_OTHER)

def enable_multiple_agents():
    agent_ids = request.form.getlist("agent_id")

    agents = []
    for agent_id in agent_ids:
        agent = Agent.query.filter_by(id=agent_id).first()
        if not agent:
            return (render_template(
                        "pyfarm/error.html",
                        error="Agent %s not found" % agent_id),
                    NOT_FOUND)

        agent.state = AgentState.OFFLINE
        db.session.add(agent)
        agents.append(agent)

    db.session.commit()

    for agent in agents:
        poll_agent.delay(agent.id)

    flash("Selected agents are now enabled.")

    if "next" in request.args:
        return redirect(request.args.get("next"), SEE_OTHER)
    else:
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

    if request.form["version"].strip() == "":
        return (render_template(
            "pyfarm/error.html", error="No version selected"), BAD_REQUEST)
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

def update_notes_for_agent(agent_id):
    agent = Agent.query.filter_by(id=agent_id).first()
    if not agent:
        return (render_template(
                    "pyfarm/error.html", error="Agent %s not found" % agent_id),
                NOT_FOUND)

    agent.notes = request.form["notes"]

    db.session.add(agent)
    db.session.commit()

    flash("Free form notes for agent %s have been edited." % agent.hostname)

    return redirect(url_for("single_agent_ui", agent_id=agent.id), SEE_OTHER)

def update_tags_in_agent(agent_id):
    agent = Agent.query.filter_by(id=agent_id).first()
    if not agent:
        return (render_template(
                    "pyfarm/error.html", error="Agent %s not found" % agent_id),
                NOT_FOUND)

    tagnames = request.form["tags"].split(" ")
    tagnames = [x.strip() for x in tagnames if not x == ""]
    tags = []
    for name in tagnames:
        tag = Tag.query.filter_by(tag=name).first()
        if not tag:
            tag = Tag(tag=name)
            db.session.add(tag)
        tags.append(tag)

    agent.tags = tags

    db.session.add(agent)
    db.session.commit()

    flash("Tags for agent %s have been updated." % agent.hostname)

    return redirect(url_for("single_agent_ui", agent_id=agent.id), SEE_OTHER)

def check_software_in_single_agent(agent_id):
    agent = Agent.query.filter_by(id=agent_id).first()
    if not agent:
        return (render_template(
                    "pyfarm/error.html", error="Agent %s not found" % agent_id),
                NOT_FOUND)

    check_all_software_on_agent.delay(agent.id)

    flash("Checking available software on agent %s" % agent.hostname)

    return redirect(url_for("single_agent_ui", agent_id=agent.id), SEE_OTHER)
