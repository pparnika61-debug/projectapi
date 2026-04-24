from flask import Flask

from control.control import controllers
from database import create_tables

app = Flask(__name__)
app.secret_key = "supersecretkey"
app.register_blueprint(controllers)
# Create DB tables
create_tables()

if __name__ == "__main__":
    app.run()