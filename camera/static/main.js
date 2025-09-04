function cameraReceive(data) {
    // HTMLで扱える形式に変換して表示する
    document.getElementById("camera-box").src = URL.createObjectURL(new Blob([data], { type: "image/jpeg" }));
}

// WebSocketで接続する準備
const ws = io.connect();

// カメラ映像を受信したときに呼び出す関数を決める
ws.on("camera", cameraReceive);