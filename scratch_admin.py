"""
flask_login_app
==============
 
An example of how to implement get_auth_token and token_loader of Flask-Login.
This example builds on the excellent docs of flask-login which clearly explains
how to setup basic session based Authentication. 
 
This example uses the python module itsdangerous to handle the encryption and
decryption of the remember me token. 
 
Flask Version: 0.9
Flask-Login Version: 0.1.3
itsdangerous Version: 0.17
 
Author: Christopher Ross
Site: http://blog.thecircuitnerd.com/flask-login-tokens/
Version: 0.1a
"""

from datetime import timedelta
 
from flask import redirect
from flask_login import login_required, logout_user

from pyfarm.core.app.loader import package
from pyfarm.models.permission import User, Role, login_serializer

from pyfarm.master.login import manager


app = package.application()
db = package.database()


@app.before_first_request
def create_user():
    db.create_all()
    User.create(username="agent", password="agent")



 
@app.route("/")
@login_required
def index_page():
    """
    Web Page to display The Main Index Page
    """
    return "index"

 
if __name__ == "__main__":
    #Change the duration of how long the Remember Cookie is valid on the users
    #computer.  This can not really be trusted as a user can edit it. 
    app.config["REMEMBER_COOKIE_DURATION"] = timedelta(days=14)

    #Tell the login manager where to redirect users to display the login page
    manager.login_view = "/login/"
    manager.init_app(app)
 
    #Run the flask Development Server
    app.run()