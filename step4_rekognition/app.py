# ============================================================
# Step4 リモート監視カメラ + AWS Rekognition (app.py)
#
# 【flask_sock から simple-websocket + threading に切り替え】
#   flask_sock のスレッドモデルはフレーム処理が重いと詰まる。
#   gevent-websocket を使い、各接続を独立したスレッドで処理する。
#
# 【スレッド構成】
#   ws_sender スレッド    : フレーム受信 → 動体検知 → ライブ配信
#   rekognition_worker    : キューから取り出してAPI呼び出し
#   ws_viewer スレッド×N : 各スマホの接続を管理
# ============================================================

import os, threading, queue, time, datetime, json, base64
import numpy as np, cv2, boto3
from flask import Flask, render_template, request
from geventwebsocket import WebSocketServer, WebSocketApplication, Resource
from geventwebsocket.handler import WebSocketHandler
from gevent import pywsgi
import gevent

app = Flask(__name__)

viewers      = set()
viewers_lock = threading.Lock()

THRESHOLD   = 500
MIN_AREA    = 1500
RK_INTERVAL = 5

prev_gray    = None
last_detect  = 0
last_rk_call = 0
detect_count = 0
log          = []
rk_queue     = queue.Queue(maxsize=1)

# ============================================================
# AWS Rekognition
#
# 認証情報は AWS_SHARED_CREDENTIALS_FILE / AWS_CONFIG_FILE で
# 指定されたファイルから boto3 が自動的に読み込む
# Colabでは以下を事前に実行しておくこと:
#   os.environ['AWS_SHARED_CREDENTIALS_FILE'] = '/content/.aws/credentials'
#   os.environ['AWS_CONFIG_FILE']             = '/content/.aws/config'
# ============================================================

# AWS_SHARED_CREDENTIALS_FILE / AWS_CONFIG_FILE が未設定なら
# Colabのデフォルトパスをセット
if 'AWS_SHARED_CREDENTIALS_FILE' not in os.environ:
    os.environ['AWS_SHARED_CREDENTIALS_FILE'] = '/content/.aws/credentials'
if 'AWS_CONFIG_FILE' not in os.environ:
    os.environ['AWS_CONFIG_FILE'] = '/content/.aws/config'

# キーは認証ファイルから自動読み込み、リージョンはハードコード
rekognition = boto3.client("rekognition", region_name="ap-northeast-1")

def rekognition_worker():
    while True:
        entry, af = rk_queue.get()
        try:
            _, ab  = cv2.imencode(".jpg", af, [cv2.IMWRITE_JPEG_QUALITY, 70])
            resp   = rekognition.detect_labels(
                Image={"Bytes": ab.tobytes()},
                MaxLabels=10, MinConfidence=60.0
            )
            labels = [{"name": l["Name"], "confidence": round(l["Confidence"],1)}
                      for l in resp["Labels"]]
        except Exception as e:
            print(f"Rekognition エラー: {e}")
            labels = []

        entry["labels"] = labels
        with viewers_lock:
            for i, e in enumerate(log):
                if e["id"] == entry["id"]:
                    log[i] = entry
                    break
        broadcast("alert:" + json.dumps(entry))
        rk_queue.task_done()

threading.Thread(target=rekognition_worker, daemon=True).start()

# ============================================================
# ヘルパー
# ============================================================

def broadcast(msg):
    with viewers_lock:
        dead = set()
        for ws in viewers:
            try:
                ws.send(msg)
            except:
                dead.add(ws)
        viewers.difference_update(dead)

# ============================================================
# フレーム処理
# ============================================================

