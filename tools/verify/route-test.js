/* ============================================================================
   route-test.js —— 纯逻辑单元测试（不需要浏览器）
   ----------------------------------------------------------------------------
   用法：node route-test.js      退出码 0 = 全通过
   思路：把状态机里的【纯函数】抽出来单独跑。改路由规则时先跑这个。
   重点：一定覆盖畸形输入 —— 真实世界的 URL 什么都可能是。
   ========================================================================== */

const MAX_INDEX = 2;

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

let fail = 0;
const eq = (a, b) => JSON.stringify(a) === JSON.stringify(b);
function check(label, got, want) {
  const ok = eq(got, want);
  if (!ok) fail++;
  console.log(`  ${ok ? 'PASS' : 'FAIL'}  ${label}`);
  if (!ok) console.log(`        期望 ${JSON.stringify(want)}\n        实际 ${JSON.stringify(got)}`);
}

console.log('\n--- 解析：正常输入 ---');
check('#/', stateFromHash('#/'), { view: 'paper', index: null, drawer: false });
check('(空)', stateFromHash(''), { view: 'paper', index: null, drawer: false });
check('#/p/0', stateFromHash('#/p/0'), { view: 'poster', index: 0, drawer: false });
check('#/p/2/a', stateFromHash('#/p/2/a'), { view: 'poster', index: 2, drawer: true });

console.log('\n--- 解析：畸形输入（必须安全回退到首页）---');
for (const bad of ['#/p/9', '#/p/0/x', '#/garbage', '#/p/1/a/extra', '#/p/', '#/p/a', '#/p/01', '#/p/-1']) {
  check(JSON.stringify(bad), stateFromHash(bad), { view: 'paper', index: null, drawer: false });
}

console.log('\n--- 往返一致性 hashFor(stateFromHash(h)) === h ---');
for (const h of ['#/', '#/p/0', '#/p/1/a', '#/p/2']) {
  check(h, hashFor(stateFromHash(h)), h);
}

console.log(`\n失败 ${fail} 项`);
process.exit(fail ? 1 : 0);
