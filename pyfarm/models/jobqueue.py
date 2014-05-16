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

"""
Job Queue Model
===============

Model for job queues
"""

from textwrap import dedent

from pyfarm.core.config import read_env_int

from pyfarm.master.application import db
from pyfarm.models.core.cfg import TABLE_JOB_QUEUE, MAX_JOBQUEUE_NAME_LENGTH
from pyfarm.models.core.mixins import UtilityMixins, ReprMixin
from pyfarm.models.core.types import id_column, IDTypeWork


class JobQueue(db.Model, UtilityMixins, ReprMixin):
    """
    Stores information about a job queue. Used for flexible, configurable
    distribution of computing capacity to jobs.
    """
    __tablename__ = TABLE_JOB_QUEUE

    REPR_COLUMNS = ("id", "name")

    id = id_column(IDTypeWork)
    parent_jobqueue_id = db.Column(IDTypeWork,
                                   db.ForeignKey("%s.id" % TABLE_JOB_QUEUE),
                                   nullable=True,
                                   doc="The parent queue of this queue. If "
                                       "NULL, this is a top level queue")
    name = db.Column(db.String(MAX_JOBQUEUE_NAME_LENGTH), nullable=False,
                     unique=True)
    minimum_agents = db.Column(db.Integer, nullable=True,
                          doc=dedent("""
                          The scheduler will try to assign at least this number
                          of agents to jobs in or below this queue as long as it
                          can use them, before any other considerations."""))
    maximum_agents = db.Column(db.Integer, nullable=True,
                          doc=dedent("""
                          The scheduler will never assign more than this number
                          of agents to jobs in or below this queue."""))
    priority = db.Column(db.Integer, nullable=False,
                         default=read_env_int(
                                   "PYFARM_JOBQUEUE_DEFAULT_PRIO", 5),
                         doc=dedent("""
                             The priority of this job queue.
                             The scheduler will not assign any nodes to other
                             job queues or jobs with the same parent and a lower
                             priority as long as this one can still use nodes.
                             Minimum_agents takes precedence over this.
                             """))
    weight = db.Column(db.Integer, nullable=False,
                       default=read_env_int(
                                   "PYFARM_JOBQUEUE_DEFAULT_WEIGHT", 10),
                       doc=dedent("""
                            The weight of this job queue.
                            The scheduler will distribute available agents
                            between jobs and job queues in the same queue
                            in proportion to their weights.
                            """))
    parent = db.relationship("JobQueue",
                              doc="Relationship between this queue its parent")
