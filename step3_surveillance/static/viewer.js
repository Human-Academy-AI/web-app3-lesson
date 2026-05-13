// ============================================================
// Step3 リモート監視カメラ - 視聴者側スクリプト (viewer.js)
//
// 【役割】
//   サーバーから3種類のメッセージをWebSocketで受け取って処理する
//
// 【受け取るメッセージの種類】
//   "live:"  + Base64画像  → <img> に表示（ライブ映像）
//   "time:"  + 時刻文字列  → 画面の時計を更新
//   "alert:" + JSON文字列  → 検知ログに画像と時刻を追加
// ============================================================

let total = 0;
const seen = new Set();  // 表示済みアラートIDを記録（重複防止）

// --- WebSocket 接続の確立 ---
const proto = location.protocol === "https:" ? "wss:" : "ws:";
const ws = new WebSocket(proto + "//" + location.host + "/ws/viewer");
//                                                       ^^^^^^^^^^
//                    /ws/viewer に接続（視聴専用エンドポイント）

// --- WebSocket イベント：接続が開いたとき ---
ws.onopen  = () => document.getElementById("st").textContent = "監視中";

// --- WebSocket イベント：接続が閉じたとき ---
ws.onclose = () => document.getElementById("st").textContent = "切断";

// --- WebSocket イベント：サーバーからメッセージが届いたとき ---
// サーバーが broadcast() で ws.send() を呼ぶたびにここが動く
// 1秒間に5回（ライブ映像）＋ 5回（時刻）＋ 検知時に1回（アラート）呼ばれる
ws.onmessage = (e) => {
  const d = e.data;  // 届いたデータ文字列

  // メッセージの先頭（プレフィックス）で種類を判別する
  // サーバー側で broadcast("live:...") / broadcast("time:...") のように
  // 先頭に識別子をつけて送っているため、ここで振り分けられる

  // ── ① "live:" → ライブ映像フレーム ─────────────────────
  if (d.startsWith("live:")) {
    document.getElementById("feed").src =
      "data:image/jpeg;base64," + d.slice(5);
    //                              ^^^^^^^
    //          slice(5) で "live:" の5文字を除いたBase64部分だけ取り出す

  // ── ② "time:" → 時刻文字列 ──────────────────────────────
  // Step2と同じ仕組み。サーバーが100msごとではなくフレームごとに送っている
  } else if (d.startsWith("time:")) {
    document.getElementById("time").textContent = d.slice(5);

  // ── ③ "alert:" → 動体検知アラート ───────────────────────
  // 検知があったとき、またはページを開いた直後（過去ログ受信）に届く
  } else if (d.startsWith("alert:")) {

    // "alert:" を除いた部分はJSON文字列
    // JSON.parse() でオブジェクトに変換する
    // 例: { id: 1, ts: "12:34:56.789", img: "Base64文字列..." }
    const a = JSON.parse(d.slice(6));

    // すでに表示済みのIDはスキップ
    // （ページを開いた直後に過去ログが再送されるため重複チェックが必要）
    if (seen.has(a.id)) return;
    seen.add(a.id);

    total++;
    document.getElementById("cnt").textContent = total;

    // 検知カードを作成してログエリアの先頭に追加（新しいものが上）
    const div = document.createElement("div");
    div.innerHTML =
      "<p><b>#" + a.id + " " + a.ts + "</b></p>" +
      "<img src='data:image/jpeg;base64," + a.img +
      "' style='width:100%;max-width:320px'><hr>";
    document.getElementById("log").prepend(div);
  }
};
