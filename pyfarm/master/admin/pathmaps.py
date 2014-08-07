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
Path maps
=========

Admin view for managing path maps
"""

from pyfarm.master.admin.baseview import SQLModelView
from pyfarm.master.application import SessionMixin
from pyfarm.models.tag import Tag
from pyfarm.models.pathmap import PathMap

from pyfarm.master.admin.core import AjaxLoader

class PathMapView(SessionMixin, SQLModelView):
    model = PathMap

    form_ajax_refs = {
        "tag": AjaxLoader("tag", Tag, fields=("tag", ),
                           fmt=lambda model: model.tag)}
