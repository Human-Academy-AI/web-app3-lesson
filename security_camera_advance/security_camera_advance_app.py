#!/usr/bin/env python3

# ライブラリの読み込み
import cv2
import boto3
import os
import datetime
from flask_socketio import SocketIO
from flask import Flask, render_template
from motion_detector import MotionDetector


app = Flask(__name__)  # Flaskアプリの準備
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0
socketio = SocketIO(app)  # WebSocket通信の準備


def camera_task():
    """ウェブサーバと同時に処理させたいものを書く関数"""
    # カメラの準備
    camera = cv2.VideoCapture(0, cv2.CAP_V4L2)
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 360)
    camera.set(cv2.CAP_PROP_FPS, 30)
    print("Webカメラを起動しました。")

    # 動体検出の準備
    motion_detector = MotionDetector()

    while True:
        # カメラから画像を読み取り
        success, image = camera.read()
        # データを変換
        byte_imgae = cv2.imencode(".jpg", image)[1].tobytes()
        # WebSocketで送信
        socketio.emit("camera", byte_imgae)

        # 動体検出で実行
        is_moving = motion_detector.detect_motion(image)

        # もし動体検出されたら
        if is_moving == True:
            # ウェブアプリに動体検出したことを知らせる
            # 知らせるだけなので、空の文字列を送信
            socketio.emit("moving", "")

            # 時刻を取得
            date = datetime.datetime.now()

            # 時刻を画像パス用の文字列に変換
            date_for_path = date.strftime("%Y%m%d-%H%M%S")

            # 時刻から画像の保存先パスを作成する
            image_path = "./static/save_images/{}.jpg".format(date_for_path)

            # 画像を保存
            cv2.imwrite(image_path, image)

            # 画像を読み込む
            with open(image_path, "rb") as f:
                # AWSで物体検出
                rekognition = boto3.client(service_name="rekognition")
                response_data = rekognition.detect_labels(
                    Image={"Bytes": f.read()}
                )["Labels"]

                # 検出したラベルを4つだけ取り出す
                labels = [d["Name"] for d in response_data][:4]

                # ウェブアプリに送る辞書型のデータを作成
                send_data = {
                    "image_path": image_path,
                    "labels": labels
                }

                # WebSocketを使って送信
                socketio.emit("message", send_data)


@app.route("/")
def main():
    """トップページにアクセスしたときに実行される関数"""
    return render_template("index.html")


if __name__ == "__main__":
    os.makedirs("./static/save_images", exist_ok=True)
    socketio.start_background_task(target=camera_task)
    socketio.run(app, host="0.0.0.0", port=8080)
