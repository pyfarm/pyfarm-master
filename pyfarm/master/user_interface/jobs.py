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

from decimal import Decimal

try:
    from httplib import BAD_REQUEST, NOT_FOUND, SEE_OTHER
except ImportError:  # pragma: no cover
    from http.client import BAD_REQUEST, NOT_FOUND, SEE_OTHER

from flask import render_template, request, redirect, url_for, flash
from sqlalchemy.orm import aliased
from sqlalchemy import func, desc, asc

from pyfarm.core.logger import getLogger
from pyfarm.core.enums import WorkState
from pyfarm.scheduler.tasks import delete_job, stop_task, assign_tasks
from pyfarm.models.job import Job
from pyfarm.models.tag import Tag
from pyfarm.models.task import Task
from pyfarm.models.jobqueue import JobQueue
from pyfarm.master.application import db

logger = getLogger("ui.jobs")

def jobs():
    queued_count_query = db.session.query(
        Task.job_id, func.count('*').label('t_queued')).\
            filter(Task.state == None).group_by(Task.job_id).subquery()
    running_count_query = db.session.query(
        Task.job_id, func.count('*').label('t_running')).\
            filter(Task.state == WorkState.RUNNING).\
                group_by(Task.job_id).subquery()
    done_count_query = db.session.query(
        Task.job_id, func.count('*').label('t_done')).\
            filter(Task.state == WorkState.DONE).\
                group_by(Task.job_id).subquery()
    failed_count_query = db.session.query(
        Task.job_id, func.count('*').label('t_failed')).\
            filter(Task.state == WorkState.FAILED).\
                group_by(Task.job_id).subquery()

    jobs_query = db.session.query(Job,
                                  func.coalesce(
                                      queued_count_query.c.t_queued,
                                      0).label('t_queued'),
                                  func.coalesce(
                                      running_count_query.c.t_running,
                                      0).label('t_running'),
                                  func.coalesce(
                                      done_count_query.c.t_done,
                                      0).label('t_done'),
                                  func.coalesce(
                                      failed_count_query.c.t_failed,
                                      0).label('t_failed')).\
        outerjoin(queued_count_query, Job.id == queued_count_query.c.job_id).\
        outerjoin(running_count_query, Job.id == running_count_query.c.job_id).\
        outerjoin(done_count_query, Job.id == done_count_query.c.job_id).\
        outerjoin(failed_count_query, Job.id == failed_count_query.c.job_id)

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

    order_dir = "desc"
    order_by = "time_submitted"
    if "order_by" in request.args:
        order_by = request.args.get("order_by")
    if order_by not in ["title", "state", "time_submitted", "t_queued",
                        "t_running", "t_failed", "t_done"]:
        return (render_template(
            "pyfarm/error.html",
            error="Unknown order key %r. Options are 'title', 'state', "
                  "'time_submitted', 't_queued', 't_running', 't_failed' or "
                  "'t_done'" % order_by), BAD_REQUEST)
    if "order_dir" in request.args:
        order_dir = request.args.get("order_dir")
        if order_dir not in ["asc", "desc"]:
            return (render_template(
            "pyfarm/error.html",
            error="Unknown order direction %r. Options are 'asc' or 'desc'" %
                  order_dir),
            BAD_REQUEST)
    if order_by == "time_submitted" and order_dir == "desc":
        jobs_query = jobs_query.order_by(desc(Job.time_submitted))
    elif order_by == "time_submitted" and order_dir == "asc":
        jobs_query = jobs_query.order_by(asc(Job.time_submitted))
    elif order_by == "state" and order_dir == "desc":
        jobs_query = jobs_query.order_by(desc(Job.state))
    elif order_by == "state" and order_dir == "asc":
        jobs_query = jobs_query.order_by(asc(Job.state))
    else:
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

    first_task = Task.query.filter_by(job=job).order_by("frame asc").first()
    last_task = Task.query.filter_by(job=job).order_by("frame desc").first()

    tasks = job.tasks.order_by(Task.frame)

    jobqueues = JobQueue.query.all()

    return render_template("pyfarm/user_interface/job.html", job=job,
                           tasks=tasks, first_task=first_task,
                           last_task=last_task, queues=jobqueues)

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

    flash("Job %s will be deleted." % job.title)

    return redirect(url_for("jobs_index_ui"), SEE_OTHER)

