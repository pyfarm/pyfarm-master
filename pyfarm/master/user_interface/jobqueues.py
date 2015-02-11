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

from pyfarm.core.logger import getLogger
from pyfarm.core.enums import WorkState
from pyfarm.master.application import db
from pyfarm.models.jobqueue import JobQueue
from pyfarm.models.job import Job

logger = getLogger("ui.jobqueues")

def jobqueues():
    jobqueues = JobQueue.query.filter_by(parent_jobqueue_id=None)

    top_level_jobs = Job.query.filter_by(queue=None)

    return render_template("pyfarm/user_interface/jobqueues.html",
                           jobqueues=jobqueues, top_level_jobs=top_level_jobs,
                           WorkState=WorkState)

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
