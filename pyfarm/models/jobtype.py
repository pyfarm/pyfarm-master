# No shebang line, this module is meant to be imported
#
# Copyright 2013 Oliver Palmer
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
Job Type Models
===============

Models and objects dedicated to handling information which is specific
to an individual job.  See :mod:`pyfarm.models.job` for more the more
general implementation.
"""

import ast
from hashlib import sha1
from textwrap import dedent

from sqlalchemy import event
from sqlalchemy.orm import validates

from pyfarm.core.config import read_env_int, read_env_bool, read_env
from pyfarm.core.logger import getLogger
from pyfarm.master.application import db
from pyfarm.models.core.cfg import (
    TABLE_JOB_TYPE, MAX_JOBTYPE_LENGTH, SHA1_ASCII_LENGTH)
from pyfarm.models.core.mixins import UtilityMixins, ReprMixin
from pyfarm.models.core.types import id_column, IDTypeWork


__all__ = ("JobType", )

JOBTYPE_BASECLASS = read_env("PYFARM_JOBTYPE_SUBCLASSES_BASE_CLASS", "JobType")

logger = getLogger("models.jobtype")


class JobType(db.Model, UtilityMixins, ReprMixin):
    """
    Stores the unique information necessary to execute a task
    """
    __tablename__ = TABLE_JOB_TYPE
    REPR_COLUMNS = (
        "id", "name", "classname", "max_batch", "batch_contiguous")

    id = id_column(IDTypeWork)
    name = db.Column(db.String(MAX_JOBTYPE_LENGTH), nullable=False,
                     doc=dedent("""
                     The name of the job type.  This can be either a human
                     readable name or the name of the job type class
                     itself."""))
    description = db.Column(db.Text, nullable=True,
                            doc=dedent("""
                            Human readable description of the job type.  This
                            field is not required and is not directly relied
                            upon anywhere."""))
    max_batch = db.Column(db.Integer,
                          default=read_env_int(
                              "JOBTYPE_DEFAULT_MAX_BATCH",
                              read_env_int("PYFARM_QUEUE_MAX_BATCH", 1)),
                          doc=dedent("""
                          When the queue runs this is the maximum number of
                          tasks that the queue can select to assign to a single
                          agent."""))
    batch_contiguous = db.Column(db.Boolean,
                                 default=read_env_bool(
                                     "JOBTYPE_DEFAULT_BATCH_CONTIGUOUS", True),
                                 doc=dedent("""
                                 If True then the queue will be forced to batch
                                 numerically contiguous tasks only for this
                                 job type.  For example if True it would batch
                                 frames 1, 2, 3, 4 together but not 2, 4, 6,
                                 8.  If this column is False however the queue
                                 will batch non-contiguous tasks too."""))
    classname = db.Column(db.String(MAX_JOBTYPE_LENGTH), nullable=True,
                          doc=dedent("""
                          The name of the job class contained within the file
                          being loaded.  This field may be null but when it's
                          not provided :attr:`name` will be used instead."""))
    code = db.Column(db.UnicodeText, nullable=False,
                     doc=dedent("""
                     General field containing the 'code' to retrieve the job
                     type.  See below for information on what this field will
                     contain depending on how the job will be loaded."""))
    sha1 = db.Column(db.String(SHA1_ASCII_LENGTH), nullable=False,
                     doc=dedent("""
                     Contains the SHA1 hash of the source code in the ``code``
                     column.  This value will automatically be updated whenever
                     ``code`` is set."""))
    jobs = db.relationship("Job", backref="job_type", lazy="dynamic",
                           doc=dedent("""
                           Relationship between this jobtype and
                           :class:`.Job` objects."""))

    @validates("max_batch")
    def validate_max_batch(self, key, value):
        if isinstance(value, int) and not value >= 1:
            raise ValueError("max_batch must be greater than or equal to 1")

        return value


def compute_sha1(code):
    """returns a sha1 for the given source code"""
    try:
        return sha1(code).hexdigest()
    except TypeError:  # required for Python 3
        return sha1(code.encode("utf-8")).hexdigest()


def set_sha1_from_code(mapper, connection, jobtype):
    """
    ensure that the sha1 matches the code's sha1 before
    insertion to prevent an accidental or malicious mismatch
    """
    jobtype.sha1 = compute_sha1(jobtype.code)


def code_set_event(target, value, oldvalue, initiator):
    """set the sha1 whenever the code column is set"""
    target.sha1 = compute_sha1(value)


event.listen(JobType, "before_insert", set_sha1_from_code)
event.listen(JobType.code, "set", code_set_event)
