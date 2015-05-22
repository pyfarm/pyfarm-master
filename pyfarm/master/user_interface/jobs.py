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
from datetime import datetime

try:
    from httplib import (
        BAD_REQUEST, NOT_FOUND, SEE_OTHER, INTERNAL_SERVER_ERROR)
except ImportError:  # pragma: no cover
    from http.client import (
        BAD_REQUEST, NOT_FOUND, SEE_OTHER, INTERNAL_SERVER_ERROR)

from flask import render_template, request, redirect, url_for, flash
from sqlalchemy.orm import aliased
from sqlalchemy import func, desc, asc, or_, distinct

from pyfarm.core.logger import getLogger
from pyfarm.core.enums import WorkState, _WorkState, AgentState
from pyfarm.scheduler.tasks import delete_job, stop_task, assign_tasks
from pyfarm.models.job import (
    Job, JobDependency, JobTagAssociation, JobNotifiedUser)
from pyfarm.models.tag import Tag
from pyfarm.models.task import Task
from pyfarm.models.agent import Agent
from pyfarm.models.jobqueue import JobQueue
from pyfarm.models.jobtype import JobType, JobTypeVersion
from pyfarm.models.user import User
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
    child_count_query = db.session.query(
        JobDependency.c.parentid, func.count('*').label('child_count')).\
                group_by(JobDependency.c.parentid).subquery()
    blocker_count_query = db.session.query(
        JobDependency.c.childid, func.count('*').label('blocker_count')).\
            join(Job, Job.id == JobDependency.c.parentid).\
                filter(or_(Job.state == None, Job.state != WorkState.DONE)).\
                    group_by(JobDependency.c.childid).subquery()
    agent_count_query = db.session.query(
        Task.job_id, func.count(distinct(Task.agent_id)).label('agent_count')).\
            filter(Task.agent_id != None, or_(Task.state == None,
                                              Task.state == WorkState.RUNNING),
                   Task.agent.has(Agent.state != AgentState.OFFLINE)).\
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
                                      0).label('t_failed'),
                                  User.username,
                                  JobType.name.label('jobtype_name'),
                                  JobType.id.label('jobtype_id'),
                                  JobQueue.fullpath.label('jobqueue_path'),
                                  func.coalesce(
                                      child_count_query.c.child_count,
                                      0).label('child_count'),
                                  func.coalesce(
                                      blocker_count_query.c.blocker_count,
                                      0).label('blocker_count'),
                                  func.coalesce(
                                      agent_count_query.c.agent_count,
                                      0).label('agent_count')).\
        join(JobTypeVersion, Job.jobtype_version_id == JobTypeVersion.id).\
        join(JobType, JobTypeVersion.jobtype_id == JobType.id).\
        outerjoin(JobQueue, Job.job_queue_id == JobQueue.id).\
        outerjoin(queued_count_query, Job.id == queued_count_query.c.job_id).\
        outerjoin(running_count_query, Job.id == running_count_query.c.job_id).\
        outerjoin(done_count_query, Job.id == done_count_query.c.job_id).\
        outerjoin(failed_count_query, Job.id == failed_count_query.c.job_id).\
        outerjoin(User, Job.user_id == User.id).\
        outerjoin(child_count_query, Job.id == child_count_query.c.parentid).\
        outerjoin(blocker_count_query, Job.id == blocker_count_query.c.childid).\
        outerjoin(agent_count_query, Job.id == agent_count_query.c.job_id)

    filters = {}
    if "tags" in request.args:
        filters["tags"] = request.args.get("tags")
        tags = request.args.get("tags").split(" ")
        tags = [x for x in tags if not x == ""]
        for tag in tags:
            jobs_query = jobs_query.filter(Job.tags.any(Tag.tag == tag))

    filters["state_paused"] = ("state_paused" in request.args and
                               request.args["state_paused"].lower() == "true")
    filters["state_queued"] = ("state_queued" in request.args and
                               request.args["state_queued"].lower() == "true")
    filters["state_running"] = ("state_running" in request.args and
                                request.args["state_running"].lower() == "true")
    filters["state_done"] = ("state_done" in request.args and
                             request.args["state_done"].lower() == "true")
    filters["state_failed"] = ("state_failed" in request.args and
                               request.args["state_failed"].lower() == "true")
    no_state_filters = True
    if (filters["state_paused"] or
        filters["state_queued"] or
        filters["state_running"] or
        filters["state_done"] or
        filters["state_failed"]):
        no_state_filters = False
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
            jobs_query = jobs_query.filter(or_(
                Job.state == None,
                Job.state.in_(wanted_states)))
        else:
            jobs_query = jobs_query.filter(Job.state.in_(wanted_states))

    if "title" in request.args:
        title = request.args.get("title")
        filters["title"] = title
        if title != "":
            jobs_query = jobs_query.filter(
                Job.title.ilike("%%%s%%" % title))

    filters["hidden_filter"] = ("hidden_filter" in request.args and
                                request.args["hidden_filter"].lower() == "true")
    filters["hidden"] = False
    filters["not_hidden"] = True

    if filters["hidden_filter"]:
        filters["hidden"] = ("hidden" in request.args and
                             request.args["hidden"].lower() == "true")
        filters["not_hidden"] = ("not_hidden" in request.args and
                                 request.args["not_hidden"].lower() == "true")
    if not filters["hidden"]:
        jobs_query = jobs_query.filter(Job.hidden != True)
    if not filters["not_hidden"]:
        jobs_query = jobs_query.filter(Job.hidden != False)

    filters["blocked_filter"] = ("blocked_filter" in request.args and
                                 request.args["blocked_filter"].lower() ==
                                    "true")
    filters["blocked"] = True
    filters["not_blocked"] = True

    if filters["blocked_filter"]:
        filters["blocked"] = ("blocked" in request.args and
                              request.args["blocked"].lower() == "true")
        filters["not_blocked"] = ("not_blocked" in request.args and
                                  request.args["not_blocked"].lower() == "true")
    if not filters["blocked"]:
        jobs_query = jobs_query.filter(
            blocker_count_query.c.blocker_count == None)
    if not filters["not_blocked"]:
        jobs_query = jobs_query.filter(
            blocker_count_query.c.blocker_count != None)

    filters["no_user"] = ("no_user" in request.args and
                          request.args["no_user"].lower() == "true")
    if "u" in request.args or filters["no_user"]:
        user_ids = request.args.getlist("u")
        user_ids = [int(x) for x in user_ids]
        if filters["no_user"]:
            jobs_query = jobs_query.filter(or_(
                Job.user_id.in_(user_ids),
                Job.user_id == None))
        else:
            jobs_query = jobs_query.filter(Job.user_id.in_(user_ids))
        filters["u"] = user_ids

    filters["no_queue"] = ("no_queue" in request.args and
                           request.args["no_queue"].lower() == "true")
    if "q" in request.args or filters["no_queue"]:
        jobqueue_ids = request.args.getlist("q")
        jobqueue_ids = [int(x) for x in jobqueue_ids]
        if filters["no_queue"]:
            jobs_query = jobs_query.filter(or_(
                Job.job_queue_id.in_(jobqueue_ids),
                Job.job_queue_id == None))
        else:
            jobs_query = jobs_query.filter(JobQueue.id.in_(jobqueue_ids))
        filters["q"] = jobqueue_ids

    if "p" in request.args:
        priorities = request.args.getlist("p")
        priorities = [int(x) for x in priorities]
        jobs_query = jobs_query.filter(Job.priority.in_(priorities))
        filters["p"] = priorities

    if "jt" in request.args:
        jobtype_ids = request.args.getlist("jt")
        jobtype_ids = [int(x) for x in jobtype_ids]
        jobs_query = jobs_query.filter(JobType.id.in_(jobtype_ids))
        filters["jt"] = jobtype_ids

    order_dir = "desc"
    order_by = "time_submitted"
    if "order_by" in request.args:
        order_by = request.args.get("order_by")
    if order_by not in ["title", "state", "time_submitted", "t_queued",
                        "t_running", "t_failed", "t_done", "username",
                        "jobtype_name", "agent_count", "priority", "weight",
                        "jobqueue_path"]:
        return (render_template(
            "pyfarm/error.html",
            error="Unknown order key %r. Options are 'title', 'state', "
                  "'time_submitted', 't_queued', 't_running', 't_failed', "
                  "'t_done', 'username', 'agent_count', 'priority', 'weight' "
                  "or 'jobqueue_path'" % order_by), BAD_REQUEST)
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
    elif order_by == "weight" and order_dir == "asc":
        jobs_query = jobs_query.order_by(asc(Job.weight))
    elif order_by == "weight" and order_dir == "desc":
        jobs_query = jobs_query.order_by(desc(Job.weight))
    elif order_by == "priority" and order_dir == "asc":
        jobs_query = jobs_query.order_by(asc(Job.priority))
    elif order_by == "priority" and order_dir == "desc":
        jobs_query = jobs_query.order_by(desc(Job.priority))
    else:
        jobs_query = jobs_query.order_by("%s %s" % (order_by, order_dir))

    jobs_query = jobs_query.order_by(Job.id)

    jobs_count = jobs_query.count()
    queued_jobs_count = jobs_query.filter(Job.state == None).count()
    running_jobs_count = jobs_query.filter(
        Job.state == WorkState.RUNNING).count()
    failed_jobs_count = jobs_query.filter(Job.state == WorkState.FAILED).count()
    done_jobs_count = jobs_query.filter(Job.state == WorkState.DONE).count()

    jobs_subquery = jobs_query.subquery()

    per_page = int(request.args.get("per_page", 100))
    page = int(request.args.get("page", 1))
    filters["per_page"] = per_page
    filters["page"] = page
    num_pages = 1
    all_pages = []
    if per_page > 0:
        jobs_query = jobs_query.offset((page - 1) * per_page).limit(per_page)
        num_pages = int(jobs_count / per_page)
        if jobs_count % per_page > 0:
            num_pages = num_pages + 1
        all_pages = range(0, num_pages)

    jobs = jobs_query.all()
    users_query = User.query.order_by(User.username)

    jobtypes_query = JobType.query

    tags_by_job_query = db.session.query(JobTagAssociation.c.job_id, Tag.tag).\
        join(Tag, JobTagAssociation.c.tag_id==Tag.id).all()
    tags_by_job_id = {}
    for association in tags_by_job_query:
        if association[0] not in tags_by_job_id:
            tags_by_job_id[association[0]] = [association[1]]
        else:
            tags_by_job_id[association[0]] += [association[1]]

    jobqueues = JobQueue.query.all()

    available_priorities = db.session.query(distinct(Job.priority)).all()
    available_priorities = set(x[0] for x in available_priorities)

    filters_and_order = filters.copy()
    filters_and_order.update({"order_by": order_by, "order_dir": order_dir})
    filters_and_order_wo_pagination = filters_and_order.copy()
    del filters_and_order_wo_pagination["per_page"]
    del filters_and_order_wo_pagination["page"]
    return render_template("pyfarm/user_interface/jobs.html",
                           jobs=jobs, filters=filters, order_by=order_by,
                           order_dir=order_dir,
                           order={"order_by": order_by, "order_dir": order_dir},
                           no_state_filters=no_state_filters, users=users_query,
                           filters_and_order=filters_and_order,
                           jobtypes=jobtypes_query,
                           tags_by_job_id=tags_by_job_id, jobs_count=jobs_count,
                           all_pages=all_pages, num_pages=num_pages,
                           filters_and_order_wo_pagination=\
                               filters_and_order_wo_pagination,
                           jobqueues=jobqueues,
                           queued_jobs_count=queued_jobs_count,
                           running_jobs_count=running_jobs_count,
                           failed_jobs_count=failed_jobs_count,
                           done_jobs_count=done_jobs_count,
                           priorities=available_priorities)

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

    users_query = User.query.filter(User.email != None)

    latest_jobtype_version = db.session.query(JobTypeVersion.version).filter_by(
            jobtype=job.jobtype_version.jobtype).\
                order_by(desc(JobTypeVersion.version)).first()

    return render_template("pyfarm/user_interface/job.html", job=job,
                           tasks=tasks, first_task=first_task,
                           last_task=last_task, queues=jobqueues,
                           users=users_query,
                           latest_jobtype_version=latest_jobtype_version[0],
                           now=datetime.utcnow())

