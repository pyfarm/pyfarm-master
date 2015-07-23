# No shebang line, this module is meant to be imported
#
# Copyright 2015 Ambient Entertainment GmbH & Co. KG
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

import json
from calendar import timegm
from datetime import timedelta

from flask import render_template, request

from sqlalchemy import or_

from pyfarm.models.jobqueue import JobQueue
from pyfarm.models.statistics.task_event_count import TaskEventCount
from pyfarm.master.config import config
from pyfarm.master.application import db


class SampleSum(object):
    def __init__(self, first_sample, last_sum=None):
        self.time_start = first_sample.time_start

        self.num_new = first_sample.num_new
        self.num_deleted = first_sample.num_deleted
        self.num_restarted = first_sample.num_restarted
        self.num_failed = first_sample.num_failed
        self.num_done = first_sample.num_done

        self.avg_queued_by_queue = (
            last_sum.avg_queued_by_queue if last_sum else {})
        self.avg_queued_by_queue[first_sample.job_queue_id] =\
            first_sample.avg_queued

        self.avg_running_by_queue = (
            last_sum.avg_running_by_queue if last_sum else {})
        self.avg_running_by_queue[first_sample.job_queue_id] =\
            first_sample.avg_running

        self.avg_done_by_queue = (
            last_sum.avg_done_by_queue if last_sum else {})
        self.avg_done_by_queue[first_sample.job_queue_id] =\
            first_sample.avg_done

        self.avg_failed_by_queue = (
            last_sum.avg_failed_by_queue if last_sum else {})
        self.avg_failed_by_queue[first_sample.job_queue_id] =\
            first_sample.avg_failed

    def add_sample(self, sample):
        self.num_new += sample.num_new
        self.num_deleted += sample.num_deleted
        self.num_restarted + sample.num_restarted
        self.num_failed += sample.num_failed
        self.num_done += sample.num_done

        self.avg_queued_by_queue[sample.job_queue_id] = sample.avg_queued
        self.avg_running_by_queue[sample.job_queue_id] = sample.avg_running
        self.avg_done_by_queue[sample.job_queue_id] = sample.avg_done
        self.avg_failed_by_queue[sample.job_queue_id] = sample.avg_failed

    def avg_queued(self):
        return sum(self.avg_queued_by_queue.values())

    def avg_running(self):
        return sum(self.avg_running_by_queue.values())

    def avg_done(self):
        return sum(self.avg_done_by_queue.values())

    def avg_failed(self):
        return sum(self.avg_failed_by_queue.values())


def task_events():
    consolidate_interval = timedelta(**config.get(
        "task_event_count_consolidate_interval"))

    task_event_count_query = TaskEventCount.query.order_by(
        TaskEventCount.time_start)

    jobqueue_ids = []
    no_queue = ("no_queue" in request.args and
        request.args["no_queue"].lower() == "true")
    if "queue" in request.args or no_queue:
        jobqueue_ids = request.args.getlist("queue")
        jobqueue_ids = [int(x) for x in jobqueue_ids]
        if no_queue:
            task_event_count_query = task_event_count_query.filter(or_(
                TaskEventCount.job_queue_id.in_(jobqueue_ids),
                TaskEventCount.job_queue_id == None))
        else:
            task_event_count_query = task_event_count_query.filter(
                TaskEventCount.job_queue_id.in_(jobqueue_ids))

    tasks_new = []
    tasks_deleted = []
    tasks_restarted = []
    tasks_failed = []
    tasks_done = []
    avg_queued = []
    avg_running = []
    avg_done = []
    avg_failed = []
    open_sample = None
    for sample in task_event_count_query:
        if not open_sample:
            open_sample = SampleSum(sample)
        elif (sample.time_start >= open_sample.time_start and
                sample.time_start <
                (open_sample.time_start + consolidate_interval)):
            open_sample.add_sample(sample)
        else:
            timestamp = timegm(open_sample.time_start.utctimetuple())
            tasks_new.append([timestamp, open_sample.num_new])
            tasks_deleted.append([timestamp, -open_sample.num_deleted])
            tasks_restarted.append([timestamp, open_sample.num_restarted])
            tasks_failed.append([timestamp, -open_sample.num_failed])
            tasks_done.append([timestamp, -open_sample.num_done])
            avg_queued.append([timestamp, open_sample.avg_queued()])
            avg_running.append([timestamp, open_sample.avg_running()])
            avg_done.append([timestamp, open_sample.avg_done()])
            avg_failed.append([timestamp, open_sample.avg_failed()])

            open_sample = SampleSum(sample, open_sample)

    if open_sample:
        timestamp = timegm(open_sample.time_start.utctimetuple())
        tasks_new.append([timestamp, open_sample.num_new])
        tasks_deleted.append([timestamp, -open_sample.num_deleted])
        tasks_restarted.append([timestamp, open_sample.num_restarted])
        tasks_failed.append([timestamp, -open_sample.num_failed])
        tasks_done.append([timestamp, -open_sample.num_done])
        avg_queued.append([timestamp, open_sample.avg_queued()])
        avg_running.append([timestamp, open_sample.avg_running()])
        avg_done.append([timestamp, open_sample.avg_done()])
        avg_failed.append([timestamp, open_sample.avg_failed()])

    jobqueues = JobQueue.query.order_by(JobQueue.fullpath).all()

    return render_template(
        "pyfarm/statistics/task_events.html",
        tasks_new_json=json.dumps(tasks_new),
        tasks_deleted_json=json.dumps(tasks_deleted),
        tasks_restarted_json=json.dumps(tasks_restarted),
        tasks_failed_json=json.dumps(tasks_failed),
        tasks_done_json=json.dumps(tasks_done),
        avg_queued_json=json.dumps(avg_queued),
        avg_running_json=json.dumps(avg_running),
        avg_done_json=json.dumps(avg_done),
        avg_failed_json=json.dumps(avg_failed),
        no_queue=no_queue,
        jobqueue_ids=jobqueue_ids,
        jobqueues=jobqueues)
