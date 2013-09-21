from flask.ext.security import login_required, auth_token_required

from pyfarm.models.security import User, Role
from pyfarm.models.security import Role, User

import pyfarm.master
from pyfarm.core.app.loader import package
app = package.application()
db = package.database()
security = package.security(User, Role)
user_datastore = package.security_datastore(User, Role)

#
# # Create a user to test with
@app.before_first_request
def create_user():
    db.create_all()
    user_datastore.create_user(
        email='test', password='test')
    db.session.commit()

# Views
@app.route('/')
@login_required
def home():
    return "index.html"

@app.route("/test")
@auth_token_required
def test():
    return "success!"

if __name__ == '__main__':
    app.run()