def delete_single_job(job_id):
    job = Job.query.filter_by(id=job_id).first()
    if not job:
        return (render_template(
                    "pyfarm/error.html", error="Job %s not found" % job_id),
                NOT_FOUND)

    job.to_be_deleted = True
    db.session.add(job)

    child_job_ids = []
    for child in job.children:
        child.to_be_deleted = True
        child_job_ids.append(child.id)
        db.session.add(child)

    db.session.commit()

    for id_ in child_job_ids + [job_id]:
        logger.info("Marking job %s for deletion", id_)
        delete_job.delay(id_)

    flash("Job %s will be deleted." % job.title)

    if "next" in request.args:
        return redirect(request.args.get("next"), SEE_OTHER)
    else:
        return redirect(url_for("jobs_index_ui"), SEE_OTHER)


def delete_multiple_jobs():
    job_ids = request.form.getlist("job_id")

    job_ids_to_delete = []
    for job_id in job_ids:
        job = Job.query.filter_by(id=job_id).first()
        if not job:
            return (render_template(
                        "pyfarm/error.html", error="Job %s not found" % job_id),
                    NOT_FOUND)

        job.to_be_deleted = True
        db.session.add(job)
        job_ids_to_delete.append(job.id)

        for child in job.children:
            child.to_be_deleted = True
            job_ids_to_delete.append(child.id)
            db.session.add(child)

    db.session.commit()

    for id_ in job_ids_to_delete:
        logger.info("Marking job %s for deletion", id_)
        delete_job.delay(id_)

    flash("Selected jobs will be deleted.")

    if "next" in request.args:
        return redirect(request.args.get("next"), SEE_OTHER)
    else:
        return redirect(url_for("jobs_index_ui"), SEE_OTHER)