def process(b64):
    global prev_gray, last_detect, last_rk_call, detect_count

    frame = cv2.imdecode(
        np.frombuffer(base64.b64decode(b64), np.uint8), cv2.IMREAD_COLOR)
    if frame is None:
        return

    JST = datetime.timezone(datetime.timedelta(hours=9))
    now = datetime.datetime.now(JST)
    ts  = now.strftime("%H:%M:%S.") + f"{now.microsecond//1000:03d}"
    h, w = frame.shape[:2]

    live = frame.copy()
    cv2.putText(live, ts, (8,h-8), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,100), 1)
    _, buf = cv2.imencode(".jpg", live, [cv2.IMWRITE_JPEG_QUALITY, 40])
    broadcast("live:" + base64.b64encode(buf).decode())
    broadcast("time:" + ts)

    gray = cv2.GaussianBlur(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY),(21,21),0)
    if prev_gray is not None:
        diff = cv2.absdiff(prev_gray, gray)
        _, th = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)
        th = cv2.dilate(th, None, iterations=2)
        cnts, _ = cv2.findContours(th, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        valid   = [c for c in cnts if cv2.contourArea(c) > MIN_AREA]
        now_t   = time.time()

        if int(np.sum(th>0)) > THRESHOLD and valid and now_t - last_detect > 3:
            last_detect = now_t
            detect_count += 1
            af = frame.copy()
            for c in valid:
                x,y,bw,bh = cv2.boundingRect(c)
                cv2.rectangle(af,(x,y),(x+bw,y+bh),(0,0,255),2)
            cv2.putText(af, f"MOTION #{detect_count}  {ts}",
                        (8,30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,0,255), 2)
            _, ab     = cv2.imencode(".jpg", af, [cv2.IMWRITE_JPEG_QUALITY, 70])
            alert_b64 = base64.b64encode(ab).decode()
            entry = {"id":detect_count,"ts":ts,"img":alert_b64,"labels":[]}
            with viewers_lock:
                log.insert(0, entry)
                if len(log) > 20: log.pop()

            if now_t - last_rk_call >= RK_INTERVAL:
                last_rk_call = now_t
                try:
                    rk_queue.put_nowait((entry, af.copy()))
                except queue.Full:
                    pass

    prev_gray = gray

# ============================================================
# Flask ルート（HTML配信）
# ============================================================

@app.route("/")
def index():
    if request.args.get("role") == "sender":
        return render_template("sender.html")
    return render_template("viewer.html")

# ============================================================
# WebSocket ハンドラ（gevent-websocket）
#
# gevent-websocket は各WebSocket接続を独立したグリーンスレッドで処理する
# flask_sock と違いフレーム処理が重くても他の接続に影響しない
# ============================================================

def handle_websocket(ws_path, ws):
    if ws_path == "/ws/sender":
        # PC送信者：フレームを受け取って process() で処理
        while not ws.closed:
            data = ws.receive()
            if data is None:
                break
            if data.startswith("frame:"):
                process(data[6:])

    elif ws_path == "/ws/viewer":
        # スマホ視聴者：登録して過去ログを送ってから待機
        with viewers_lock:
            viewers.add(ws)
        for entry in reversed(log):
            try:
                ws.send("alert:" + json.dumps(entry))
            except:
                break
        try:
            while not ws.closed:
                ws.receive()  # 接続維持のために待機
        finally:
            with viewers_lock:
                viewers.discard(ws)

# ============================================================
# WSGIアプリのラッパー：/ws/* は WebSocket、それ以外は Flask
# ============================================================

class AppDispatcher:
    def __init__(self, flask_app):
        self.flask_app = flask_app

    def __call__(self, environ, start_response):
        path = environ.get("PATH_INFO", "")
        ws   = environ.get("wsgi.websocket")

        if ws:
            # WebSocket接続
            handle_websocket(path, ws)
            return []
        else:
            # 通常のHTTPリクエストはFlaskへ
            return self.flask_app(environ, start_response)


if __name__ == "__main__":
    print("Step4 起動中... ポート5003")
    server = pywsgi.WSGIServer(
        ("0.0.0.0", 5003),
        AppDispatcher(app),
        handler_class=WebSocketHandler
    )
    server.serve_forever()
