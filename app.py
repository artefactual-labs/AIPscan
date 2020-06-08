from flask import Flask

app = Flask(__name__)

@app.route('/')
def index():
    return "This is an example app"

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
