/* ============================================================================
   example-flow-test.js —— 交互链路测试模板
   ----------------------------------------------------------------------------
   契约：本脚本运行结束后必须写
        document.body.setAttribute('data-test-result', '…')
   格式约定（flow-test.ps1 会据此着色）：
        'OK:<说明>'  = 通过
        'XX:<说明>'  = 失败
        其它         = 附注（灰字）
   多项之间用 ' ;; ' 分隔。

   当前这份是按 soviet-press 的 DOM 约定写的（body[data-view] / body[data-drawer]）。
   换成别的项目时，改 chk() 的读取方式和选择器即可。
   ========================================================================== */
(async function () {
  const out = [];
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

  // 捕获运行期错误：不加这个，脚本一抛异常页面就是空白，你连"失败了"都看不出来
  const errs = [];
  window.addEventListener('error', (e) => errs.push(String(e.message)));

  // —— 按项目改这里 ——
  const snap = () => document.body.dataset.view + '/' + document.body.dataset.drawer;
  const visible = () =>
    ['view-paper', 'view-p0', 'view-p1', 'view-p2']
      .filter((id) => !document.getElementById(id).hidden)
      .join(',');
  const chk = (label, expected) => {
    const got = snap() + '|' + visible();
    out.push((got.indexOf(expected) === 0 ? 'OK:' : 'XX:') + label + ' = ' + got);
  };

  try {
    await sleep(400);
    chk('1 初始态', 'paper/closed|view-paper');

    document.querySelector('[data-goto="0"]').click();
    await sleep(1600);
    chk('2 点击板块进入海报', 'poster/closed|view-p0');

    document.querySelector('#view-p0 .drawer__bar').click();
    await sleep(1600);
    chk('3 点击文章条展开', 'poster/open|view-p0');

    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
    await sleep(1600);
    chk('4 ESC 收回文章', 'poster/closed|view-p0');

    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
    await sleep(2000);
    chk('5 ESC 退回报纸', 'paper/closed|view-paper');

    // 换一个板块，确认不是只对 0 号有效
    document.querySelector('[data-goto="2"]').click();
    await sleep(1600);
    chk('6 另一个板块同样可用', 'poster/closed|view-p2');

    // ← 整屏覆盖层必须验"归位"，这是最容易变成线上事故的一条。
    //    ⚠️ 必须【轮询】：转场收尾是异步的，只读一次会得到假失败。
    const wipe = document.getElementById('wipe');
    if (wipe) {
      let cp = '';
      for (let i = 0; i < 40; i++) {                 // 最多等 4s
        cp = getComputedStyle(wipe).clipPath;
        if (cp.indexOf('100% 100%') < 0) break;      // 不含满屏面积 = 已归位
        await sleep(100);
      }
      const ok = cp.indexOf('100% 100%') < 0;
      out.push((ok ? 'OK:' : 'XX:') + '7 转场层已归位 = ' + cp);
    }
  } catch (e) {
    out.push('XX:脚本抛异常 = ' + e.message);
  }

  out.push('附注: 运行期错误 = ' + (errs.join(';') || '无'));
  document.body.setAttribute('data-test-result', out.join(' ;; '));
})();
