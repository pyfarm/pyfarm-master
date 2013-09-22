from flask.ext.security import login_required, auth_token_required

from pyfarm.core.app.loader import package
import pyfarm.master

app = package.application()
db = package.database()
security = package.security(User, Role)
securitydb = package.security_datastore(User, Role)


# Create a user to test with
@app.before_first_request
def create_user():
    db.create_all()
    securitydb.create_user(
        email="agent", password="agent", username="foo")
    db.session.commit()

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