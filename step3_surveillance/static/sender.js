async function start() {
  const stream = await navigator.mediaDevices.getUserMedia({video:{width:320,height:240,frameRate:5}});
  document.getElementById("v").srcObject = stream;
  const proto = location.protocol === "https:" ? "wss:" : "ws:";
  const ws = new WebSocket(proto + "//" + location.host + "/ws/sender");
  ws.onopen = () => {
    document.getElementById("st").textContent = "配信中";
    const canvas = document.createElement("canvas");
    canvas.width = 320; canvas.height = 240;
    const ctx = canvas.getContext("2d");
    let sending = false;
    setInterval(() => {
      if (ws.readyState !== WebSocket.OPEN || sending) return;
      ctx.drawImage(document.getElementById("v"), 0, 0, 320, 240);
      sending = true;
      ws.send("frame:" + canvas.toDataURL("image/jpeg", 0.5).split(",")[1]);
      sending = false;
    }, 1000 / 5);
  };
  ws.onclose = () => document.getElementById("st").textContent = "切断";
}
