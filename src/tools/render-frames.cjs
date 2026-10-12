/* ============================================================================
   离线逐帧渲染 · render-frames.cjs
   ----------------------------------------------------------------------------
   为什么不在浏览器里"在线播放 + 录屏"：
   在线播放要同时跟合成器、光栅线程、垂直同步赛跑，任何一环抖动都直接进画面。
   离线逐帧渲染把"时间"变成参数：每一帧按精确的 t 单独渲染，编码器按固定
   帧率输出，时序由编码器保证，与浏览器调度无关。

   用法（先由外部启动好带调试端口的 Chrome）：
     1) 启动 Chrome：
        chrome.exe --headless=new --remote-debugging-port=9223 --window-size=1920,1080 \
          --force-device-scale-factor=1 --user-data-dir=<临时目录> \
          "file:///<绝对路径>/constructivism-motion-20s.html?pure=1&hud=0"
     2) node render-frames.cjs 9223 <输出目录> [fps] [总帧数] [起始帧] [帧数]
        例：node render-frames.cjs 9223 frames 30 600

   帧 i 对应 t = i / fps。总帧数 = fps × 时长（20s）：30fps → 600 帧，
   最后一帧是 t = 599/30 = 19.9667s，不含 t=20s（它等于 0s），因此循环无缝。
   ========================================================================== */
'use strict';
const fs = require('fs');
const path = require('path');

const port      = process.argv[2] || '9223';
const outDir    = process.argv[3] || 'frames';
const fps       = parseInt(process.argv[4] || '30', 10);
const total     = parseInt(process.argv[5] || String(fps * 20), 10);
const fromFrame = parseInt(process.argv[6] || '0', 10);
const count     = parseInt(process.argv[7] || String(total - fromFrame), 10);
const vw        = parseInt(process.argv[8] || '1920', 10);
const vh        = parseInt(process.argv[9] || '1080', 10);

const sleep = ms => new Promise(r => setTimeout(r, ms));

async function findPage(port){
  for(let i = 0; i < 60; i++){
    try{
      const res = await fetch(`http://127.0.0.1:${port}/json/list`);
      const list = await res.json();
      const p = list.find(t => t.type === 'page' && t.webSocketDebuggerUrl);
      if(p) return p;
    }catch(e){ /* 端口还没起来 */ }
    await sleep(250);
  }
  throw new Error('CDP 目标未就绪：确认 Chrome 带 --remote-debugging-port 启动');
}

async function main(){
  const page = await findPage(port);
  const ws = new WebSocket(page.webSocketDebuggerUrl);
  let seq = 0;
  const waiting = new Map();

  ws.addEventListener('message', ev => {
    const m = JSON.parse(ev.data);
    if(m.id && waiting.has(m.id)){
      const slot = waiting.get(m.id);
      waiting.delete(m.id);
      m.error ? slot.rej(new Error(JSON.stringify(m.error))) : slot.res(m.result);
    }
  });
  await new Promise((res, rej) => { ws.addEventListener('open', res); ws.addEventListener('error', rej); });

  const send = (method, params) => new Promise((res, rej) => {
    const myId = ++seq;
    waiting.set(myId, { res, rej });
    ws.send(JSON.stringify({ id: myId, method, params: params || {} }));
  });

  await send('Page.enable');
  await send('Runtime.enable');
  /* ⚠️ 关键：--window-size 设的是**窗口**尺寸，无头下视口会比它小（实测 1920×1080 的窗口
     只得到 1898×926 的视口），于是页面里的等比缩放会把画布缩到 85.7% 并留黑边。
     必须用 CDP 强制视口尺寸，才能得到 1:1 的 1920×1080 画面。 */
  await send('Emulation.setDeviceMetricsOverride', {
    width: vw, height: vh, deviceScaleFactor: 1, mobile: false
  });
  await sleep(300);   /* 等 resize → fit() 重新计算缩放 */
  const vp = await send('Runtime.evaluate', {
    expression: 'JSON.stringify([window.innerWidth, window.innerHeight, window.__scale || 0])',
    returnByValue: true });
  console.log('viewport =', vp.result.value, '(期望 [1920,1080,1])');
  /* 等字体加载完成：webfont 未就绪时抓到的帧会掉字体 */
  await send('Runtime.evaluate', { expression: 'document.fonts.ready.then(()=>1)', awaitPromise: true });
  const chk = await send('Runtime.evaluate', {
    expression: 'typeof window.__seek === "function"', returnByValue: true });
  if(!chk.result.value) throw new Error('页面缺少 window.__seek（请用新版 constructivism-motion-20s.html）');

  fs.mkdirSync(outDir, { recursive: true });
  const t0 = Date.now();

  for(let n = 0; n < count; n++){
    const i = fromFrame + n;
    const t = i / fps;
    await send('Runtime.evaluate', {
      expression: `window.__seek(${t.toFixed(5)})`, awaitPromise: true });
    const shot = await send('Page.captureScreenshot', { format: 'png', fromSurface: true });
    fs.writeFileSync(
      path.join(outDir, 'frame_' + String(i).padStart(4, '0') + '.png'),
      Buffer.from(shot.data, 'base64'));
    if(n % 25 === 0 || n === count - 1){
      console.log(`frame ${i}/${total - 1}  t=${t.toFixed(3)}s  elapsed=${((Date.now()-t0)/1000).toFixed(1)}s`);
    }
  }

  ws.close();
  console.log(`RENDER_DONE ${count} frames -> ${outDir}`);
}

main().catch(e => { console.error('RENDER_ERR', e.message); process.exit(1); });
