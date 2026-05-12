const proto = location.protocol === "https:" ? "wss:" : "ws:";
const ws = new WebSocket(proto + "//" + location.host + "/ws/clock");
ws.onopen = () => document.getElementById("st").textContent = "受信中";
ws.onclose = () => document.getElementById("st").textContent = "切断";
ws.onmessage = (e) => document.getElementById("time").textContent = e.data;
