// ============================================================
// Step4 - 送信者側スクリプト (sender.js)
// 2FPS に落として遅延・詰まりを防ぐ
// ============================================================

async function start() {
  const stream = await navigator.mediaDevices.getUserMedia({
    video: { width: 320, height: 240, frameRate: 2 }
  });
  document.getElementById("v").srcObject = stream;

  const proto = location.protocol === "https:" ? "wss:" : "ws:";
  const ws = new WebSocket(proto + "//" + location.host + "/ws/sender");

  ws.onopen = () => {
    document.getElementById("st").textContent = "配信中";
    const canvas = document.createElement("canvas");
    canvas.width = 320; canvas.height = 240;
    const ctx = canvas.getContext("2d");
    let sending = false;

    // 500msごと（2FPS）
    setInterval(() => {
      // バッファが溜まっていたら送信しない
      if (ws.readyState !== WebSocket.OPEN || ws.bufferedAmount > 0 || sending) return;
      ctx.drawImage(document.getElementById("v"), 0, 0, 320, 240);
      sending = true;
      ws.send("frame:" + canvas.toDataURL("image/jpeg", 0.5).split(",")[1]);
      sending = false;
    }, 500);
  };

  ws.onclose = () => document.getElementById("st").textContent = "切断";
}
