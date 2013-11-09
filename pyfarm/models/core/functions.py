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
.. include:: ../include/references.rst

Functions
=========

Contains core functions and data for use by :mod:`pyfarm.models`
"""

from uuid import UUID
from datetime import datetime
from textwrap import dedent
from pyfarm.core.config import cfg
from pyfarm.master.application import db
from pyfarm.models.core.types import IDColumn, IDTypeWork


def modelfor(model, table):
    """
    Returns True if the given `model` object is for the
    expected `table`.

    >>> from pyfarm.models.core.cfg import TABLE_AGENT
    >>> from pyfarm.models import Agent
    >>> modelfor(Agent("foo", "10.56.0.0", "255.0.0.0"), TABLE_AGENT)
    True
    """
    try:
        return model.__tablename__ == table
    except AttributeError:
        return False
    

def getuuid(value, table, table_attrib, error_tail):
    """
    Returns the proper value for the given input.  Depending on the type being
    provided this will return one of the following:

        * None
        * the value from an attribute
        * string from a UUID
        * the original value (after validating it's a UUID)

    :arg string value:
        the value to validate and returning data from

    :arg string table:
        the table which the provided `value` belongs to

    :arg string table_attrib:
        the attribute to use when attempting to pull data off of a model
        object

    :arg string error_tail:
        added to the end of error messages

    :arg str error_text:
        error text to render in the event of problems

    :exception ValueError:
        raised when the provided input is invalid, blank, or otherwise
        unexpected
    """
    if value is None:
        return value

    elif modelfor(value, table):
        value = getattr(value, table_attrib, None)
        if value is None:
            raise ValueError("null id provided for %s" % error_tail)
        return value

    # if a string was provided then we should
    # try to convert it into a uuid first to
    # be sure it's valid
    elif isinstance(value, basestring):
        UUID(value)
        return value

    elif isinstance(value, UUID):
        return str(value)

    else:
        raise ValueError("failed to determine %s" % error_tail)


def WorkColumns(state_default, priority_default, priority_alt=500):
    """
    Produces some default columns which are used by models which produce
    work.  Currently this includes |Job| and |TaskModel|
    """
    return (
        # id
        IDColumn(IDTypeWork),

        # state
        db.Column(db.Integer, default=state_default,
                  doc=dedent("""
                  The state of the job with a value provided by
                  :class:`.WorkState`""")),

        # priority
        db.Column(db.Integer, default=lambda: cfg.get(priority_default, priority_alt),
                  doc=dedent("""
                  The priority of the job relative to others in the
                  queue.  This is not the same as task priority.

                  **configured by**: `%s`""" % priority_default)),

        # time_submitted
        db.Column(db.DateTime, default=datetime.now,
                               doc=dedent("""
                               The time the job was submitted.  By default this
                               defaults to using :meth:`datetime.datetime.now`
                               as the source of submission time.  This value
                               will not be set more than once and will not
                               change even after a job is requeued.""")),

        # time_started
        db.Column(db.DateTime,
                  doc=dedent("""
                  The time this job was started.  By default this value is set
                  when :attr:`state` is changed to an appropriate value or
                  when a job is requeued.""")),

        # time_finished
        db.Column(db.DateTime,
                  doc=dedent("""
                  Time the job was finished.  This will be set when the last
                  task finishes and reset if a job is requeued."""))
    )


def split_and_extend(items):
    """
    Takes a list of input elements and splits them
    before producing an extended set.

    **Example**
        >>> split_and_extend(["root.admin", "admin"])
        set(['admin', 'root.admin', 'root'])
    """
    if not items:
        return items

    output = set()

    for item in items:
        current = []

        for split_item in item.split("."):
            current = current + [split_item]
            output.add(".".join(current))

    return output