# ============================================================
# Step1 シンプルカメラ - サーバー側 (app.py)
#
# 【役割】
#   PCブラウザ（送信者）からカメラ映像を受け取り、
#   スマホ（視聴者）へ転送する「中継サーバー」です。
#
# 【WebSocketの流れ】
#   PCブラウザ  --[映像フレーム]--> サーバー --[映像フレーム]--> スマホ
# ============================================================

import threading
from flask import Flask, render_template, request
from flask_sock import Sock

app = Flask(__name__)

# --- WebSocket の初期化 ---
# Sock(app) で Flask アプリに WebSocket 機能を追加する
# これにより @sock.route() でWebSocketのエンドポイントを定義できるようになる
sock = Sock(app)

# 視聴者（スマホ）のWebSocket接続をまとめて管理するセット
viewers = set()
lock = threading.Lock()


@app.route("/")
def index():
    if request.args.get("role") == "sender":
        return render_template("sender.html")
    return render_template("viewer.html")


# --- WebSocket エンドポイント①：PC送信者用 ---
# @sock.route("/ws/sender") で /ws/sender というURLへの
# WebSocket接続を受け付けるハンドラを登録する
# 通常のHTTPルート @app.route() と違い、接続が続く限りこの関数が動き続ける
@sock.route("/ws/sender")
def ws_sender(ws):
    # ws はこのPC接続のWebSocketオブジェクト
    # ws.receive() でPCから送られるデータを1件受け取る
    # データが来るまでここでブロック（待機）する
    while True:
        data = ws.receive()  # PCからフレームデータが届くまで待つ
        if data is None:     # None が返ったら接続が切れたサイン
            break            # ループを抜けて関数を終了する

        # 受け取ったフレームを全スマホ視聴者へ転送する
        with lock:
            dead = set()
            for v in viewers:
                try:
                    # ws.send() で接続中の相手へデータを送信する
                    # ここでは受け取ったフレームをそのまま各スマホへ中継
                    v.send(data)
                except:
                    dead.add(v)  # 送信失敗 = 切断済みと判断
            viewers.difference_update(dead)


# --- WebSocket エンドポイント②：スマホ視聴者用 ---
# スマホがこのエンドポイントに接続してきたら viewers に追加する
# 映像はサーバーから一方的に送られるので、スマホ側は受け取るだけでよい
@sock.route("/ws/viewer")
def ws_viewer(ws):
    # 新しい視聴者を登録（以降 ws_sender がこの ws に映像を転送する）
    with lock:
        viewers.add(ws)
    try:
        # スマホ側からは何も送ってこないが、
        # ws.receive() で待ち続けることで「接続を維持」できる
        # ここを抜けると関数が終了し、接続が切れてしまう
        while ws.receive(timeout=60) is not None:
            pass
    finally:
        # 切断時（タイムアウト・ブラウザを閉じるなど）に視聴者リストから削除
        with lock:
            viewers.discard(ws)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
