#!/usr/bin/env python3

# ライブラリの読み込み
import cv2
from flask_socketio import SocketIO
from flask import Flask, render_template


app = Flask(__name__)  # Flaskアプリの準備
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0
socketio = SocketIO(app)  # WebSocket通信の準備


def camera_task():
    """ウェブサーバと同時に処理させたいものを書く関数"""
    camera = cv2.VideoCapture(0, cv2.CAP_V4L2)
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 360)
    camera.set(cv2.CAP_PROP_FPS, 30)
    print("Webカメラを起動しました。")

    while True:
        # カメラから画像を読み取り
        success, image = camera.read()
        # データを変換
        byte_imgae = cv2.imencode(".jpg", image)[1].tobytes()
        # WebSocketで送信
        socketio.emit("camera", byte_imgae)


@app.route("/")
def main():
    """トップページにアクセスしたときに実行される関数"""
    return render_template("index.html")


if __name__ == "__main__":
    socketio.start_background_task(target=camera_task)
    socketio.run(app, host="0.0.0.0", port=8080)
