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

from os.path import join, realpath, isfile

try:
    from httplib import NOT_FOUND, TEMPORARY_REDIRECT, BAD_REQUEST
except ImportError:  # pragma: no cover
    from http.client import NOT_FOUND, TEMPORARY_REDIRECT, BAD_REQUEST

from flask import render_template, redirect

from pyfarm.models.task import Task
from pyfarm.models.tasklog import TaskLog, TaskTaskLogAssociation
from pyfarm.master.config import config


LOGFILES_DIR = config.get("tasklogs_dir")

def logs_in_task(job_id, task_id):
    task = Task.query.filter_by(id=task_id, job_id=job_id).first()
    if not task:
        return (render_template(
            "pyfarm/error.html", error="Task %s not found" % task_id),
            NOT_FOUND)

    association_objects_query = TaskTaskLogAssociation.query.filter(
            TaskTaskLogAssociation.task == task)

    attempts = dict()
    for item in association_objects_query:
        if item.attempt in attempts:
            attempts[item.attempt] += [item]
        else:
            attempts[item.attempt] = [item]

    return render_template("pyfarm/user_interface/logs_in_task.html",
                           attempts=attempts, task=task)

def single_tasklog(job_id, task_id, log_id):
    task = Task.query.filter_by(id=task_id, job_id=job_id).first()
    if not task:
        return (render_template(
            "pyfarm/error.html", error="Task %s not found" % task_id),
            NOT_FOUND)

    association_object = TaskTaskLogAssociation.query.filter(
            TaskTaskLogAssociation.task == task,
            TaskTaskLogAssociation.log.has(
                TaskLog.identifier == log_id)).first()

    if not association_object:
        return (render_template(
            "pyfarm/error.html", error="Tasklog %s not found" % log_id),
            NOT_FOUND)

    log = association_object.log

    path = realpath(join(LOGFILES_DIR, log_id))
    if not realpath(path).startswith(LOGFILES_DIR):
        return jsonify(error="Identifier is not acceptable"), BAD_REQUEST

    if isfile(path) or isfile(path + ".gz"):
        return render_template("pyfarm/user_interface/tasklog.html",
                           job=task.job, task=task, log=log,
                           attempt=association_object.attempt)
    else:
        agent = log.agent
        if not agent:
            return (render_template(
                "pyfarm/error.html", error="Task log %s not found on master "
                "and agent unknown." % log_id), NOT_FOUND)
        return redirect(agent.ui_url() + "/task_logs/" + log_id,
                        TEMPORARY_REDIRECT)
