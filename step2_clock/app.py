# ============================================================
# Step2 時刻アプリ - サーバー側 (app.py)
#
# 【役割】
#   サーバーの現在時刻（日本時間）を100msごとにスマホへ送る
#
# 【HTTPとWebSocketの違いをここで体験する】
#   HTTP    : スマホが「今何時？」と聞いて → サーバーが答える（1往復）
#   WebSocket: サーバーが「今12:34:56です」と勝手に送り続ける（サーバープッシュ）
# ============================================================

import threading
import time
import datetime
from flask import Flask, render_template
from flask_sock import Sock

app = Flask(__name__)

# --- WebSocket の初期化 ---
sock = Sock(app)

# 接続中のスマホをまとめて管理するセット
clients = set()
lock = threading.Lock()


# ============================================================
# バックグラウンド処理：全クライアントへ時刻を送り続ける
# ============================================================

def broadcast():
    while True:
        JST = datetime.timezone(datetime.timedelta(hours=9))
        now = datetime.datetime.now(JST)
        ts  = now.strftime("%H:%M:%S.") + f"{now.microsecond // 1000:03d}"

        with lock:
            dead = set()
            for ws in clients:
                try:
                    # --- WebSocket でサーバーからデータを「プッシュ」送信 ---
                    # ws.send() はクライアントのリクエストを待たずに
                    # サーバー側から自発的にデータを送れる
                    # これがWebSocketの最大の特徴（HTTPにはできない）
                    ws.send(ts)
                except:
                    dead.add(ws)
            clients.difference_update(dead)

        time.sleep(0.1)  # 100ms待機してから次の時刻を送る


# サーバー起動と同時にバックグラウンドで時刻送信を開始
threading.Thread(target=broadcast, daemon=True).start()


@app.route("/")
def index():
    return render_template("index.html")


# --- WebSocket エンドポイント：スマホ接続を受け付ける ---
# スマホが /ws/clock に接続してきたらこの関数が動く
# broadcast() が別スレッドで動いており、登録された clients へ時刻を送り続ける
@sock.route("/ws/clock")
def clock_ws(ws):
    # 新しいスマホを clients に追加
    # 以降 broadcast() がこの ws へも時刻を送るようになる
    with lock:
        clients.add(ws)
    try:
        # --- 接続を維持するための待機 ---
        # ws.receive() で待ち続けることで関数が終了せず接続が保たれる
        # スマホからは何も送ってこないが、接続維持のためにここで待つ必要がある
        # もしここがなければ関数がすぐに return してしまい接続が切れる
        while ws.receive(timeout=60) is not None:
            pass
    finally:
        # タイムアウトや切断時に clients から削除
        with lock:
            clients.discard(ws)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=False)
