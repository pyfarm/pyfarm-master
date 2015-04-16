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

from flask import render_template

from sqlalchemy import func, or_, distinct

from pyfarm.core.enums import WorkState, AgentState

from pyfarm.master.application import db
from pyfarm.models.job import Job
from pyfarm.models.jobtype import JobType, JobTypeVersion
from pyfarm.models.task import Task
from pyfarm.models.agent import Agent
from pyfarm.models.jobgroup import JobGroup


def jobgroups():
    agent_count_query = db.session.query(
        Job.job_group_id,
        func.count(distinct(Task.agent_id)).label('agent_count')).\
            join(Task, Task.job_id == Job.id).\
            filter(Job.job_group_id != None).\
            filter(Task.agent_id != None, or_(Task.state == None,
                                              Task.state == WorkState.RUNNING),
                   Task.agent.has(Agent.state != AgentState.OFFLINE)).\
                group_by(Job.job_group_id).subquery()
    submit_time_query = db.session.query(
        Job.job_group_id,
        func.min(Job.time_submitted).label('time_submitted')).\
            group_by(Job.job_group_id).subquery()

    jobgroups_query = db.session.query(JobGroup,
                                       JobType.name.label('main_jobtype_name'),
                                       func.coalesce(
                                           agent_count_query.c.agent_count,
                                           0).label('agent_count'),
                                       submit_time_query.c.time_submitted.\
                                           label('time_submitted'),
                                       ).\
        join(JobType, JobGroup.main_jobtype_id == JobType.id).\
        outerjoin(agent_count_query,
                  JobGroup.id == agent_count_query.c.job_group_id).\
        outerjoin(submit_time_query,
                  JobGroup.id == submit_time_query.c.job_group_id)

    exists_query = jobgroups_query.filter(Job.job_group_id == JobGroup.id).\
        exists()

    jobs_query = db.session.query(Job.job_group_id,
                                  Job,
                                  JobType.name.label('jobtype_name')).\
        join(JobTypeVersion, Job.jobtype_version_id == JobTypeVersion.id).\
        join(JobType, JobTypeVersion.jobtype_id == JobType.id).\
        filter(exists_query)

    jobs_by_group = {}
    for group_id, job, jobtype_name in jobs_query:
        if group_id in jobs_by_group:
            jobs_by_group[group_id].append(job)
        else:
            jobs_by_group[group_id] = [(job, jobtype_name)]

    return render_template("pyfarm/user_interface/jobgroups.html",
                           jobgroups=jobgroups_query,
                           jobs_by_group=jobs_by_group)
