let total = 0;
const seen = new Set();
const proto = location.protocol === "https:" ? "wss:" : "ws:";
const ws = new WebSocket(proto + "//" + location.host + "/ws/viewer");
ws.onopen = () => document.getElementById("st").textContent = "監視中";
ws.onclose = () => document.getElementById("st").textContent = "切断";
ws.onmessage = (e) => {
  const d = e.data;
  if (d.startsWith("live:")) {
    document.getElementById("feed").src = "data:image/jpeg;base64," + d.slice(5);
  } else if (d.startsWith("time:")) {
    document.getElementById("time").textContent = d.slice(5);
  } else if (d.startsWith("alert:")) {
    const a = JSON.parse(d.slice(6));
    if (seen.has(a.id)) return;
    seen.add(a.id);
    total++;
    document.getElementById("cnt").textContent = total;
    const div = document.createElement("div");
    div.innerHTML = "<p><b>#" + a.id + " " + a.ts + "</b></p><img src='data:image/jpeg;base64," + a.img + "' style='width:100%;max-width:320px'><hr>";
    document.getElementById("log").prepend(div);
  }
};
