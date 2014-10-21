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
    from httplib import NOT_FOUND
except ImportError:  # pragma: no cover
    from http.client import NOT_FOUND

from flask import render_template

from pyfarm.models.task import Task
from pyfarm.models.tasklog import TaskLog, TaskTaskLogAssociation

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
