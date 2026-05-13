// ============================================================
// Step1 シンプルカメラ - 視聴者側スクリプト (viewer.js)
//
// 【役割】
//   WebSocketでサーバーに接続し、
//   送られてくるJPEG画像を <img> タグに表示し続ける
// ============================================================

// --- WebSocket 接続の確立 ---
// ページが読み込まれた瞬間に自動で接続を開始する
// （ボタンを押さなくても自動でつながる）
const proto = location.protocol === "https:" ? "wss:" : "ws:";
const ws = new WebSocket(proto + "//" + location.host + "/ws/viewer");
//                                                       ^^^^^^^^^^
//                        サーバーの /ws/viewer エンドポイントに接続


// --- WebSocket イベント：接続が開いたとき ---
ws.onopen = () => document.getElementById("st").textContent = "受信中";


// --- WebSocket イベント：接続が閉じたとき ---
ws.onclose = () => document.getElementById("st").textContent = "切断";


// --- WebSocket イベント：サーバーからメッセージが届いたとき ---
// onmessage はサーバーからデータが送られてくるたびに呼ばれる
// 映像が5FPSで送られるなら、1秒間に5回呼ばれる
// e.data に届いたデータ（文字列）が入っている
ws.onmessage = (e) => {

  // メッセージの先頭が "frame:" なら映像フレームデータ
  // startsWith() で先頭文字列を確認する
  if (e.data.startsWith("frame:")) {

    // "frame:" の6文字を除いたBase64文字列をJPEGとして <img> に表示
    // data:image/jpeg;base64,... という形式がブラウザの画像表示フォーマット
    document.getElementById("feed").src =
      "data:image/jpeg;base64," + e.data.slice(6);
    //                                      ^^^^^^
    //            slice(6) で先頭6文字（"frame:"）を取り除く
  }
};
