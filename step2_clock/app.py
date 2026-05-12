import threading, time, datetime
from flask import Flask, render_template
from flask_sock import Sock

app = Flask(__name__)
sock = Sock(app)
clients = set()
lock = threading.Lock()

def broadcast():
    while True:
        now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
        ts = now.strftime("%H:%M:%S.") + f"{now.microsecond//1000:03d}"
        with lock:
            dead = set()
            for ws in clients:
                try:
                    ws.send(ts)
                except:
                    dead.add(ws)
            clients.difference_update(dead)
        time.sleep(0.1)

threading.Thread(target=broadcast, daemon=True).start()

@app.route("/")
def index():
    return render_template("index.html")

@sock.route("/ws/clock")
def clock_ws(ws):
    with lock:
        clients.add(ws)
    try:
        while ws.receive(timeout=60) is not None:
            pass
    finally:
        with lock:
            clients.discard(ws)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=False)
