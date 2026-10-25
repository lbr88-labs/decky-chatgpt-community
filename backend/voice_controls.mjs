const action = process.argv[2];
const controls = {
  "mute-microphone": ["Mute microphone", "Unmute microphone", "Microphone muted"],
  "unmute-microphone": ["Unmute microphone", "Mute microphone", "Microphone unmuted"],
  "mute-speaker": ["Mute speakers", "Unmute speakers", "Speaker muted"],
  "unmute-speaker": ["Unmute speakers", "Mute speakers", "Speaker unmuted"],
};

async function fail(message) {
  process.stdout.write(`${JSON.stringify({ ok: false, message })}\n`);
  process.exitCode = 1;
}

if (!(action in controls)) {
  await fail("Unknown voice control");
} else {
  try {
    const targets = await fetch("http://127.0.0.1:9223/json/list").then((response) => response.json());
    const target = targets.find((entry) => entry.type === "page" && entry.webSocketDebuggerUrl);
    if (!target) throw new Error("ChatGPT control surface is unavailable");
    const [clickLabel, alreadyLabel, message] = controls[action];
    const expression = `(() => {
      const buttons = [...document.querySelectorAll('button[aria-label]')];
      const label = (value) => value.trim().toLowerCase();
      if (buttons.some((button) => label(button.getAttribute('aria-label') || '') === label(${JSON.stringify(alreadyLabel)}))) return 'already';
      const button = buttons.find((button) => label(button.getAttribute('aria-label') || '') === label(${JSON.stringify(clickLabel)}));
      if (!button) return 'unavailable';
      button.click();
      return 'changed';
    })()`;
    const socket = new WebSocket(target.webSocketDebuggerUrl);
    const response = await new Promise((resolve, reject) => {
      const timeout = setTimeout(() => reject(new Error("ChatGPT did not respond")), 3000);
      socket.addEventListener("open", () => socket.send(JSON.stringify({
        id: 1,
        method: "Runtime.evaluate",
        params: { expression, returnByValue: true },
      })));
      socket.addEventListener("message", (event) => {
        const data = JSON.parse(String(event.data));
        if (data.id !== 1) return;
        clearTimeout(timeout);
        resolve(data);
      });
      socket.addEventListener("error", () => reject(new Error("ChatGPT control connection failed")));
    });
    socket.close();
    const value = response?.result?.result?.value;
    if (value === "unavailable") throw new Error("Start ChatGPT Voice Mode first");
    if (value !== "changed" && value !== "already") throw new Error("ChatGPT rejected the voice control");
    process.stdout.write(`${JSON.stringify({ ok: true, message: value === "already" ? `${message} already` : message })}\n`);
  } catch (error) {
    await fail(error instanceof Error ? error.message : "Voice control failed");
  }
}
