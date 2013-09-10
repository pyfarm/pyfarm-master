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
from textwrap import dedent
from sqlalchemy import event
from sqlalchemy.orm import validates
from pyfarm.core.enums import JobTypeLoadMode
from pyfarm.models.core.types import IDColumn, IDTypeWork
from pyfarm.models.core.cfg import TABLE_JOB_TYPE, MAX_JOBTYPE_LENGTH, TABLE_JOB
from pyfarm.models.core.app import db

JOBTYPE_BASECLASS = "JobType"


class JobTypeModel(db.Model):
    """
    Stores the unique information necessary to execute a task
    """
    __tablename__ = TABLE_JOB_TYPE

    id = IDColumn(db.Integer)
    _jobid = db.Column(IDTypeWork, db.ForeignKey("%s.id" % TABLE_JOB),
                       nullable=False,
                       doc=dedent("""
                       The foreign key which stores :class:`JobModel.id`"""))
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
    classname = db.Column(db.String(MAX_JOBTYPE_LENGTH), nullable=True,
                          doc=dedent("""
                          The name of the job class contained within the file
                          being loaded.  This field may be null but when it's
                          not provided :attr:`name` will be used instead."""))
    code = db.Column(db.UnicodeText, nullable=False,
                     doc=dedent("""
                     General field containing the 'code' the retrieve the job
                     type.  See below for information on what this field will
                     contain depending on how the job will be loaded.

                     * DOWNLOAD - full source code for the job type
                     * IMPORT - full path to the module to import
                     * OPEN - remote filepath to open (this is *not*
                     cross-platform safe)"""))
    mode = db.Column(db.Integer, default=JobTypeLoadMode.IMPORT, nullable=False,
                     doc=dedent("""
                     Indicates how the job type should be retrieved.

                     .. csv-table:: **JobTypeLoadMode Enums**
                        :header: Value, Result
                        :widths: 10, 50

                        DOWNLOAD, job type will be downloaded remotely
                        IMPORT, the remote agent will import the job type
                        OPEN, code is loaded directly from a file on disk"""))

    @validates("mode")
    def validates_mode(self, key, value):
        """ensures the value provided to :attr:`mode` is valid"""
        if value not in JobTypeLoadMode:
            raise ValueError("invalid value for mode")
        return value


def jobtype_before_insert(mapper, connection, jobtype):
    if jobtype.mode != JobTypeLoadMode.DOWNLOAD:
        return

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

event.listen(JobTypeModel, "before_insert", jobtype_before_insert)