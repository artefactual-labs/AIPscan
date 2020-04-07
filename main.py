from flask import Flask, render_template
from config import DevConfig

app = Flask(__name__)
app.config.from_object(DevConfig)


@app.route("/")
def home():
    return render_template("home.html")


if __name__ == "__main__":
    app.run()
