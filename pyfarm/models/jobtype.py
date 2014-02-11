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

from pyfarm.core.config import read_env_int, read_env_bool
from pyfarm.core.logger import getLogger
from pyfarm.master.application import db
from pyfarm.models.core.cfg import (
    TABLE_JOB_TYPE, MAX_JOBTYPE_LENGTH, SHA1_ASCII_LENGTH)
from pyfarm.models.core.mixins import UtilityMixins, ReprMixin
from pyfarm.models.core.types import id_column, IDTypeWork


__all__ = ("JobType", )

JOBTYPE_BASECLASS = "JobType"

logger = getLogger("models.jobtype")


class JobType(db.Model, UtilityMixins, ReprMixin):
    """
    Stores the unique information necessary to execute a task
    """
    __tablename__ = TABLE_JOB_TYPE
    REPR_COLUMNS = (
        "id", "name", "classname", "max_batch",
        "batch_contiguous", "batch_non_contiguous")

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


def jobtype_before_insert(mapper, connection, jobtype):
    # TODO: this parsing is extremely basic and needs some expansion
    # If jobtype's says to download a file then we must
    # be sure it's valid.  If we don't, you could probably tip over
    # the master(s) under the load of rapidly failing tasks due to
    # any of the following:
    #   * job class name does not exist in the code (...)
    #   * invalid Python code (SyntaxError)
    #   * invalid parent class (jobtype must subclass JobType)
    try:
        parsed = ast.parse(jobtype.code)

        if jobtype.classname is None:
            raise ValueError("required field `classname` not set")

        # NOTE: some coverage is skipped because the final except clause
        # prevents coverage from pulling the correct lines in
        for node in ast.walk(parsed):
            if not isinstance(node, ast.ClassDef):
                continue

            # found the class, make sure it has the proper parent class
            elif node.name == jobtype.classname:
                if JOBTYPE_BASECLASS not in set(base.id for base in node.bases):
                    error_args = (jobtype.classname, JOBTYPE_BASECLASS)
                    raise SyntaxError("%s is not a subclass of %s" % error_args)
                else:  # pragma: no cover
                    break
        else:  # pragma: no cover
            raise SyntaxError(
                "jobtype class `%s` does not exist" % jobtype.classname)

    except Exception:
        raise


def set_sha1_from_code(mapper, connection, jobtype):
    """
    ensure that the sha1 matches the code's sha1 before
    insertion to prevent an accidental or malicious mismatch
    """
    try:
        jobtype.sha1 = sha1(jobtype.code).hexdigest()
    except TypeError:
        jobtype.sha1 = sha1(jobtype.code.encode("utf-8")).hexdigest()


event.listen(JobType, "before_insert", jobtype_before_insert)
event.listen(JobType, "before_insert", set_sha1_from_code)
event.listen(JobType, "before_update", set_sha1_from_code)
