// ============================================================
// Step2 時刻アプリ - クライアント側スクリプト (clock.js)
//
// 【役割】
//   WebSocketでサーバーに接続し、
//   100msごとに送られてくる時刻文字列を画面に表示する
//
// 【ポイント】
//   HTTPの場合は自分でリクエストしないとデータが来ない
//   WebSocketはサーバーが勝手に送ってくる → onmessage が自動で呼ばれる
// ============================================================

const proto = location.protocol === "https:" ? "wss:" : "ws:";

// --- WebSocket 接続の確立 ---
// ページを開いた瞬間にサーバーへ接続を試みる
const ws = new WebSocket(proto + "//" + location.host + "/ws/clock");


// --- WebSocket イベント：接続が開いたとき ---
ws.onopen = () => document.getElementById("st").textContent = "受信中";


// --- WebSocket イベント：接続が閉じたとき ---
ws.onclose = () => document.getElementById("st").textContent = "切断";


// --- WebSocket イベント：サーバーからメッセージが届いたとき ---
// サーバーが ws.send(ts) を呼ぶたびに、こちらの onmessage が自動で呼ばれる
// HTTPのようにこちらからリクエストしていないのに受け取れる＝「サーバープッシュ」
// e.data にはサーバーから送られた文字列（例: "12:34:56.789"）が入っている
ws.onmessage = (e) => document.getElementById("time").textContent = e.data;
//                                                                   ^^^^^^
//                                          届いた時刻文字列をそのまま表示するだけ
