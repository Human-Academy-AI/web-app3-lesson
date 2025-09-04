function cameraReceive(data) {
  // HTMLで扱える形式に変換して表示する
  document.getElementById("camera-box").src = URL.createObjectURL(new Blob([data], { type: "image/jpeg" }));
}

function movingReceive(data) {
  // 処理中の画像を表示する
  document.getElementById("camera-box").src = "./static/processing.jpg"
}

function messageReceive(data) {
  document.getElementById("photo-box").src = data.image_path;

  // 検出したラベルを表示
  const box = document.getElementById("labels-box");
  box.innerHTML = "";
  data.labels.forEach(function (tag) {
    const span = document.createElement("span");
    span.textContent = tag;
    box.appendChild(span);
  });
}


// WebSocketで接続する準備
const ws = io.connect();


// 動体検出したときに呼び出す関数を決める
ws.on("moving", movingReceive);

// 画像パスとラベルを受信したときに呼び出す関数を決める
ws.on("message", messageReceive);

// カメラ映像を受信したときに呼び出す関数を決める
ws.on("camera", cameraReceive);
