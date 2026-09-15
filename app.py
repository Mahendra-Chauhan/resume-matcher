"""
app.py — the entry point of our Flask web application.

This file's only job right now is to prove Flask is installed and working.
We'll expand it step by step as we build the real features.
"""

# Flask is the web framework — it lets Python code respond to web browser requests.
from flask import Flask

# This creates our "application" object. Every Flask app starts with this line.
# __name__ tells Flask where to look for things like templates and static files.
app = Flask(__name__)


# The @app.route decorator says: "when someone visits this URL in a browser,
# run the function right below it."
# "/" means the homepage — e.g. http://127.0.0.1:5000/
@app.route("/")
def home():
    # Whatever this function returns is what the browser displays.
    return "Resume Matcher is alive! Flask is working correctly."


# This block only runs when you execute this file directly (python app.py),
# not when it's imported elsewhere. It's a standard Python pattern.
if __name__ == "__main__":
    # debug=True auto-reloads the server when you save changes to this file,
    # and shows helpful error pages in the browser if something breaks.
    app.run(debug=True)

    