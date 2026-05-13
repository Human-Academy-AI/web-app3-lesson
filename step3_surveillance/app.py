# ============================================================
# Step3 リモート監視カメラ - サーバー側 (app.py)
#
# 【役割】
#   Step1（カメラ中継）＋ Step2（時刻配信）を組み合わせ、
#   さらにOpenCVで動体検知を行う
#
# 【WebSocketで送るメッセージの種類】
#   "live:"  + Base64画像  → ライブ映像フレーム（5FPS）
#   "time:"  + 時刻文字列  → 現在時刻（フレームごと）
#   "alert:" + JSON文字列  → 動体検知アラート
# ============================================================

import threading
import time
import datetime
import json
import base64
import numpy as np
import cv2
from flask import Flask, render_template, request
from flask_sock import Sock

app = Flask(__name__)

# --- WebSocket の初期化 ---
sock = Sock(app)

# 視聴者（スマホ）のWebSocket接続を管理するセット
viewers = set()
lock = threading.Lock()

# 動体検知のパラメータ
THRESHOLD = 500
MIN_AREA  = 1500
COOLDOWN  = 3

prev_gray    = None
last_detect  = 0
detect_count = 0
log          = []


# ============================================================
# ヘルパー関数：全スマホ視聴者へWebSocketでメッセージを送る
# ============================================================

def broadcast(msg):
    # viewers セット内の全スマホへ同じメッセージを一斉送信する
    # これがStep1・2と違うポイント：複数のスマホへ同時配信できる
    with lock:
        dead = set()
        for ws in viewers:
            try:
                ws.send(msg)  # 各スマホのWebSocketへ送信
            except:
                dead.add(ws)  # 送信失敗 = 切断済み
        viewers.difference_update(dead)


# ============================================================
# フレーム処理：受け取った画像を加工して配信・検知する
# ============================================================

def process(b64):
    global prev_gray, last_detect, detect_count

    # Base64文字列 → OpenCV画像に変換
    frame = cv2.imdecode(
        np.frombuffer(base64.b64decode(b64), np.uint8),
        cv2.IMREAD_COLOR
    )
    if frame is None:
        return

    JST = datetime.timezone(datetime.timedelta(hours=9))
    now = datetime.datetime.now(JST)
    ts  = now.strftime("%H:%M:%S.") + f"{now.microsecond // 1000:03d}"
    h, w = frame.shape[:2]

    # --- WebSocket① ライブ映像を全スマホへ配信 ---
    # 時刻を焼き込んだ画像をBase64に変換して "live:" プレフィックスで送る
    # スマホ側は "live:" を見てライブ映像と判断する
    live = frame.copy()
    cv2.putText(live, ts, (8, h - 8),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 100), 1)
    _, buf = cv2.imencode(".jpg", live, [cv2.IMWRITE_JPEG_QUALITY, 50])
    broadcast("live:" + base64.b64encode(buf).decode())

    # --- WebSocket② 時刻文字列を全スマホへ配信 ---
    # Step2と同じ仕組み。スマホの時計表示を更新するために送る
    broadcast("time:" + ts)

    # 動体検知（フレーム差分法）
    gray = cv2.GaussianBlur(
        cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), (21, 21), 0
    )

    if prev_gray is not None:
        diff = cv2.absdiff(prev_gray, gray)
        _, th = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)
        th = cv2.dilate(th, None, iterations=2)
        cnts, _ = cv2.findContours(
            th, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        valid   = [c for c in cnts if cv2.contourArea(c) > MIN_AREA]
        diff_px = int(np.sum(th > 0))

        if diff_px > THRESHOLD and valid and time.time() - last_detect > COOLDOWN:
            last_detect = time.time()
            detect_count += 1

            # 検知フレームに赤枠と警告テキストを描画
            af = frame.copy()
            for c in valid:
                x, y, bw, bh = cv2.boundingRect(c)
                cv2.rectangle(af, (x, y), (x + bw, y + bh), (0, 0, 255), 2)
            cv2.putText(af, f"MOTION #{detect_count}  {ts}", (8, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

            _, ab = cv2.imencode(".jpg", af, [cv2.IMWRITE_JPEG_QUALITY, 50])
            entry = {
                "id":  detect_count,
                "ts":  ts,
                "img": base64.b64encode(ab).decode()
            }

            log.insert(0, entry)
            if len(log) > 20:
                log.pop()

            # --- WebSocket③ 動体検知アラートを全スマホへ配信 ---
            # JSON形式にして "alert:" プレフィックスで送る
            # スマホ側は "alert:" を見て検知ログに追加する
            broadcast("alert:" + json.dumps(entry))

    prev_gray = gray


@app.route("/")
def index():
    if request.args.get("role") == "sender":
        return render_template("sender.html")
    return render_template("viewer.html")


# --- WebSocket エンドポイント①：PC送信者用 ---
# PCブラウザから "frame:" + Base64画像 を受け取り process() で処理する
@sock.route("/ws/sender")
def ws_sender(ws):
    while True:
        data = ws.receive()  # PCからフレームが届くまで待つ
        if data is None:     # None = 接続切断
            break
        if data.startswith("frame:"):
            process(data[6:])  # "frame:" の6文字を除いた Base64部分を渡す


# --- WebSocket エンドポイント②：スマホ視聴者用 ---
# 新規接続スマホを登録し、過去の検知ログを送ってから待機する
@sock.route("/ws/viewer")
def ws_viewer(ws):
    with lock:
        viewers.add(ws)  # 登録後は broadcast() が自動的に映像を送り始める

    # --- 新規接続スマホへ過去の検知ログを送信 ---
    # スマホを開き直した場合でも過去の検知履歴を表示できるようにする
    # サーバーのlog変数に保存されているエントリを古い順に送る
    for entry in reversed(log):
        try:
            # "alert:" + JSONで既存ログを送る（通常の検知アラートと同じ形式）
            ws.send("alert:" + json.dumps(entry))
        except:
            break

    try:
        # 接続を維持するための待機（スマホからは何も送ってこない）
        while ws.receive(timeout=60) is not None:
            pass
    finally:
        with lock:
            viewers.discard(ws)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002, debug=False)