def rerun_single_job(job_id):
    job = Job.query.filter_by(id=job_id).first()
    if not job:
        return (render_template(
                    "pyfarm/error.html", error="Job %s not found" % job_id),
                NOT_FOUND)

    for task in job.tasks:
        if task.state != WorkState.RUNNING:
            task.state = None
            task.agent = None
            task.failures = 0
            db.session.add(task)

    job.state = None
    db.session.add(job)
    db.session.commit()

    assign_tasks.delay()

    flash("Job %s will be run again." % job.title)

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

    flash("Job %s will be paused." % job.title)

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

    flash("Job %s is unpaused." % job.title)

    if "next" in request.args:
        return redirect(request.args.get("next"), SEE_OTHER)
    else:
        return redirect(url_for("jobs_index_ui"), SEE_OTHER)

def alter_frames_in_single_job(job_id):
    job = Job.query.filter_by(id=job_id).first()
    if not job:
        return (render_template(
                    "pyfarm/error.html", error="Job %s not found" % job_id),
                NOT_FOUND)
    start = Decimal(request.form['start'])
    end = Decimal(request.form['end'])
    by = Decimal(request.form['by'])

    try:
        job.alter_frame_range(start, end, by)
    except ValueError as e:
        return (render_template(
                    "pyfarm/error.html", error=e), BAD_REQUEST)

    db.session.commit()
    assign_tasks.delay()

    flash("Frame selection for job %s has been changed." % job.title)

    return redirect(url_for("single_job_ui", job_id=job.id), SEE_OTHER)

def alter_scheduling_parameters_for_job(job_id):
    job = Job.query.filter_by(id=job_id).first()
    if not job:
        return (render_template(
                    "pyfarm/error.html", error="Job %s not found" % job_id),
                NOT_FOUND)

    job.priority = int(request.form['priority'])
    job.weight = int(request.form['weight'])
    if request.form['minimum_agents']:
        job.minimum_agents = int(request.form['minimum_agents'])
    else:
        job.minimum_agents = None
    if request.form['maximum_agents']:
        job.maximum_agents = int(request.form['maximum_agents'])
    else:
        job.maximum_agents = None
    job.batch = int(request.form['batch'])

    if request.form['queue']:
        queue_id = int(request.form['queue'])
        queue = JobQueue.query.filter_by(id=queue_id).first()
        if not queue:
            return (render_template(
                        "pyfarm/error.html", error="Queue %s not found" % queue_id),
                    NOT_FOUND)
        job.queue = queue
    else:
        job.queue = None

    db.session.add(job)
    db.session.commit()

    flash("Scheduling parameters for job %s have been changed." % job.title)

    return redirect(url_for("single_job_ui", job_id=job.id), SEE_OTHER)

def update_notes_for_job(job_id):
    job = Job.query.filter_by(id=job_id).first()
    if not job:
        return (render_template(
                    "pyfarm/error.html", error="Job %s not found" % job_id),
                NOT_FOUND)

    job.notes = request.form['notes']

    db.session.add(job)
    db.session.commit()

    flash("Free form notes for job %s have been edited." % job.title)

    return redirect(url_for("single_job_ui", job_id=job.id), SEE_OTHER)

def update_tags_in_job(job_id):
    job = Job.query.filter_by(id=job_id).first()
    if not job:
        return (render_template(
                    "pyfarm/error.html", error="Job %s not found" % job_id),
                NOT_FOUND)

    tagnames = request.form["tags"].split(" ")
    tagnames = [x for x in tagnames if not x == ""]
    tags = []
    for name in tagnames:
        tag = Tag.query.filter_by(tag=name).first()
        if not tag:
            tag = Tag(tag=name)
            db.session.add(tag)
        tags.append(tag)

    job.tags = tags

    db.session.add(job)
    db.session.commit()

    flash("Tags for job %s have been updated." % job.title)

    return redirect(url_for("single_job_ui", job_id=job.id), SEE_OTHER)

def rerun_single_task(job_id, task_id):
    job = Job.query.filter_by(id=job_id).first()
    if not job:
        return (render_template(
                    "pyfarm/error.html", error="Job %s not found" % job_id),
                NOT_FOUND)

    task = Task.query.filter_by(id=task_id, job=job).first()
    if not task:
        return (render_template(
                    "pyfarm/error.html", error="Task %s not found" % task_id),
                NOT_FOUND)
    if task.state == WorkState.RUNNING:
        return (render_template(
                    "pyfarm/error.html", error="Cannot rerun task while it is "
                    "still running" % job_id),
                BAD_REQUEST)

    task.state = None
    task.agent = None
    task.failures = 0

    if Job.state != WorkState.RUNNING:
        job.state = None

    db.session.add(job)
    db.session.add(task)
    db.session.commit()

    assign_tasks.delay()

    flash("Task %s (frame %s) in job %s will be run again." %
          (task.id, task.frame, job.title))

    if "next" in request.args:
        return redirect(request.args.get("next"), SEE_OTHER)
    else:
        return redirect(url_for("single_job_ui", job_id=job.id), SEE_OTHER)
