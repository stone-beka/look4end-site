/* ============================================================================
   press.js — 报纸 / 海报 / 文章抽屉 的两级状态机
   ----------------------------------------------------------------------------
   设计原则：
   1. 状态由 history 驱动，不是由点击驱动。ESC 与浏览器后退键调用同一条路径，
      所以两者行为必然一致（「粗野主义 Web」的诚实原则：返回键要如预期工作）。
   2. 所有视图切换经过一次红色硬边擦除，符合构成主义的"硬切"语汇。
   3. 尊重 prefers-reduced-motion：开启时跳过擦除，直接切换。
   4. 转场用「最新状态胜出」的循环，而不是"忙就丢弃"——
      否则连点两下会让 history 与 DOM 脱节。
   ========================================================================== */
(() => {
  'use strict';

  const body     = document.body;
  const wipeEl   = document.getElementById('wipe');
  const liveEl   = document.getElementById('live');
  const mainEl   = document.getElementById('main');
  const reduceMQ = window.matchMedia('(prefers-reduced-motion: reduce)');

  const views = {
    paper: document.getElementById('view-paper'),
    '0':   document.getElementById('view-p0'),
    '1':   document.getElementById('view-p1'),
    '2':   document.getElementById('view-p2'),
  };

  const PAPER = { view: 'paper', index: null, drawer: false };
  const MAX_INDEX = 2;

  /* ---------- 状态 <-> 路由 ---------- */

  const hashFor = (s) => (s.view !== 'poster' ? '#/' : `#/p/${s.index}${s.drawer ? '/a' : ''}`);

  function stateFromHash(hash) {
    const m = /^#\/p\/(\d)(\/a)?$/.exec(hash || '');
    if (m) {
      const index = Number(m[1]);
      if (index >= 0 && index <= MAX_INDEX) {
        return { view: 'poster', index, drawer: Boolean(m[2]) };
      }
    }
    return { view: 'paper', index: null, drawer: false };
  }

  /* ---------- 应用状态到 DOM ---------- */

  let state = { view: 'paper', index: null, drawer: false };
  let desired = null;          // 最近一次"请求"的状态（转场结束前先于 state 更新）
  let returnFocusEl = null;    // 退回报纸时把焦点还给谁

  function apply(next) {
    state = next;
    body.dataset.view = next.view;
    body.dataset.drawer = next.drawer ? 'open' : 'closed';

    const activeKey = next.view === 'paper' ? 'paper' : String(next.index);
    for (const key of Object.keys(views)) {
      const el = views[key];
      if (el) el.hidden = key !== activeKey;
    }

    document.querySelectorAll('.drawer__bar').forEach((btn) => {
      btn.setAttribute('aria-expanded', String(next.drawer));
    });

    announce(next);
  }

  function announce(s) {
    if (!liveEl) return;
    if (s.view === 'paper') {
      liveEl.textContent = '已退回报纸首页';
      return;
    }
    const titleEl = views[String(s.index)]?.querySelector('.drawer__title');
    const title = titleEl ? titleEl.textContent.trim() : '';
    liveEl.textContent = s.drawer
      ? `已展开文章：${title}。按 Escape 收回文章。`
      : `已进入海报：${title}。按 Escape 退回报纸首页。`;
  }

  /* ---------- 焦点管理 ---------- */

  function focusView(s) {
    if (s.view === 'paper') {
      const target = (returnFocusEl && document.contains(returnFocusEl))
        ? returnFocusEl
        : document.querySelector('.block__link');
      if (target) target.focus();
      return;
    }
    const el = views[String(s.index)];
    if (el) el.focus({ preventScroll: true });
  }

  /* ---------- 转场 ---------- */

  function afterTransition(el, fallbackMs = 700) {
    return new Promise((resolve) => {
      let done = false;
      const finish = () => {
        if (done) return;
        done = true;
        el.removeEventListener('transitionend', onEnd);
        resolve();
      };
      // 红色幕布动的是 clip-path（Block Invasion 那版动的是 transform）
      const onEnd = (e) => {
        if (e.target === el && e.propertyName === 'clip-path') finish();
      };
      el.addEventListener('transitionend', onEnd);
      // 兜底：标签页不可见时 transitionend 可能缺席
      setTimeout(finish, fallbackMs);
    });
  }

  let pending = null;
  let running = false;

  async function transitionTo(next) {
    desired = next;
    pending = next;
    if (running) return;          // 已有转场在跑，它会处理新的 pending

    running = true;
    try {
      while (pending) {
        const target = pending;
        pending = null;

        if (reduceMQ.matches || !wipeEl) {
          apply(target);
          focusView(target);
          continue;
        }

        wipeEl.classList.add('is-in');
        await afterTransition(wipeEl);

        apply(target);
        focusView(target);

        // 幕布收拢到底边退场；再清空 .is-out 时两端都是"零面积"，
        // 所以回到初始态不会产生可见的二次扫过。
        wipeEl.classList.remove('is-in');
        wipeEl.classList.add('is-out');
        await afterTransition(wipeEl);
        wipeEl.classList.remove('is-out');
      }
    } finally {
      running = false;
    }
  }

  /* ---------- 导航 ---------- */

  function navigate(next, { replace = false } = {}) {
    const snapshot = { view: next.view, index: next.index, drawer: next.drawer };
    const hash = hashFor(snapshot);
    if (replace) history.replaceState(snapshot, '', hash);
    else history.pushState(snapshot, '', hash);
    transitionTo(snapshot);
  }

  /* ---------- 事件绑定 ---------- */

  document.querySelectorAll('[data-goto]').forEach((a) => {
    a.addEventListener('click', (e) => {
      e.preventDefault();
      returnFocusEl = a;
      navigate({ view: 'poster', index: Number(a.dataset.goto), drawer: false });
    });
  });

  document.querySelectorAll('.drawer__bar').forEach((btn) => {
    btn.addEventListener('click', () => {
      const view = btn.closest('.view--poster');
      if (!view) return;
      const index = Number(view.dataset.index);
      // 用「最近一次请求的状态」判断，避免转场途中 state 尚未更新导致的抖动
      const cur = desired || state;
      const isOpen = cur.drawer && cur.index === index;
      navigate({ view: 'poster', index, drawer: !isOpen });
    });
  });

  // ESC —— 与浏览器后退键走同一条路径
  document.addEventListener('keydown', (e) => {
    if (e.key !== 'Escape' && e.key !== 'Esc') return;
    if ((desired || state).view === 'paper') return;   // 报纸是顶层
    e.preventDefault();
    history.back();
  });

  window.addEventListener('popstate', (e) => {
    const next = (e.state && typeof e.state.view === 'string')
      ? e.state
      : stateFromHash(location.hash);
    transitionTo(next);
  });

  // 手动改 hash（粘链接）时也能对上
  window.addEventListener('hashchange', () => {
    const fromHash = stateFromHash(location.hash);
    if (hashFor(fromHash) !== hashFor(desired || state)) transitionTo(fromHash);
  });

  /* ---------- 初始化 ---------- */

  function init() {
    if (mainEl) mainEl.tabIndex = -1;

    // 海报视图必须可编程聚焦，才能承接焦点
    document.querySelectorAll('.view--poster').forEach((v) => { v.tabIndex = -1; });

    const initial = stateFromHash(location.hash);

    // 保证 ESC / 后退始终有层级可退：栈底先压入"报纸"
    if (initial.view !== 'paper') {
      history.replaceState({ view: 'paper', index: null, drawer: false }, '', '#/');
      if (initial.drawer) {
        const posterOnly = { view: 'poster', index: initial.index, drawer: false };
        history.pushState(posterOnly, '', hashFor(posterOnly));
      }
      history.pushState({ ...initial }, '', hashFor(initial));
    } else {
      history.replaceState({ view: 'paper', index: null, drawer: false }, '', '#/');
    }

    apply(initial);
    if (initial.view !== 'paper') focusView(initial);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