def rerun_single_job(job_id):
    job = Job.query.filter_by(id=job_id).first()
    if not job:
        return (render_template(
                    "pyfarm/error.html", error="Job %s not found" % job_id),
                NOT_FOUND)

    job.rerun()
    db.session.commit()
    assign_tasks.delay()

    flash("Job %s will be run again." % job.title)

    if "next" in request.args:
        return redirect(request.args.get("next"), SEE_OTHER)
    else:
        return redirect(url_for("jobs_index_ui"), SEE_OTHER)

def rerun_multiple_jobs():
    job_ids = request.form.getlist("job_id")

    for job_id in job_ids:
        job = Job.query.filter_by(id=job_id).first()
        if not job:
            return (render_template(
                        "pyfarm/error.html", error="Job %s not found" % job_id),
                    NOT_FOUND)
        job.rerun()

    db.session.commit()
    assign_tasks.delay()

    flash("Selected jobs will be run again.")

    if "next" in request.args:
        return redirect(request.args.get("next"), SEE_OTHER)
    else:
        return redirect(url_for("jobs_index_ui"), SEE_OTHER)

def rerun_failed_in_job(job_id):
    job = Job.query.filter_by(id=job_id).first()
    if not job:
        return (render_template(
                    "pyfarm/error.html", error="Job %s not found" % job_id),
                NOT_FOUND)

    job.rerun_failed()
    db.session.commit()

    assign_tasks.delay()

    flash("Failed tasks in job %s will be run again." % job.title)

    if "next" in request.args:
        return redirect(request.args.get("next"), SEE_OTHER)
    else:
        return redirect(url_for("jobs_index_ui"), SEE_OTHER)

