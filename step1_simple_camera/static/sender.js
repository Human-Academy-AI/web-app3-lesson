// ============================================================
// Step1 シンプルカメラ - 送信者側スクリプト (sender.js)
//
// 【役割】
//   PCのWebカメラを起動し、映像フレームをJPEG画像に変換して
//   WebSocketでサーバーへ送り続ける
// ============================================================

async function start() {

  // PCのカメラを起動（320x240、5FPS）
  const stream = await navigator.mediaDevices.getUserMedia({
    video: { width: 320, height: 240, frameRate: 5 }
  });
  document.getElementById("v").srcObject = stream;


  // --- WebSocket 接続の確立 ---
  // new WebSocket(url) でサーバーへの接続を開始する
  // 通常のHTTP fetch() と違い、一度つなぐと切れるまで接続が維持される
  // https の場合は wss（暗号化あり）、http の場合は ws を使う
  const proto = location.protocol === "https:" ? "wss:" : "ws:";
  const ws = new WebSocket(proto + "//" + location.host + "/ws/sender");
  //                                                       ^^^^^^^^^^
  //                        サーバーの /ws/sender エンドポイントに接続


  // --- WebSocket イベント：接続が開いたとき ---
  // onopen はサーバーとのハンドシェイクが完了し
  // データを送受信できる状態になったときに1回だけ呼ばれる
  ws.onopen = () => {
    document.getElementById("st").textContent = "配信中";

    // フレームを描画するための透明なキャンバスを作成
    const canvas = document.createElement("canvas");
    canvas.width = 320;
    canvas.height = 240;
    const ctx = canvas.getContext("2d");

    // 前のフレームの送信が終わっていない間はスキップするフラグ
    let sending = false;

    // 200msごと（5FPS）に映像フレームを送信するループ
    setInterval(() => {

      // --- WebSocket の状態チェック ---
      // ws.readyState は接続状態を表す数値
      //   0: CONNECTING（接続中）
      //   1: OPEN（接続済み・送受信可能）← 送信できるのはこの状態だけ
      //   2: CLOSING（切断中）
      //   3: CLOSED（切断済み）
      if (ws.readyState !== WebSocket.OPEN || sending) return;

      // <video> の現在フレームをキャンバスに描画してJPEGに変換
      ctx.drawImage(document.getElementById("v"), 0, 0, 320, 240);

      sending = true;

      // --- WebSocket でデータを送信 ---
      // ws.send() で文字列やバイナリをサーバーへ送れる
      // ここでは "frame:" + Base64文字列 の形式で送っている
      // サーバー側は先頭の "frame:" を見てフレームデータだと判断する
      ws.send("frame:" + canvas.toDataURL("image/jpeg", 0.5).split(",")[1]);
      //       ^^^^^^^^  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
      //       識別子      JPEG画像をBase64テキストに変換（","の後ろだけ取り出す）

      sending = false;

    }, 1000 / 5);
  };


  // --- WebSocket イベント：接続が閉じたとき ---
  // onclose はサーバーから切断されたとき、またはブラウザを閉じたときに呼ばれる
  ws.onclose = () => document.getElementById("st").textContent = "切断";
}
