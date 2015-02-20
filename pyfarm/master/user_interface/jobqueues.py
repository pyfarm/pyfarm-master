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
    from httplib import SEE_OTHER, NOT_FOUND
except ImportError:  # pragma: no cover
    from http.client import SEE_OTHER, NOT_FOUND

from flask import render_template, request, redirect, url_for, flash
from sqlalchemy import or_

from pyfarm.core.logger import getLogger
from pyfarm.core.enums import WorkState
from pyfarm.master.application import db
from pyfarm.models.jobqueue import JobQueue
from pyfarm.models.job import Job

logger = getLogger("ui.jobqueues")

def jobqueues():
    jobqueues = JobQueue.query.filter_by(parent_jobqueue_id=None).all()
    jobqueues = sorted(jobqueues, key=lambda x: x.num_assigned_agents(),
                       reverse=True)

    top_level_jobs_query = Job.query.filter_by(queue=None)

    filters = {}
    if ("state_paused" not in request.args and
        "state_queued" not in request.args and
        "state_running" not in request.args and
        "state_done" not in request.args and
        "state_failed" not in request.args):
        filters["state_paused"] = False
        filters["state_queued"] = False
        filters["state_running"] = True
        filters["state_done"] = False
        filters["state_failed"] = False
    else:
        filters["state_paused"] = ("state_paused" in request.args and
                                   request.args["state_paused"].lower() ==
                                        "true")
        filters["state_queued"] = ("state_queued" in request.args and
                                   request.args["state_queued"].lower() ==
                                        "true")
        filters["state_running"] = ("state_running" in request.args and
                                    request.args["state_running"].lower() ==
                                        "true")
        filters["state_done"] = ("state_done" in request.args and
                                 request.args["state_done"].lower() ==
                                        "true")
        filters["state_failed"] = ("state_failed" in request.args and
                                   request.args["state_failed"].lower() ==
                                        "true")

    wanted_states = []
    if filters["state_paused"]:
        wanted_states.append(WorkState.PAUSED)
    if filters["state_running"]:
        wanted_states.append(WorkState.RUNNING)
    if filters["state_done"]:
        wanted_states.append(WorkState.DONE)
    if filters["state_failed"]:
        wanted_states.append(WorkState.FAILED)
    if filters["state_queued"]:
        top_level_jobs_query = top_level_jobs_query.filter(or_(
            Job.state == None,
            Job.state.in_(wanted_states)))
    else:
        top_level_jobs_query = top_level_jobs_query.filter(
            Job.state.in_(wanted_states))

    top_level_jobs = sorted(top_level_jobs_query.all(),
                            key=lambda x: x.num_assigned_agents(), reverse=True)

    return render_template("pyfarm/user_interface/jobqueues.html",
                           jobqueues=jobqueues, top_level_jobs=top_level_jobs,
                           WorkState=WorkState, filters=filters)

def jobqueue_create():
    if request.method == 'POST':
        jobqueue = JobQueue()
        jobqueue.name = request.form["name"]
        if request.form["parent"] != "":
            jobqueue.parent_jobqueue_id = request.form["parent"]
        if request.form["minimum_agents"] != "":
            jobqueue.minimum_agents = request.form["minimum_agents"]
        if request.form["maximum_agents"] != "":
            jobqueue.maximum_agents = request.form["maximum_agents"]
        if request.form["priority"] != "":
            jobqueue.priority = request.form["priority"]
        if request.form["weight"] != "":
            jobqueue.weight = request.form["weight"]

        db.session.add(jobqueue)
        db.session.flush()

        jobqueue.fullpath = jobqueue.path()
        db.session.add(jobqueue)
        db.session.commit()

        flash("Created new jobqueue \"%s\"." % jobqueue.name)

        return redirect(url_for("jobqueues_index_ui"), SEE_OTHER)
    else:
        jobqueues = JobQueue.query

        parent = request.args.get("parent", None)
        if parent:
            parent = int(parent)

        return render_template("pyfarm/user_interface/jobqueue_create.html",
                            parent=parent, jobqueues=jobqueues)

def jobqueue(queue_id):
    queue = JobQueue.query.filter_by(id=queue_id).first()
    if not queue:
        return (render_template(
                    "pyfarm/error.html",
                    error="Jobqueue %s not found" % queue_id), NOT_FOUND)

    if request.method == 'POST':
        if request.form["minimum_agents"] != "":
            queue.minimum_agents = request.form["minimum_agents"]
        else:
            queue.minimum_agents = None
        if request.form["maximum_agents"] != "":
            queue.maximum_agents = request.form.get("maximum_agents", None)
        else:
            queue.maximum_agents = None
        queue.priority = request.form["priority"]
        queue.weight = request.form["weight"]

        db.session.add(queue)
        db.session.commit()

        flash("Jobqueue %s has been updated." % queue.name)

        return redirect(url_for("single_jobqueue_ui", queue_id=queue_id),
                        SEE_OTHER)

    else:

        return render_template("pyfarm/user_interface/jobqueue.html",
                            queue=queue)

def delete_jobqueue(queue_id):
    with db.session.no_autoflush:
        queue = JobQueue.query.filter_by(id=queue_id).first()
        if not queue:
            return (render_template(
                        "pyfarm/error.html",
                        error="Jobqueue %s not found" % queue_id), NOT_FOUND)

        for subqueue in queue.children:
            delete_subqueue(subqueue)

        for job in queue.jobs:
            job.queue = queue.parent
            db.session.add(job)

    logger.info("Deleting jobqueue %s", queue.path())

    db.session.delete(queue)
    db.session.commit()

    return redirect(url_for("jobqueues_index_ui"), SEE_OTHER)

def delete_subqueue(queue):
    for subqueue in queue.children:
        delete_subqueue(subqueue)

    for job in queue.jobs:
        job.queue = queue.parent
        db.session.add(job)

    logger.info("Deleting jobqueue %s", queue.path())

    db.session.delete(queue)
    db.session.flush()
