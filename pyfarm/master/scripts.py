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
Scripts
=======

Contains entry points for command line tools.
"""

# TODO: if adding to the admin group, admin password must be provided


def create_user():
    # TODO: produce warning when no group(s) are provided
    pass


def add_user_to_groups():
    # TODO: if group(s) do not exist, confirm their creation
    pass


def delete_group():
    # TODO: produce warning if user(s) exist in the group, ask for confirmation
    pass


def delete_user():
    # TODO: delete user
    # TODO: remove empty group(s)
    pass