def rerun_failed_in_multiple_jobs():
    job_ids = request.form.getlist("job_id")

    for job_id in job_ids:
        job = Job.query.filter_by(id=job_id).first()
        if not job:
            return (render_template(
                        "pyfarm/error.html", error="Job %s not found" % job_id),
                    NOT_FOUND)

        job.rerun_failed()
        db.session.commit()

    assign_tasks.delay()

    flash("Failed tasks in selected jobs will be run again.")

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

    job.state = WorkState.PAUSED
    db.session.add(job)
    db.session.commit()

    for task in job.tasks:
        if task.state == WorkState.RUNNING:
            stop_task.delay(task.id)

    assign_tasks.delay()

    flash("Job %s will be paused." % job.title)

    if "next" in request.args:
        return redirect(request.args.get("next"), SEE_OTHER)
    else:
        return redirect(url_for("jobs_index_ui"), SEE_OTHER)

def pause_multiple_jobs():
    job_ids = request.form.getlist("job_id")

    task_ids_to_stop = []
    for job_id in job_ids:
        job = Job.query.filter_by(id=job_id).first()
        if not job:
            return (render_template(
                        "pyfarm/error.html", error="Job %s not found" % job_id),
                    NOT_FOUND)

        for task in job.tasks:
            if task.state == WorkState.RUNNING:
                task_ids_to_stop.append(task.id)

        job.state = WorkState.PAUSED
        db.session.add(job)

    db.session.commit()

    for task_id in task_ids_to_stop:
        stop_task.delay(task_id)
    assign_tasks.delay()

    flash("Selected jobs will be paused.")

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
    job.update_state()
    db.session.add(job)
    db.session.commit()

    assign_tasks.delay()

    flash("Job %s is unpaused." % job.title)

    if "next" in request.args:
        return redirect(request.args.get("next"), SEE_OTHER)
    else:
        return redirect(url_for("jobs_index_ui"), SEE_OTHER)

