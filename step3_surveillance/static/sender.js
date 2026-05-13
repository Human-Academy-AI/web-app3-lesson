// ============================================================
// Step3 リモート監視カメラ - 送信者側スクリプト (sender.js)
//
// 【役割】
//   Step1の sender.js とほぼ同じ。
//   PCのカメラ映像をJPEGに変換してWebSocketでサーバーへ送り続ける。
//   動体検知はサーバー側（OpenCV）が行うため、
//   このファイルは「映像を送るだけ」のシンプルな役割。
// ============================================================

async function start() {

  // PCカメラを起動（320x240、5FPS）
  const stream = await navigator.mediaDevices.getUserMedia({
    video: { width: 320, height: 240, frameRate: 5 }
  });
  document.getElementById("v").srcObject = stream;

  // --- WebSocket 接続の確立 ---
  const proto = location.protocol === "https:" ? "wss:" : "ws:";
  const ws = new WebSocket(proto + "//" + location.host + "/ws/sender");
  //                                                       ^^^^^^^^^
  //                    Step1と違い /ws/sender に接続（送信専用エンドポイント）

  // --- WebSocket イベント：接続が開いたとき ---
  ws.onopen = () => {
    document.getElementById("st").textContent = "配信中";

    const canvas = document.createElement("canvas");
    canvas.width = 320;
    canvas.height = 240;
    const ctx = canvas.getContext("2d");
    let sending = false;

    // 200msごと（5FPS）にフレームを送信
    setInterval(() => {
      if (ws.readyState !== WebSocket.OPEN || sending) return;
      ctx.drawImage(document.getElementById("v"), 0, 0, 320, 240);
      sending = true;

      // --- WebSocket でフレームを送信 ---
      // "frame:" + Base64文字列 をサーバーへ送る
      // サーバーの ws_sender() がこれを受け取り process() で処理する
      ws.send("frame:" + canvas.toDataURL("image/jpeg", 0.5).split(",")[1]);

      sending = false;
    }, 1000 / 5);
  };

  // --- WebSocket イベント：接続が閉じたとき ---
  ws.onclose = () => document.getElementById("st").textContent = "切断";
}
