function clockReceive(data) {
  document.getElementById("date").innerText = data;
}

// WebSocketの通信準備
const ws = io.connect();

// 時刻を受信したときに呼び出す関数を決める
ws.on("message", clockReceive);