def unpause_multiple_jobs():
    job_ids = request.form.getlist("job_id")

    for job_id in job_ids:
        job = Job.query.filter_by(id=job_id).first()
        if not job:
            return (render_template(
                        "pyfarm/error.html", error="Job %s not found" % job_id),
                    NOT_FOUND)

        job.state = None
        job.update_state()
        db.session.add(job)

    db.session.commit()

    assign_tasks.delay()

    flash("Selected jobs are unpaused")

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
    job.requeue = int(request.form['requeue'])
    if request.form['minimum_ram']:
        job.ram = int(request.form['minimum_ram'])
    else:
        job.ram = None

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

def move_multiple_jobs():
    job_ids = request.form.getlist("job_id")

    queue_id = int(request.form['queue'])
    queue = JobQueue.query.filter_by(id=queue_id).first()
    if not queue:
        return (render_template(
            "pyfarm/error.html", error="Queue %s not found" % queue_id),
        NOT_FOUND)

    for job_id in job_ids:
        job = Job.query.filter_by(id=job_id).first()
        if not job:
            return (render_template(
                        "pyfarm/error.html", error="Job %s not found" % job_id),
                    NOT_FOUND)

        job.queue = queue
        db.session.add(job)

    db.session.commit()

    flash("Selected jobs have been moved to queue %s" % queue.path())

    if "next" in request.args:
        return redirect(request.args.get("next"), SEE_OTHER)
    else:
        return redirect(url_for("jobs_index_ui"), SEE_OTHER)

def set_prio_weight_on_jobs():
    job_ids = request.form.getlist("job_id")

    prio = int(request.form["prio"])
    weight = int(request.form["weight"])

    for job_id in job_ids:
        job = Job.query.filter_by(id=job_id).first()
        if not job:
            return (render_template(
                        "pyfarm/error.html", error="Job %s not found" % job_id),
                    NOT_FOUND)

        job.priority = prio
        job.weight = weight
        db.session.add(job)

    db.session.commit()

    flash("Priority and weight on selected jobs have been set")

    if "next" in request.args:
        return redirect(request.args.get("next"), SEE_OTHER)
    else:
        return redirect(url_for("jobs_index_ui"), SEE_OTHER)

