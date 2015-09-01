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
from datetime import timedelta, datetime

from flask import render_template, request

from sqlalchemy import or_

from pyfarm.core.logger import getLogger
from pyfarm.models.jobqueue import JobQueue
from pyfarm.models.statistics.task_event_count import TaskEventCount
from pyfarm.models.statistics.task_count import TaskCount
from pyfarm.master.config import config
from pyfarm.master.application import db

logger = getLogger("ui.task_events")


class TotalsAverage(object):
    def __init__(self, first_sample, last_sum=None):
        self.time_start = first_sample.counted_time
        self.num_samples_by_queue = {first_sample.job_queue_id: 1}

        self.avg_queued_by_queue = (
            last_sum.avg_queued_by_queue if last_sum else {})
        self.avg_queued_by_queue[first_sample.job_queue_id] =\
            first_sample.total_queued

        self.avg_running_by_queue = (
            last_sum.avg_running_by_queue if last_sum else {})
        self.avg_running_by_queue[first_sample.job_queue_id] =\
            first_sample.total_running

        self.avg_done_by_queue = (
            last_sum.avg_done_by_queue if last_sum else {})
        self.avg_done_by_queue[first_sample.job_queue_id] =\
            first_sample.total_done

        self.avg_failed_by_queue = (
            last_sum.avg_failed_by_queue if last_sum else {})
        self.avg_failed_by_queue[first_sample.job_queue_id] =\
            first_sample.total_failed

    def add_sample(self, sample):
        self.num_samples_by_queue[sample.job_queue_id] =\
            self.num_samples_by_queue.get(sample.job_queue_id, 0) + 1
        num_samples = self.num_samples_by_queue[sample.job_queue_id]

        self.avg_queued_by_queue[sample.job_queue_id] =\
            (float(sample.total_queued) / num_samples +
             ((float(num_samples) - 1) / num_samples) *
                self.avg_queued_by_queue.get(sample.job_queue_id, 0.0))

        self.avg_running_by_queue[sample.job_queue_id] =\
            (float(sample.total_running) / num_samples +
             ((float(num_samples) - 1) / num_samples) *
                self.avg_running_by_queue.get(sample.job_queue_id, 0.0))

        self.avg_done_by_queue[sample.job_queue_id] =\
            (float(sample.total_done) / num_samples +
             ((float(num_samples) - 1) / num_samples) *
                self.avg_done_by_queue.get(sample.job_queue_id, 0.0))

        self.avg_failed_by_queue[sample.job_queue_id] =\
            (float(sample.total_failed) / num_samples +
             ((float(num_samples) - 1) / num_samples) *
                self.avg_failed_by_queue.get(sample.job_queue_id, 0.0))

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

    minutes_resolution = int(consolidate_interval.total_seconds() / 60)
    if "minutes_resolution" in request.args:
        minutes_resolution = int(request.args.get("minutes_resolution"))
        consolidate_interval = timedelta(minutes=minutes_resolution)

    days_back = int(request.args.get("days_back", 7))
    time_back = timedelta(days=days_back)

    task_event_count_query = TaskEventCount.query.order_by(
        TaskEventCount.time_start).filter(
            TaskEventCount.time_start > datetime.utcnow() - time_back)

    task_count_query = TaskCount.query.order_by(
        TaskCount.counted_time).filter(
            TaskCount.counted_time > datetime.utcnow() - time_back)

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
            task_count_query = task_count_query.filter(or_(
                TaskCount.job_queue_id.in_(jobqueue_ids),
                TaskCount.job_queue_id == None))
        else:
            task_event_count_query = task_event_count_query.filter(
                TaskEventCount.job_queue_id.in_(jobqueue_ids))
            task_count_query = task_count_query.filter(
                TaskCount.job_queue_id.in_(jobqueue_ids))

    tasks_new = []
    tasks_deleted = []
    tasks_restarted = []
    tasks_failed = []
    tasks_done = []
    current_period_start = None
    for sample in task_event_count_query:
        if not current_period_start:
            current_period_start = sample.time_start
            timestamp = timegm(current_period_start.utctimetuple())
            tasks_new.append([timestamp, sample.num_new])
            tasks_deleted.append([timestamp, -sample.num_deleted])
            tasks_restarted.append([timestamp, sample.num_restarted])
            tasks_failed.append([timestamp, -sample.num_failed])
            tasks_done.append([timestamp, -sample.num_done])
        elif (sample.time_start <
              (current_period_start + consolidate_interval)):
            tasks_new[-1][-1] += sample.num_new
            tasks_deleted[-1][-1] -= sample.num_deleted
            tasks_restarted[-1][-1] += sample.num_restarted
            tasks_failed[-1][-1] -= sample.num_failed
            tasks_done[-1][-1] -= sample.num_done
        else:
            while (sample.time_start >=
                   (current_period_start + consolidate_interval)):
                current_period_start += consolidate_interval
                timestamp = timegm(current_period_start.utctimetuple())
                tasks_new.append([timestamp, 0])
                tasks_deleted.append([timestamp, 0])
                tasks_restarted.append([timestamp, 0])
                tasks_failed.append([timestamp, 0])
                tasks_done.append([timestamp, 0])

            tasks_new[-1][-1] += sample.num_new
            tasks_deleted[-1][-1] -= sample.num_deleted
            tasks_restarted[-1][-1] += sample.num_restarted
            tasks_failed[-1][-1] -= sample.num_failed
            tasks_done[-1][-1] -= sample.num_done

    total_queued = []
    total_running = []
    total_done = []
    total_failed = []
    current_average = None
    for sample in task_count_query:
        if not current_average:
            current_average = TotalsAverage(sample)
        elif (sample.counted_time <
              (current_average.time_start + consolidate_interval)):
            current_average.add_sample(sample)
        else:
            timestamp = timegm(current_average.time_start.utctimetuple())
            total_queued.append([timestamp, current_average.avg_queued()])
            total_running.append([timestamp, current_average.avg_running()])
            total_done.append([timestamp, current_average.avg_done()])
            total_failed.append([timestamp, current_average.avg_failed()])
            current_average = TotalsAverage(sample, current_average)

    if current_average:
        timestamp = timegm(current_average.time_start.utctimetuple())
        total_queued.append([timestamp, current_average.avg_queued()])
        total_running.append([timestamp, current_average.avg_running()])
        total_done.append([timestamp, current_average.avg_done()])
        total_failed.append([timestamp, current_average.avg_failed()])

    jobqueues = JobQueue.query.order_by(JobQueue.fullpath).all()

    return render_template(
        "pyfarm/statistics/task_events.html",
        tasks_new_json=json.dumps(tasks_new),
        tasks_deleted_json=json.dumps(tasks_deleted),
        tasks_restarted_json=json.dumps(tasks_restarted),
        tasks_failed_json=json.dumps(tasks_failed),
        tasks_done_json=json.dumps(tasks_done),
        total_queued_json=json.dumps(total_queued),
        total_running_json=json.dumps(total_running),
        total_done_json=json.dumps(total_done),
        total_failed_json=json.dumps(total_failed),
        no_queue=no_queue,
        jobqueue_ids=jobqueue_ids,
        jobqueues=jobqueues,
        minutes_resolution=minutes_resolution,
        days_back=days_back)
