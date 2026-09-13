export const meta = {
  name: 'sashizu-review',
  description: '指図の検分の輪 — 三役(検図・考証・庭方)を並列に、変わった章だけ、指摘は上限10件、最大3巡で止まる',
  whenToUse: '指図を書き終えて検分に出すとき(/kenzu から)。ユーザーに見せる前・実装に入る前。',
  phases: [{ title: '検分' }, { title: '直し' }],
}
// 使い方(/kenzu が組み立てる): args = { estate: 'doi', changed: '<review_gate.py --changed の出力>',
//   roles: ['edo-kenzu','edo-kosho','edo-niwashi'], ledger: '<review_ledger.py show の出力>', rounds: 3 }
// 文字列 'doi' だけでも動く(全役・全章)。
const A = (typeof args === 'string') ? { estate: args.trim().split(/\s+/)[0] } : (args || {})
const estate = A.estate
if (!estate) throw new Error('args.estate(邸名)が要る')
const ROLES = A.roles || ['edo-kenzu', 'edo-kosho', 'edo-niwashi']
const MAXR = A.rounds || 3
const LABEL = { 'edo-kenzu': '検図', 'edo-kosho': '考証', 'edo-niwashi': '庭方' }

const FINDINGS = {
  type: 'object',
  properties: {
    verdict: { type: 'string', enum: ['pass', 'fail', 'advisory'] },
    findings: { type: 'array', maxItems: 10, items: { type: 'object', properties: {
      sev: { type: 'string', enum: ['高', '中', '低'] },
      where: { type: 'string', maxLength: 80 },
      text: { type: 'string', maxLength: 200 },
      chapter: { type: 'string', maxLength: 40 },
    }, required: ['sev', 'where', 'text'] } },
    counts: { type: 'object', properties: { 高: { type: 'integer' }, 中: { type: 'integer' }, 低: { type: 'integer' } },
      required: ['高', '中', '低'] },
    resolved: { type: 'array', items: { type: 'string', maxLength: 120 } },
    truncated: { type: 'integer' },
    summary: { type: 'string', maxLength: 1500 },
  },
  required: ['verdict', 'findings', 'counts', 'truncated', 'summary'],
}

function reviewPrompt(role, round, scope, prev) {
  return [
    `邸: ${estate}。検分の第 ${round} 巡(ユーザー入力なしの上限 ${MAXR} 巡)。`,
    `見る範囲: ${scope}`,
    A.ledger ? `前巡までの台帳(review_ledger.py):\n${A.ledger}` : '',
    prev ? `前巡のあなたの指摘(解消したか継続かを必ず判定する):\n${JSON.stringify(prev.findings)}` : '',
    '規則: 変わった章と前巡の指摘の解消だけを人の目で検める。機械検査(*_check)は生成器が全件走らせているので、',
    'その結果(0件/n件)は読むだけで再実行しない。指摘は重要度順に最大10件、各200字以内。落とした件数は truncated に。',
    'summary は 1,500 字以内で、verdict・件数・上位5件の一行だけ。役名・巡次・検査名を summary に並べない。',
  ].filter(Boolean).join('\n')
}

let scope = A.changed ? `変わった章(review_gate.py --changed):\n${A.changed}` : '全章(初回)'
let prev = {}
const history = []
for (let round = 1; round <= MAXR; round++) {
  const roles = round === 1 ? ROLES : ROLES.filter(r => prev[r] && prev[r].verdict === 'fail')
  const res = await parallel(roles.map(r => () =>
    agent(reviewPrompt(r, round, scope, prev[r]), { agentType: r, label: `${LABEL[r] || r}:${round}巡`, phase: '検分', schema: FINDINGS })))
  const byRole = {}
  roles.forEach((r, i) => { if (res[i]) byRole[r] = res[i] })
  const fails = Object.entries(byRole).filter(([, v]) => v.verdict === 'fail')
  const total = Object.values(byRole).reduce((s, v) => s + v.findings.length, 0)
  const dropped = Object.values(byRole).reduce((s, v) => s + (v.truncated || 0), 0)
  log(`第${round}巡: ${Object.entries(byRole).map(([r, v]) => `${LABEL[r] || r}=${v.verdict}(高${v.counts.高}中${v.counts.中}低${v.counts.低})`).join(' / ')}` +
      (dropped ? ` ／ 上限で落とした指摘 ${dropped} 件` : ''))
  history.push({ round, results: byRole })
  prev = { ...prev, ...byRole }
  if (!fails.length) return { estate, rounds: round, verdict: 'pass', history }
  if (round === MAXR) {
    log(`三巡則: ${MAXR} 巡で止める。decision か blocker を post してユーザーの返事を待つ`)
    return { estate, rounds: round, verdict: 'stopped', open: Object.fromEntries(fails), history }
  }
  const fix = await agent([
    `邸: ${estate}。検分の第 ${round} 巡で次の指摘が出た。指図(json・生成器・kosho.md)を直し、生成器を実行して html を出し直せ。`,
    '設計判断が要る指摘(意匠・史料の読み)は直さず「差し戻し」として列挙する。指図に無い値を発明しない。',
    JSON.stringify(Object.fromEntries(fails.map(([r, v]) => [r, v.findings]))),
    '返答は 1,500 字以内: 直した章の一覧・差し戻しの一覧・実行した生成器の結果(図版数/エラー)。',
  ].join('\n'), { agentType: 'edo-sashizukata', label: `直し:${round}巡`, phase: '直し' })
  scope = `第 ${round} 巡の指摘に対する直し(指図方の返答):\n${fix}\n※ review_gate.py --changed の章の指紋は呼び出し元が次巡の前に更新する`
}
