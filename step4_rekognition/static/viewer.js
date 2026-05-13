// ============================================================
// Step4 - 視聴者側スクリプト (viewer.js)
//
// 【Step3からの変更点】
//   "alert:" メッセージに labels（認識結果テキスト）が追加された
//   画像オーバーレイなし。ラベルをテキストで表示するだけ。
// ============================================================

let total = 0;
const seen = new Set();

const proto = location.protocol === "https:" ? "wss:" : "ws:";
const ws = new WebSocket(proto + "//" + location.host + "/ws/viewer");

ws.onopen  = () => document.getElementById("st").textContent = "監視中";
ws.onclose = () => document.getElementById("st").textContent = "切断";

ws.onmessage = (e) => {
  const d = e.data;

  // ── ① ライブ映像フレーム ──────────────────────────────
  if (d.startsWith("live:")) {
    document.getElementById("feed").src =
      "data:image/jpeg;base64," + d.slice(5);

  // ── ② 時刻 ────────────────────────────────────────────
  } else if (d.startsWith("time:")) {
    document.getElementById("time").textContent = d.slice(5);

  // ── ③ 動体検知アラート ───────────────────────────────
  } else if (d.startsWith("alert:")) {
    const a = JSON.parse(d.slice(6));
    if (seen.has(a.id)) {
      // すでに表示済みのカードにRekognitionの結果だけ追記する
      const existing = document.getElementById("alert-" + a.id);
      if (existing && a.labels && a.labels.length > 0) {
        existing.querySelector(".labels").innerHTML = labelsHtml(a.labels);
      }
      return;
    }
    seen.add(a.id);
    total++;
    document.getElementById("cnt").textContent = total;

    const div = document.createElement("div");
    div.id = "alert-" + a.id;
    div.innerHTML =
      "<p><b>#" + a.id + " " + a.ts + "</b></p>" +
      "<img src='data:image/jpeg;base64," + a.img +
        "' style='width:100%;max-width:320px'>" +
      "<p><b>Rekognition認識結果:</b></p>" +
      "<p class='labels'>" +
        (a.labels && a.labels.length > 0 ? labelsHtml(a.labels) : "認識中...") +
      "</p><hr>";
    document.getElementById("log").prepend(div);
  }
};

// ラベルをバッジ形式のHTML文字列に変換する
function labelsHtml(labels) {
  return labels.map(l =>
    "<span style='margin:2px;padding:2px 6px;background:#eee;border-radius:3px;display:inline-block'>" +
    l.name + " " + l.confidence + "%" +
    "</span>"
  ).join("");
}
