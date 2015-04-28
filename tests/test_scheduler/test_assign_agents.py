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

import uuid

from pyfarm.master.testutil import BaseTestCase
BaseTestCase.build_environment()

from pyfarm.master.application import db
from pyfarm.models.agent import Agent
from pyfarm.models.jobtype import JobType, JobTypeVersion
from pyfarm.models.job import Job
from pyfarm.models.task import Task
from pyfarm.models.jobqueue import JobQueue
from pyfarm.scheduler.tasks import assign_tasks_to_agent

class TestAssignAgent(BaseTestCase):
    def create_jobtype_version(self):
        jobtype = JobType()
        jobtype.name = "foo"
        jobtype.description = "this is a job type"
        jobtype_version = JobTypeVersion()
        jobtype_version.jobtype = jobtype
        jobtype_version.version = 1
        jobtype_version.classname = "Foobar"
        jobtype_version.code = ("""
            class Foobar(JobType):
                pass""").encode("utf-8")
        db.session.add(jobtype_version)
        db.session.flush()

        return jobtype_version

    def create_queue_with_job(self, name, jobtype_version):
        queue = JobQueue(name=name)
        job = Job(title="Test Job %s" % name, jobtype_version=jobtype_version,
                  queue=queue)

        for i in range(0, 100):
            task = Task(job=job, frame=i)
            db.session.add(task)
        db.session.add(job)
        db.session.flush()

        return queue

    def test_assign_by_weight(self):
        jobtype_version = self.create_jobtype_version()
        high_queue = self.create_queue_with_job("heavyweight", jobtype_version)
        high_queue.weight = 60
        mid_queue = self.create_queue_with_job("mediumweight", jobtype_version)
        mid_queue.weight = 30
        low_queue = self.create_queue_with_job("lightweight", jobtype_version)
        low_queue.weight = 10
        db.session.add_all([high_queue, mid_queue, low_queue])
        db.session.commit()

        agents = []
        for i in range(0, 100):
            agent = Agent(hostname="agent%s" % i, id=uuid.uuid4(), ram=32,
                          free_ram=32, cpus=1, port=50000)
            db.session.add(agent)
            agents.append(agent)
        db.session.commit()

        for agent in agents:
            assign_tasks_to_agent(agent.id)

        self.assertGreaterEqual(high_queue.num_assigned_agents(), 59)
        self.assertLessEqual(high_queue.num_assigned_agents(), 61)

        self.assertGreaterEqual(mid_queue.num_assigned_agents(), 29)
        self.assertLessEqual(mid_queue.num_assigned_agents(), 31)

        self.assertGreaterEqual(low_queue.num_assigned_agents(), 9)
        self.assertLessEqual(low_queue.num_assigned_agents(), 11)

    def test_assign_by_weight_additional_queues(self):
        jobtype_version = self.create_jobtype_version()
        high_queue = self.create_queue_with_job("heavyweight", jobtype_version)
        high_queue.weight = 60
        mid_queue = self.create_queue_with_job("mediumweight", jobtype_version)
        mid_queue.weight = 30
        low_queue = self.create_queue_with_job("lightweight", jobtype_version)
        low_queue.weight = 10
        db.session.add_all([high_queue, mid_queue, low_queue])

        # The presence of additional queues with arbitrary weights should not
        # make any difference if they aren't drawing any agents
        additional_queue1 = JobQueue(name="additional1", weight=10)
        additional_queue2 = JobQueue(name="additional2", weight=10)
        additional_queue3 = JobQueue(name="additional3", weight=10)

        db.session.commit()

        agents = []
        for i in range(0, 100):
            agent = Agent(hostname="agent%s" % i, id=uuid.uuid4(), ram=32,
                          free_ram=32, cpus=1, port=50000)
            db.session.add(agent)
            agents.append(agent)
        db.session.commit()

        for agent in agents:
            assign_tasks_to_agent(agent.id)

        self.assertGreaterEqual(high_queue.num_assigned_agents(), 59)
        self.assertLessEqual(high_queue.num_assigned_agents(), 61)

        self.assertGreaterEqual(mid_queue.num_assigned_agents(), 29)
        self.assertLessEqual(mid_queue.num_assigned_agents(), 31)

        self.assertGreaterEqual(low_queue.num_assigned_agents(), 9)
        self.assertLessEqual(low_queue.num_assigned_agents(), 11)
