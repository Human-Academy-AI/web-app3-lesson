#!/usr/bin/env python3

# ライブラリの読み込み
import datetime
import time
from flask_socketio import SocketIO
from flask import Flask, render_template


app = Flask(__name__)  # Flaskアプリの準備
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0
socketio = SocketIO(app)  # WebSocket通信の準備


def clock_task():
    """ウェブサーバと同時に処理させたいものを書く関数"""
    while True:
        # 時刻を取得
        date = datetime.datetime.now()

        # 表示用に時刻の文字列を作成
        date_for_display = date.strftime("%Y-%m-%d %H:%M:%S")

        # 時刻を送信
        socketio.emit("message", date_for_display)
        print("[{}]: ウェブアプリに時間を送信".format(date_for_display))
        # 1秒待つ
        time.sleep(1.0)


@app.route("/")
def main():
    """トップページにアクセスしたときに実行される関数"""
    return render_template("index.html")


if __name__ == "__main__":
    socketio.start_background_task(target=clock_task)
    socketio.run(app, host="0.0.0.0", port=8080)
