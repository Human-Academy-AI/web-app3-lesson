import threading
from flask import Flask, render_template, request
from flask_sock import Sock

app = Flask(__name__)
sock = Sock(app)
viewers = set()
lock = threading.Lock()

@app.route("/")
def index():
    if request.args.get("role") == "sender":
        return render_template("sender.html")
    return render_template("viewer.html")

@sock.route("/ws/sender")
def ws_sender(ws):
    while True:
        data = ws.receive()
        if data is None:
            break
        with lock:
            dead = set()
            for v in viewers:
                try:
                    v.send(data)
                except:
                    dead.add(v)
            viewers.difference_update(dead)

@sock.route("/ws/viewer")
def ws_viewer(ws):
    with lock:
        viewers.add(ws)
    try:
        while ws.receive(timeout=60) is not None:
            pass
    finally:
        with lock:
            viewers.discard(ws)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
