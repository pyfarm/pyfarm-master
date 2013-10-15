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
from pyfarm.master.api.decorators import put_model, post_model
from pyfarm.master.application import db
from pyfarm.master.utility import JSONResponse


#TODO: documentation
class AgentsIndex(MethodView):
    """
    Endpoint for /agents
    """
    # TODO: add filtering via url /api/v1/agents/1
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


    # TODO: be sure not to null non-nullables by providing a null
    # TODO: if STATE is changed to offline, STOP other tasks/related activity
    @post_model(AgentModel)
    def post(self, data, model):
        """
        .. http:post:: /agents

            * update column (or columns)

                **Request**

                .. sourcecode:: http

                    POST /<prefix>/agents HTTP/1.1
                    Accept: application/json

                    {"id": 2, "ram": 256}

                **Response**

                .. sourcecode:: http

                    HTTP/1.1 200 OK
                    Content-Type: application/json

                    {
                        "cpu_allocation": 1.0,
                        "cpus": 4,
                        "freeram": 2294,
                        "hostname": "agent",
                        "id": 2,
                        "ip": "10.190.195.156",
                        "port": 16207,
                        "ram": 256,
                        "ram_allocation": 0.8,
                        "state": 8
                     }

            * update unknown column(s)

                **Request**

                .. sourcecode:: http

                    POST /<prefix>/agents HTTP/1.1
                    Accept: application/json

                    {"id": 2, "foo": 256}

                **Response**

                .. sourcecode:: http

                    HTTP/1.1 400 BAD REQUEST
                    Content-Type: application/json

                    [5, "unknown columns were included with the request: ['foo']"]

            * update without ID

                **Request**

                .. sourcecode:: http

                    POST /<prefix>/agents HTTP/1.1
                    Accept: application/json

                    {"ram": 256}

                **Response**

                .. sourcecode:: http

                    HTTP/1.1 400 BAD REQUEST
                    Content-Type: application/json

                    [2, "id field is missing"]
        """
        update_data = data.copy()
        update_data.pop("id")

        # add the model to the session and update it
        updated = False
        db.session.add(model)
        for key, value in update_data.iteritems():
            current_value = getattr(model, key)

            if value != current_value:
                setattr(model, key, value)
                updated = True

        if updated:
            db.session.commit()

        return JSONResponse(model.to_dict())