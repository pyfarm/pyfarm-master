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
Mixin Classes
=============

Module containing mixins which can be used by multiple models.
"""

from warnings import warn
from datetime import datetime
from sqlalchemy.orm import validates
from pyfarm.core.warning import ColumnStateChangeWarning
from pyfarm.core.config import read_env_int


class WorkValidationMixin(object):
    """
    Mixin that adds a `state` column and uses a class
    level `STATE_ENUM` attribute to assist in validation.
    """
    MIN_PRIORITY = read_env_int("PYFARM_QUEUE_MIN_PRIORITY", -1000)
    MAX_PRIORITY = read_env_int("PYFARM_QUEUE_MAX_PRIORITY", 1000)

    # quick check of the configured data
    assert MAX_PRIORITY >= MIN_PRIORITY, "MIN_PRIORITY must be <= MAX_PRIORITY"

    @validates("state")
    def validate_state(self, key, value):
        """
        Validates the `value` being provided for `state` is within
        the range provided by `STATE_ENUM`
        """
        if value not in self.STATE_ENUM:
            raise ValueError("%s is not a valid state" % repr(value))

        return value

    @validates("priority")
    def validate_priority(self, key, value):
        """ensures the value provided to priority is valid"""
        if self.MIN_PRIORITY <= value <= self.MAX_PRIORITY:
            return value

        err_args = (key, self.MIN_PRIORITY, self.MAX_PRIORITY)
        raise ValueError("%s must be between %s and %s" % err_args)

    @validates("attempts")
    def validate_attempts(self, key, value):
        """ensures the number of attempts provided is valid"""
        if value > 0 or value is None:
            return value

        raise ValueError("%s cannot be less than zero" % key)


class StateChangedMixin(object):
    """
    Mixin which adds a static method to be used when the model
    state changes
    """
    @staticmethod
    def stateChangedEvent(target, new_value, old_value, initiator):
        """update the datetime objects depending on the new value"""
        if new_value == target.STATE_ENUM.RUNNING:
            target.time_started = datetime.now()
            target.time_finished = None

            if target.attempts is None:
                target.attempts = 1
            else:
                target.attempts += 1

        elif new_value in (target.STATE_ENUM.DONE, target.STATE_ENUM.FAILED):
            if target.time_started is None:  # pragma: no cover
                msg = "job %s has not been started yet, state is " % target.id
                msg += "being set to %s" % target.STATE_ENUM.get(new_value)
                warn(msg,  ColumnStateChangeWarning)

            target.time_finished = datetime.now()


class DictMixins(object):
    """
    Mixins which can be used to produce dictionaries
    of existing data
    """
    def to_dict(self):
        """Produce a dictionary of existing data in the table"""
        try:
            serialize_column = self.serialize_column
        except AttributeError:  # pragma: no cover
            serialize_column = None

        result = {}
        for column_name in self.__table__.c.keys():
            value = getattr(self, column_name)

            if serialize_column is not None:
                value = serialize_column(value)

            result[column_name] = value

        return result

    def to_schema(self):
        """
        Produce a dictionary which represents the
        table's schema in a basic format
        """
        result = {}
        for name, column in self.__table__.c.items():
            try:
                column.type.python_type
            except NotImplementedError:
                column_type = column.type.__class__.__name__
            else:
                column_type = str(column.type)

            result[name] = column_type

        return result