def alter_autodeletion_for_job(job_id):
    job = Job.query.filter_by(id=job_id).first()
    if not job:
        return (render_template(
                    "pyfarm/error.html", error="Job %s not found" % job_id),
                NOT_FOUND)

    if request.form['autodelete_time']:
        job.autodelete_time = int(request.form['autodelete_time'])

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

def add_notified_user_to_job(job_id):
    job = Job.query.filter_by(id=job_id).first()
    if not job:
        return (render_template(
                    "pyfarm/error.html", error="Job %s not found" % job_id),
                NOT_FOUND)

    user_id = request.form['user']
    user = User.query.filter_by(id=user_id).first()
    if not user:
        return (render_template(
                    "pyfarm/error.html", error="User %s not found" % user_id),
                NOT_FOUND)

    notified_user = JobNotifiedUser.query.filter_by(user=user, job=job).first()
    if not notified_user:
        notified_user = JobNotifiedUser(user=user, job=job)
        notified_user.on_success = False
        notified_user.on_failure = False

    notified_user.on_success = (("on_success" in request.form and
                                 request.form["on_success"] == "true") or
                                notified_user.on_success)
    notified_user.on_failure = (("on_failure" in request.form and
                                 request.form["on_failure"] == "true") or
                                notified_user.on_failure)
    notified_user.on_deletion = (("on_deletion" in request.form and
                                  request.form["on_deletion"] == "true") or
                                 notified_user.on_deletion)

    db.session.add(notified_user)
    db.session.commit()

    flash("User %s has been added as notified user to job %s." %
          (user.username, job.title))

    return redirect(url_for("single_job_ui", job_id=job.id), SEE_OTHER)

def remove_notified_user_from_job(job_id, user_id):
    job = Job.query.filter_by(id=job_id).first()
    if not job:
        return (render_template(
                    "pyfarm/error.html", error="Job %s not found" % job_id),
                NOT_FOUND)

    user = User.query.filter_by(id=user_id).first()
    if not user:
        return (render_template(
                    "pyfarm/error.html", error="User %s not found" % user_id),
                NOT_FOUND)

    notified_user = JobNotifiedUser.query.filter_by(user=user, job=job).first()
    if notified_user:
        db.session.delete(notified_user)
    db.session.commit()

    flash("User %s has been removed from notified users for job %s." %
          (user.username, job.title))

    return redirect(url_for("single_job_ui", job_id=job.id), SEE_OTHER)

def upgrade_job_to_latest_jobtype_version(job_id):
    job = Job.query.filter_by(id=job_id).first()
    if not job:
        return (render_template(
                    "pyfarm/error.html", error="Job %s not found" % job_id),
                NOT_FOUND)

    latest_version = JobTypeVersion.query.filter_by(
            jobtype=job.jobtype_version.jobtype).\
                order_by(desc(JobTypeVersion.version)).first()
    if not latest_version:
        return (render_template(
            "pyfarm/error.html", error="Jobtype %s has no versions" %
            job.jobtype_id), INTERNAL_SERVER_ERROR)

    job.jobtype_version = latest_version

    db.session.add(job)
    db.session.commit()

    flash("Job %s has been upgraded to jobtype %s, version %s." %
          (job.title, job.jobtype_version.jobtype.name,
           job.jobtype_version.version))

    return redirect(url_for("single_job_ui", job_id=job.id), SEE_OTHER)

def update_tags_in_job(job_id):
    job = Job.query.filter_by(id=job_id).first()
    if not job:
        return (render_template(
                    "pyfarm/error.html", error="Job %s not found" % job_id),
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
                    "still running"),
                BAD_REQUEST)

    task.state = None
    task.agent = None
    task.failures = 0

    if Job.state != WorkState.RUNNING:
        job.state = None
    job.completion_notify_sent = False

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
