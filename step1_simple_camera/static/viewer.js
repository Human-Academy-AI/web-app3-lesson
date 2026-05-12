const proto = location.protocol === "https:" ? "wss:" : "ws:";
const ws = new WebSocket(proto + "//" + location.host + "/ws/viewer");
ws.onopen = () => document.getElementById("st").textContent = "受信中";
ws.onclose = () => document.getElementById("st").textContent = "切断";
ws.onmessage = (e) => {
  if (e.data.startsWith("frame:"))
    document.getElementById("feed").src = "data:image/jpeg;base64," + e.data.slice(6);
};
