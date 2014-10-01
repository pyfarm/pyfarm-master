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

from flask import render_template, request, redirect, url_for
from sqlalchemy.orm import aliased
from sqlalchemy import func

from pyfarm.core.logger import getLogger
from pyfarm.core.enums import WorkState
from pyfarm.scheduler.tasks import delete_job, stop_task, assign_tasks
from pyfarm.models.job import Job
from pyfarm.models.tag import Tag
from pyfarm.models.task import Task
from pyfarm.master.application import db

logger = getLogger("ui.jobs")

def jobs():
    a_q = aliased(Task)
    a_r = aliased(Task)
    a_d = aliased(Task)
    a_f = aliased(Task)
    jobs_query = db.session.query(Job,
                                  func.count(
                                      a_q.id.distinct()).label("t_queued"),
                                  func.count(
                                      a_r.id.distinct()).label("t_running"),
                                  func.count(
                                      a_d.id.distinct()).label("t_done"),
                                  func.count(
                                      a_f.id.distinct()).label("t_failed")).\
        outerjoin(a_q, Job.tasks_queued).\
        outerjoin(a_r, Job.tasks_running).\
        outerjoin(a_d, Job.tasks_done).\
        outerjoin(a_f, Job.tasks_failed).\
        group_by(Job)

    filters = {}
    if "tags" in request.args:
        filters["tags"] = request.args.get("tags")
        tags = request.args.get("tags").split(",")
        tags = [x for x in tags if not x == ""]
        if tags:
            jobs_query = jobs_query.filter(Job.tags.any(Tag.tag.in_(tags)))

    if "state" in request.args:
        state = request.args.get("state")
        filters["state"] = state
        # TODO Use the actual WorkState enum here
        if state not in ["paused", "running", "done", "failed", ""]:
            return (render_template(
                "pyfarm/error.html", error="unknown state"), BAD_REQUEST)
        if state != "":
            jobs_query = jobs_query.filter(Job.state == state)

    if "title" in request.args:
        title = request.args.get("title")
        filters["title"] = title
        if title != "":
            jobs_query = jobs_query.filter(
                Job.title.ilike("%%%s%%" % title))

    order_dir = "asc"
    order_by = "title"
    if "order_by" in request.args:
        order_by = request.args.get("order_by")
        if order_by not in ["title", "state", "time_submitted", "t_queued",
                            "t_running", "t_failed", "t_done"]:
            return (render_template(
                "pyfarm/error.html", error="unknown order key"), BAD_REQUEST)
        if "order_dir" in request.args:
            order_dir = request.args.get("order_dir")
            if order_dir not in ["asc", "desc"]:
                return (render_template(
                "pyfarm/error.html", error="unknown order dir"), BAD_REQUEST)
        jobs_query = jobs_query.order_by("%s %s" % (order_by, order_dir))

    jobs = jobs_query.all()
    return render_template("pyfarm/user_interface/jobs.html",
                           jobs=jobs, filters=filters, order_by=order_by,
                           order_dir=order_dir,
                           order={"order_by": order_by, "order_dir": order_dir})

def single_job(job_id):
    job = Job.query.filter_by(id=job_id).first()
    if not job:
        return (render_template(
                    "pyfarm/error.html", error="Job %s not found" % job_id),
                NOT_FOUND)

    tasks = job.tasks.order_by(Task.frame)

    return render_template("pyfarm/user_interface/job.html", job=job,
                           tasks=tasks)

def delete_single_job(job_id):
    job = Job.query.filter_by(id=job_id).first()
    if not job:
        return (render_template(
                    "pyfarm/error.html", error="Job %s not found" % job_id),
                NOT_FOUND)

    job.to_be_deleted = True
    db.session.add(job)
    db.session.commit()

    logger.info("Marking job %s for deletion", job.id)

    delete_job.delay(job.id)

    return redirect(url_for("jobs_index_ui"), SEE_OTHER)

def rerun_single_job(job_id):
    job = Job.query.filter_by(id=job_id).first()
    if not job:
        return (render_template(
                    "pyfarm/error.html", error="Job %s not found" % job_id),
                NOT_FOUND)

    for task in job.tasks:
        if task.state is not WorkState.RUNNING:
            task.state = None
            task.agent = None
            task.attempts = 0
            db.session.add(task)

    job.state = None
    db.session.add(job)
    db.session.commit()

    assign_tasks.delay()

    if "next" in request.args:
        return redirect(request.args.get("next"), SEE_OTHER)
    else:
        return redirect(url_for("jobs_index_ui"), SEE_OTHER)

def pause_single_job(job_id):
    job = Job.query.filter_by(id=job_id).first()
    if not job:
        return (render_template(
                    "pyfarm/error.html", error="Job %s not found" % job_id),
                NOT_FOUND)

    for task in job.tasks:
        if task.state == WorkState.RUNNING:
            stop_task.delay(task.id)

    job.state = WorkState.PAUSED
    db.session.add(job)
    db.session.commit()

    assign_tasks.delay()

    if "next" in request.args:
        return redirect(request.args.get("next"), SEE_OTHER)
    else:
        return redirect(url_for("jobs_index_ui"), SEE_OTHER)

def unpause_single_job(job_id):
    job = Job.query.filter_by(id=job_id).first()
    if not job:
        return (render_template(
                    "pyfarm/error.html", error="Job %s not found" % job_id),
                NOT_FOUND)

    job.state = None
    db.session.add(job)
    db.session.commit()

    if "next" in request.args:
        return redirect(request.args.get("next"), SEE_OTHER)
    else:
        return redirect(url_for("jobs_index_ui"), SEE_OTHER)
