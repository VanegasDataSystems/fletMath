// fletMath web sound engine (static web build only).
// Python runs in a Web Worker (Pyodide) and posts "preload:a,b,..." / "play:name" on a BroadcastChannel;
// this page-side script plays pre-decoded Web Audio buffers, which start almost instantly on iOS,
// unlike the <audio> element behind flet-audio. Injected into index.html by scripts/patch_web.py.
(() => {
  const AC = window.AudioContext || window.webkitAudioContext;
  if (!AC || !window.BroadcastChannel) return;
  const ctx = new AC({ latencyHint: "interactive" });
  // play through the silent switch like the <audio> element did; the in-app Sounds switch is the mute
  try { if (navigator.audioSession) navigator.audioSession.type = "playback"; } catch (e) {}

  const buffers = new Map();
  const loading = new Map();

  function load(name) {
    if (!loading.has(name)) {
      loading.set(name, fetch(`sounds/${name}.wav`)
        .then((r) => r.arrayBuffer())
        .then((data) => new Promise((ok, fail) => ctx.decodeAudioData(data, ok, fail)))
        .then((buf) => { buffers.set(name, buf); })
        .catch(() => { loading.delete(name); }));
    }
    return loading.get(name);
  }

  function start(buf) {
    const src = ctx.createBufferSource();
    src.buffer = buf;
    src.connect(ctx.destination);
    src.start(0);
  }

  // iOS keeps the context suspended until a touch; resume (and prime with silence) on every touch
  // until it runs - it can be suspended again by a call or another app
  function unlock() {
    if (ctx.state === "running") return;
    ctx.resume();
    start(ctx.createBuffer(1, 1, 22050));
  }
  for (const type of ["pointerdown", "touchend", "keydown"]) {
    document.addEventListener(type, unlock, { capture: true, passive: true });
  }

  function play(name) {
    const buf = buffers.get(name);
    if (!buf) { load(name); return; }  // not decoded yet: skip rather than play late
    if (ctx.state !== "running") ctx.resume();
    start(buf);
  }

  const channel = new BroadcastChannel("fletmath-sfx");
  channel.onmessage = (event) => {
    const msg = String(event.data);
    const sep = msg.indexOf(":");
    const verb = msg.slice(0, sep);
    const arg = msg.slice(sep + 1);
    if (verb === "preload") arg.split(",").forEach(load);
    else if (verb === "play") play(arg);
  };
})();
