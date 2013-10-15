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
API Utilities
-------------

Functions and classes specific to the API endpoints
"""

from pyfarm.master.utility import get_column_sets


class column_cache(object):
    """
    Basic cache which stores required and optional columns for
    individual tables
    """
    models = {}

    @classmethod
    def get_columns(cls, model):
        """
        Returns a tuple of (all_columns, required_columns).  Results will
        be stored for reuse before being returned from :func:`.get_column_sets`
        """
        if model not in cls.models:
            cls.models[model] = get_column_sets(model)

        return cls.models[model]

    @classmethod
    def all_columns(cls, model):
        """returns a set of all columns for model using :meth:`get_columns`"""
        all_columns, required_columns = cls.get_columns(model)
        return all_columns

    @classmethod
    def required_columns(cls, model):
        """
        returns a set of all required columns for the model using
        :meth:`get_columns`
        """
        all_columns, required_columns = cls.get_columns(model)
        return required_columns
