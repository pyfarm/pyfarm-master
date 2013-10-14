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

from flask.views import MethodView
from pyfarm.models.agent import AgentModel
from pyfarm.master.api.decorators import put_model
from pyfarm.master.application import db
from pyfarm.master.utility import JSONResponse


#TODO: documentation
class AgentsIndex(MethodView):
    """
    Endpoint for /agents
    """
    def get(self):
        # TODO: add filtering
        data = dict(
            (i.hostname, (i.id, i.state, i.freeram, i.ram, i.cpus))
            for i in AgentModel.query)
        return JSONResponse(data)

    @put_model(AgentModel)
    def put(self, data, model):
        db.session.add(model)
        db.session.commit()
        return JSONResponse(model.to_dict())