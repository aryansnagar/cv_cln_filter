import os
from flask import Flask, send_from_directory
BASE = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)

@app.get("/")
def form():
    return send_from_directory(BASE, "form_page.html")

if __name__ == "__main__":
    app.run(port=5001)
