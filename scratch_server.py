from flask.ext.security import (
    SQLAlchemyUserDatastore, Security, login_required, auth_token_required,
    roles_required)
from pyfarm.models.core.app import app, db
from pyfarm.models.security import Role, User

app.config["DEBUG"] = True
app.config["WTF_CSRF_ENABLED"] = False
app.config["SECURITY_TRACKABLE"] = True

# Setup Flask-Security
user_datastore = SQLAlchemyUserDatastore(db, User, Role)
security = Security(app, user_datastore)

# Create a user to test with
@app.before_first_request
def create_user():
    db.create_all()
    user_datastore.create_user(
        email='test', password='test')
    # user_datastore.create_role(name="api") # TODO: not working for some reason
    # user_datastore.add_role_to_user("test", "api")
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


# @app.route("/test/role/admin")
# @auth_token_required
# @roles_required("admin")
# def test_role_admin():
#     return "success (rule: admin)!"
#
#
# @app.route("/test/role/api")
# @auth_token_required
# @roles_required("api")
# def test_role_api():
#     return "success (rule: api)!"

if __name__ == '__main__':
    app.run()