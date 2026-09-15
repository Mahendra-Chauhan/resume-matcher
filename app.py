"""
app.py — entry point. Now also sets up the database connection.
"""

from flask import Flask
from models import db  # our shared db object from models.py

app = Flask(__name__)

# Tells Flask-SQLAlchemy where the database file lives.
# sqlite:/// means "a local file", followed by the filename.
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///resume_matcher.db"

# Connects our models.py db object to this specific Flask app.
db.init_app(app)


@app.route("/")
def home():
    return "Resume Matcher is alive! Flask is working correctly."


if __name__ == "__main__":
    app.run(debug=True)
    