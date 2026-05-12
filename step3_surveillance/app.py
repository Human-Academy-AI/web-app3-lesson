import threading, time, datetime, json, base64
import numpy as np, cv2
from flask import Flask, render_template, request
from flask_sock import Sock

app = Flask(__name__)
sock = Sock(app)
viewers = set()
lock = threading.Lock()
prev_gray = None
last_detect = 0
detect_count = 0
log = []

THRESHOLD = 500
MIN_AREA  = 1500
COOLDOWN  = 3

def broadcast(msg):
    with lock:
        dead = set()
        for ws in viewers:
            try:
                ws.send(msg)
            except:
                dead.add(ws)
        viewers.difference_update(dead)

def process(b64):
    global prev_gray, last_detect, detect_count
    frame = cv2.imdecode(np.frombuffer(base64.b64decode(b64), np.uint8), cv2.IMREAD_COLOR)
    if frame is None:
        return
    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
    ts  = now.strftime("%H:%M:%S.") + f"{now.microsecond//1000:03d}"
    h, w = frame.shape[:2]

    # 時刻を焼き込んでライブ配信
    live = frame.copy()
    cv2.putText(live, ts, (8, h-8), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,100), 1)
    _, buf = cv2.imencode(".jpg", live, [cv2.IMWRITE_JPEG_QUALITY, 50])
    broadcast("live:" + base64.b64encode(buf).decode())
    broadcast("time:" + ts)

    # 動体検知
    gray = cv2.GaussianBlur(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), (21,21), 0)
    if prev_gray is not None:
        diff = cv2.absdiff(prev_gray, gray)
        _, th = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)
        th = cv2.dilate(th, None, iterations=2)
        cnts, _ = cv2.findContours(th, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        valid = [c for c in cnts if cv2.contourArea(c) > MIN_AREA]
        if int(np.sum(th>0)) > THRESHOLD and valid and time.time()-last_detect > COOLDOWN:
            last_detect = time.time()
            detect_count += 1
            af = frame.copy()
            for c in valid:
                x,y,bw,bh = cv2.boundingRect(c)
                cv2.rectangle(af, (x,y), (x+bw,y+bh), (0,0,255), 2)
            cv2.putText(af, f"MOTION #{detect_count}  {ts}", (8,30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,0,255), 2)
            _, ab = cv2.imencode(".jpg", af, [cv2.IMWRITE_JPEG_QUALITY, 50])
            entry = {"id": detect_count, "ts": ts, "img": base64.b64encode(ab).decode()}
            log.insert(0, entry)
            if len(log) > 20:
                log.pop()
            broadcast("alert:" + json.dumps(entry))
    prev_gray = gray

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
        if data.startswith("frame:"):
            process(data[6:])

@sock.route("/ws/viewer")
def ws_viewer(ws):
    with lock:
        viewers.add(ws)
    for entry in reversed(log):
        try:
            ws.send("alert:" + json.dumps(entry))
        except:
            break
    try:
        while ws.receive(timeout=60) is not None:
            pass
    finally:
        with lock:
            viewers.discard(ws)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002, debug=False)
