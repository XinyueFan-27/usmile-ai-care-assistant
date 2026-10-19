// usmile AI 护齿助手 Demo 前端逻辑（个人作品集项目，非 usmile 官方，未上线）。
// 页面结构与交互来自 prototype/index.html（Melody 定稿）；这里只把占位换成后端 /api 返回的真实数据（D46）。
// 所有判断（推荐、分流、安全边界、问答）都在后端；前端只负责展示和记录本地状态。
(function () {
  var $ = function (s, el) { return (el || document).querySelector(s); };
  var $$ = function (s, el) { return Array.prototype.slice.call((el || document).querySelectorAll(s)); };
  var PENDING = '【待知识库】';
  var DISC = '<div class="sec small">本助手提供的信息仅供参考，不能代替牙医诊断。</div>';
  var LABELS = {};   // mock / 大模型繁忙 / 资料要点 的标注文案，来自 /api/health

  function esc(t) { return String(t == null ? '' : t).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/\n/g, '<br>'); }
  function val(t) { return esc(t).split(PENDING).join('<span class="ph">' + PENDING + '</span>'); }
  function toast(t) { var el = $('#toast'); el.textContent = t; el.style.display = 'block'; clearTimeout(toast.t); toast.t = setTimeout(function () { el.style.display = 'none'; }, 2200); }
  function api(path, body) {
    return fetch('/api' + path, body === undefined ? {} : { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
      .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); });
  }
  var SOURCES = {};  // 来源编号 → 名称、链接（来自 /api/sources 不存在时用出处里带的）
  function srcLinks(ids) {
    ids = (ids || []).filter(function (x, i, a) { return a.indexOf(x) === i; });
    if (!ids.length) return '<span class="ph">' + PENDING + '</span>';
    return ids.map(function (i) { var s = SOURCES[i]; return s && s.url ? '<a href="' + s.url + '" target="_blank">' + esc(i) + '</a>' : esc(i); }).join('、');
  }

  // ---------- 状态 ----------
  var model = null;        // null | 型号名 | 'unsure'
  var routePath = null;    // smart | basic | unsure
  var META = {};

  // ---------- 路由（同原型） ----------
  function show(route) {
    var parts = route.split('/'), name = parts[0] || 'home', arg = parts[1] || '';
    if (!$('#s-' + name)) name = 'home';
    $$('.screen').forEach(function (s) { s.classList.remove('on'); });
    var scr = $('#s-' + name); scr.classList.add('on');
    $('#phone').dataset.screen = name;
    $('#navEyebrow').textContent = scr.dataset.eyebrow || '';
    $('#navTitle').textContent = scr.dataset.title;
    $$('#sideNav a').forEach(function (a) { a.classList.toggle('on', a.getAttribute('href') === '#' + name); });
    $$('.mask').forEach(function (m) { m.classList.remove('on'); });
    if (name === 'quiz') renderQuiz();
    if (name === 'rec') renderRec();
    if (name === 'route') renderRoute();
    if (name === 'bind') renderBind();
    if (name === 'setup') enterSetup();
    if (name === 'sync') renderSync();
    if (name === 'chat') enterChat(arg);
    window.scrollTo(0, 0);
  }
  function go(route) { if (location.hash.slice(1) === route) show(route); else location.hash = route; }
  window.addEventListener('hashchange', function () { show(location.hash.slice(1)); });
  $('#backBtn').onclick = function () { history.length > 1 ? history.back() : go('home'); };
  document.addEventListener('click', function (e) {
    if (e.target.closest('[data-app-set]')) { toast('Demo 不跳转笑容加 App · 跳转方式' + PENDING); return; }
    var a = e.target.closest('[data-ask]');
    if (a) { go('chat'); setTimeout(function () { var c = $('#exampleChips [data-kind=' + a.dataset.ask + ']'); if (c) c.click(); }, 0); return; }
    var t = e.target.closest('[data-go]'); if (!t) return;
    if (t.dataset.quizStep) { qi = +t.dataset.quizStep; }
    else if (t.dataset.go === 'quiz' && t.closest('#s-home,#bMask')) { qi = 0; }
    go(t.dataset.go);
  });

  // ---------- 选购测评：题目来自 /api/quiz；第 1 题不能自己填写，第 2–4 题可以（D46 ①②） ----------
  var Q = [], ASSUME = [], ans = [], customText = [], qi = 0;
  var CUSTOM = '其他，自己填写';
  function optsOf(q) { return q.custom ? q.opts.concat([CUSTOM]) : q.opts; }
  function isCustom(k, i) { return !!Q[k].custom && i === Q[k].opts.length; }
  function answered(k) { return ans[k].some(function (i) { return !isCustom(k, i) || customText[k].trim(); }); }
  function optHtml(o) { return esc(o) + (ASSUME.indexOf(o) >= 0 ? ' <span class="tag assume">业务假设</span>' : ''); }
  function updateNext() { var q = Q[qi]; $('#qNext').disabled = !!(q.req && !answered(qi)); $('#qReq').style.display = (q.req && !answered(qi)) ? 'block' : 'none'; }
  function renderQuiz() {
    if (!Q.length) return;
    var q = Q[qi], opts = optsOf(q);
    $('#qStep').textContent = '0' + (qi + 1) + ' / 05';
    $('#qSegs').innerHTML = [0, 1, 2, 3, 4].map(function (k) { return '<i' + (k <= qi ? ' class="on"' : '') + '></i>'; }).join('');
    $('#qTitle').textContent = q.t; $('#qHint').textContent = q.hint + (q.custom ? ' · 没有合适的可以自己填写' : '');
    $('#qOpts').innerHTML = opts.map(function (o, i) {
      var label = (q.custom && i === q.opts.length) ? esc(o) : optHtml(o);
      return '<button class="opt' + (q.multi ? ' multi' : '') + (ans[qi].indexOf(i) >= 0 ? ' sel' : '') + '" data-i="' + i + '"><span class="badge b' + i + '">' + 'ABCDEF'[i] + '</span><span class="ot">' + label + '</span><span class="box"></span></button>';
    }).join('');
    $('#qCustom').classList.toggle('on', !!q.custom && ans[qi].indexOf(q.opts.length) >= 0);
    $('#qCustomInput').value = customText[qi];
    $('#qPrev').style.visibility = qi === 0 ? 'hidden' : 'visible';
    $('#qNext').textContent = qi === 4 ? '看推荐' : '下一题';
    $('#qReq').textContent = '预算为必答题，请先选择';
    updateNext();
  }
  $('#qOpts').onclick = function (e) {
    var b = e.target.closest('.opt'); if (!b) return;
    var i = +b.dataset.i, q = Q[qi], a = ans[qi];
    if (!q.multi) ans[qi] = [i];
    else {
      var k = a.indexOf(i);
      if (k >= 0) a.splice(k, 1);
      else { if (q.none !== undefined) { if (i === q.none) a.length = 0; else { var n = a.indexOf(q.none); if (n >= 0) a.splice(n, 1); } } a.push(i); }
    }
    renderQuiz();
  };
  $('#qCustomInput').oninput = function () { customText[qi] = this.value; updateNext(); };
  $('#qPrev').onclick = function () { if (qi > 0) { qi--; renderQuiz(); } };
  $('#qNext').onclick = function () { if (qi < 4) { qi++; renderQuiz(); } else { go('rec'); } };
  function picked(k) { return ans[k].filter(function (i) { return !isCustom(k, i); }).map(function (i) { return Q[k].opts[i]; }); }
  function typed(k) { return Q[k] && Q[k].custom && ans[k].indexOf(Q[k].opts.length) >= 0 ? customText[k].trim() : ''; }
  // 交给推荐规则：只用固定选项
  function answersPayload() {
    return { q1: picked(0)[0] || null, q2: picked(1), q3: picked(2)[0] || null, q4: picked(3), q5: picked(4)[0] || null };
  }
  // 交给 AI 助手：第 2–5 题 + 自己填写的内容，不含预算（D46 ⑥）
  function profilePayload() {
    var p = answersPayload(); delete p.q1;
    [1, 2, 3].forEach(function (k) { if (typed(k)) p['q' + (k + 1) + '_自己填写'] = typed(k); });
    return p;
  }

  // ---------- 推荐卡 ----------
  var rec = null, recKey = '';
  function renderRec() {
    var key = JSON.stringify(answersPayload());
    if (!answersPayload().q1) { go('quiz'); return; }
    if (key === recKey && rec) { paintRec(); return; }
    recKey = key; rec = null;
    $('#recLoading').style.display = 'block'; $('#recFull').style.display = 'none'; $('#recEmpty').style.display = 'none';
    $('#recLoading').textContent = '正在按你的回答挑选型号、生成推荐理由…';
    api('/recommend', { answers: answersPayload(), explain: true }).then(function (r) { if (recKey === key) { rec = r; paintRec(); } })
      .catch(function () { $('#recLoading').textContent = '推荐服务暂时不可用，请稍后再试。'; });
  }
  function paintRec() {
    $('#recLoading').style.display = 'none';
    var ok = rec.status === 'ok';
    $('#recFull').style.display = ok ? 'block' : 'none';
    $('#recEmpty').style.display = ok ? 'none' : 'block';
    if (!ok) { $('#recEmpty .card div:nth-child(2)').textContent = rec.message || (rec.errors || []).join('；'); return; }
    var m = rec.main, b = rec.backup;
    $('#mainModel').textContent = m.model;
    $('#mainPrice').innerHTML = '¥' + val(m.price) + '　<span style="color:#8f9bb6">京东官方自营店标价</span>';
    var sens = (answersPayload().q2 || []).indexOf('牙龈敏感或容易出血') >= 0;
    $('#headType').textContent = '';
    $('#mainHead').innerHTML = val(m.brush_head.text);
    $('#mainSrc').innerHTML = srcLinks((m.price_sources || []).concat(m.brush_head.sources || []));
    // 理由格子：对应用户选项；格子下面加理由文字（D46 ③，不显示出处）
    var rs = (m.reasons && m.reasons.reasons) || [];
    var tiles = (m.matched || []).map(function (h) { return h.option; });
    if (!tiles.length) tiles = rs.map(function (r) { return r.option; });
    tiles = tiles.slice(0, 3);
    $('#reasons').innerHTML = tiles.map(function (p) { return '<div class="w"><i>✓</i>' + esc(p) + '</div>'; }).join('');
    $('#reasons').style.gridTemplateColumns = 'repeat(' + Math.max(1, Math.min(tiles.length, 3)) + ',1fr)';
    $('#reasonText').innerHTML = rs.map(function (r) {
      var t = r.reason || '';
      return '<div>· ' + (/^你选了/.test(t) || !r.option ? '' : '<b>' + esc(r.option) + '</b>：') + esc(t) + '</div>';
    }).join('');
    var anyTyped = [1, 2, 3].some(function (k) { return typed(k); });
    $('#basedOn').textContent = '每格对应你在测评里的选项' + (anyTyped ? '；你自己填写的内容不参与规则选型号，会交给 AI 助手参考' : '');
    $('#reasonBy').textContent = m.reasons && m.reasons.by === 'llm'
      ? '理由由大模型（' + (m.reasons.llm_model || '') + '）根据官方参数生成，程序校验数字和型号'
      : '理由为规则模板文案（大模型未生成或未通过校验）';
    // 使用注意：后端规则（官方起始模式，D39 / D46 ④）
    var notes = rec.notes || [], c = '<b>使用注意</b><br>', bleed = false;
    notes.forEach(function (n) { if (/持续出血/.test(n.text)) bleed = true; else c += '· ' + esc(n.text) + '<br>'; });
    if (!notes.length || (notes.length === 1 && bleed)) c += '· 按官方说明使用；有问题可以问 AI 助手<br>';
    if (bleed || sens) c += '<div class="bleed">持续出血请先看牙医</div>';
    $('#caution').innerHTML = c;
    $('#backupCard').style.display = b ? 'block' : 'none';
    if (b) {
      $('#bkModel').textContent = b.model;
      $('#bkPrice').innerHTML = '¥' + val(b.price) + '　<span class="small">京东官方自营店标价</span>';
      $('#bkSrc').innerHTML = srcLinks((b.price_sources || []).concat(b.brush_head.sources || []));
    }
    $('#buyNote').innerHTML = m.buy && m.buy.url ? '购买链接：<a href="' + m.buy.url + '" target="_blank">' + esc(m.buy.name) + '</a>' : '';
    $('#fitBtn').textContent = '符合我的情况';
  }
  $('#buyBtn').onclick = function () { if (rec && rec.main && rec.main.buy && rec.main.buy.url) window.open(rec.main.buy.url, '_blank'); else toast('购买链接' + PENDING); };
  $('#fitBtn').onclick = function () { this.textContent = '已反馈，谢谢'; };
  $('#askAiBtn').onclick = function () { go('chat/rec'); };

  // ---------- 我的牙刷：型号列表来自 /api/models，界面不标款式（D46 ⑧） ----------
  var MODELS = null;
  function renderRoute() {
    var draw = function () {
      var list = MODELS.smart.concat(MODELS.basic).sort(function (a, b) { return a.localeCompare(b, 'zh'); });
      $('#modelList').innerHTML = list.length ? list.map(function (n, i) {
        return '<button class="entry' + (i % 2 ? ' g' : '') + '" data-model-pick="' + esc(n) + '"><span class="ic">' + esc(n.charAt(0)) + '</span>'
          + '<span><span class="t">' + esc(n) + '</span><br><span class="small">选择这款，查看能用的功能</span></span><span class="arr">›</span></button>';
      }).join('') : '<div class="card small">型号列表<span class="ph">' + PENDING + '</span></div>';
    };
    if (MODELS) draw(); else api('/models').then(function (r) { MODELS = r; draw(); });
  }
  $('#s-route').addEventListener('click', function (e) {
    var b = e.target.closest('[data-model-pick]'); if (!b) return;
    var pick = b.dataset.modelPick;
    model = pick === 'unsure' ? 'unsure' : pick; st = {}; setupRes = null;
    $('#setupResult').style.display = 'none';
    api('/route', { model: model === 'unsure' ? null : model }).then(function (r) { routePath = r.path; go(r.path === 'smart' ? 'bind' : 'setup'); });
  });

  // ---------- 引导绑定笑容加 App ----------
  var DL_URL = '';
  function renderBind() {
    if (routePath !== 'smart') { go('route'); return; }
    $('#bindModel').textContent = model;
    if (!DL_URL) api('/kb/KB-APP-01').then(function (r) {
      var s = r.citations[0] && r.citations[0].sources[0];
      DL_URL = (s && s.url) || '';
      $('#dlText').innerHTML = '入口：usmile 官网下载中心（' + srcLinks(['S10']) + '）';
    });
  }
  $('#dlBtn').onclick = function () { if (DL_URL) window.open(DL_URL, '_blank'); else toast('下载入口' + PENDING); };

  // ---------- 画像同步：只同步第 2–5 题，不同步预算 ----------
  function renderSync() {
    var has = [1, 2, 3, 4].some(function (k) { return ans[k] && ans[k].length; });
    $('#syncList').innerHTML = has ? [1, 2, 3, 4].map(function (k) {
      var t = picked(k).concat(typed(k) ? ['自己填写：' + typed(k)] : []);
      return '<li><span class="k">' + esc(Q[k].t) + '</span>' + (esc(t.join('、')) || '（未作答）') + '</li>';
    }).join('') : '<li>你还没做过选购测评，没有可同步的内容，直接去绑定即可。</li>';
    $('#syncBtns').style.display = has ? 'flex' : 'none';
    $('#syncSkip').style.display = has ? 'none' : 'block';
    $('#syncState').textContent = '';
  }
  var synced = false;
  function doSync(consent) {
    api('/profile-sync', { answers: answersPayload(), consent: consent, already_synced: synced }).then(function (r) {
      if (r.status === 'synced') synced = true;
      $('#syncState').textContent = r.message; $('#syncBtns').style.display = 'none';
      toast('Demo 不连接真实 App · 绑定步骤以 App 内指引为准');
    });
  }
  $('#syncYes').onclick = function () { doSync(true); };
  $('#syncNo').onclick = function () { doSync(false); };
  $('#syncSkip').onclick = function () { toast('Demo 不连接真实 App · 绑定步骤以 App 内指引为准'); };

  // ---------- 首次设置 + 刷头提醒（后端 4 项，D46 ⑨） ----------
  var st = {}, setupRes = null, subscribed = false;
  function enterSetup() {
    if (routePath === 'smart') { go('bind'); return; }
    $('#setupModel').innerHTML = model ? '<span>' + (model === 'unsure' ? '型号未确认 · 先给通用建议' : '你的型号：' + esc(model)) + '</span><a href="#route">更换</a>'
      : '<span>还没选择型号</span><a href="#route">去选择</a>';
    syncSeg();
  }
  function syncSeg() {
    $$('#s-setup .seg').forEach(function (seg) { $$('button', seg).forEach(function (b) { b.classList.toggle('sel', st[seg.dataset.key] === b.dataset.v); }); });
    $('#genBtn').disabled = !(model && st.first && st.sens && st.goal);
  }
  $$('#s-setup .seg').forEach(function (seg) { seg.onclick = function (e) { var b = e.target.closest('button'); if (!b) return; st[seg.dataset.key] = b.dataset.v; syncSeg(); }; });
  var GOAL = { clean: '刷不干净', habit: '刷牙习惯不好', gum: '护理牙龈' };
  function genSetup() {
    $('#genBtn').disabled = true; $('#genBtn').textContent = '正在生成…';
    api('/setup', { model: model === 'unsure' ? null : model, first_time: st.first === 'yes', sensitive: st.sens === 'yes', goal: GOAL[st.goal] }).then(function (r) {
      setupRes = r; $('#genBtn').textContent = '生成我的设置'; syncSeg();
      if (r.status === 'not_applicable') { toast(r.message); go('bind'); return; }
      var unsure = r.status === 'general';
      $('#setupResult').style.display = 'block';
      $('#generalTag').innerHTML = unsure ? '<span class="general">通用建议 · 确认型号后给出针对性设置</span>' : '<span class="tag hl">按你的型号和回答生成</span>';
      $('#unsureHelp').style.display = unsure ? 'block' : 'none';
      var html = (r.items || []).map(function (it) {
        var ids = (it.sources || []).concat((it.citations || []).map(function (c) { return c.chunk_id; }));
        return '<div class="item"><div class="k">' + esc(it.name) + '</div><div>' + val(it.text) + '</div>'
          + (ids.length ? '<div class="small">出处：' + srcLinks(it.sources).replace('<span class="ph">' + PENDING + '</span>', '') + ((it.citations || []).length ? ' ' + (it.citations || []).map(function (c) { return esc(c.chunk_id); }).join('、') : '') + '</div>' : '') + '</div>';
      }).join('');
      if ((r.notes || []).length) html += '<div class="item"><div class="k">第一周注意事项</div><div>' + r.notes.map(esc).join('<br>') + '</div></div>';
      $('#setupItems').innerHTML = html;
      if (!$('#startDate').value) { var d = new Date(); d.setMinutes(d.getMinutes() - d.getTimezoneOffset()); $('#startDate').value = d.toISOString().slice(0, 10); }
      refreshReminder();
      setTimeout(function () { $('#setupResult').scrollIntoView({ behavior: 'smooth' }); }, 50);
    }).catch(function () { $('#genBtn').textContent = '生成我的设置'; syncSeg(); toast('服务暂时不可用，请稍后再试'); });
  }
  function refreshReminder() {
    var d = $('#startDate').value; if (!d) return;
    api('/reminder', { model: model === 'unsure' ? null : model, start_date: d, subscribe: subscribed }).then(function (r) {
      $('#nextDate').innerHTML = r.status === 'ok' ? '<b>' + esc(r.next_date) + '</b>（开始日期 + 官方周期 ' + esc(r.cycle) + '；出处 ' + srcLinks(r.cycle_sources) + '）'
        : val(r.next_date || PENDING);
    });
  }
  $('#startDate').onchange = refreshReminder;
  $('#genBtn').onclick = genSetup;
  $('#remindBtn').onclick = function () {
    if (subscribed) { subscribed = false; this.textContent = '提醒我'; $('#remindState').textContent = '已取消；仍可在这里看到更换日期'; refreshReminder(); return; }
    $('#subMask').classList.add('on');
  };
  $('#subNo').onclick = function () { $('#subMask').classList.remove('on'); $('#remindState').textContent = '未授权，仍可在这里看到更换日期'; };
  $('#subYes').onclick = function () { $('#subMask').classList.remove('on'); subscribed = true; $('#remindState').textContent = '已订阅（Demo 模拟），到期提醒一次，可随时取消'; $('#remindBtn').textContent = '取消提醒'; refreshReminder(); };

  // ---------- AI 问答 ----------
  var chatInited = false, chatProfile = null, lastQ = null, lastFromExample = false;
  function addMsg(cls, html) { var m = document.createElement('div'); m.className = 'msg ' + cls; m.innerHTML = html; $('#chatBox').appendChild(m); m.scrollIntoView({ block: 'end' }); return m; }
  function renderCtx() {
    $('#chatCtx').innerHTML = model ? '<span>当前型号：' + (model === 'unsure' ? '未确认' : esc(model)) + '</span><a href="#route">更换</a>'
      : '<span>还没选择型号，问到型号相关问题时会先问你</span><a href="#route">选择</a>';
  }
  function enterChat(arg) {
    renderCtx();
    if (!chatInited) { chatInited = true; addMsg('bot', '你好，我是 AI 护齿助手，可以回答使用方法、刷头、适用人群等问题，回答会标注出处。<br><span class="small">问题不清楚时我会先问你一句。</span>'); }
    if (arg === 'rec' && rec && rec.main) {
      // 从推荐卡进入：带上推荐型号和测评情况（不含预算）
      chatProfile = profilePayload(); model = rec.main.model; routePath = null; renderCtx();
      api('/route', { model: model }).then(function (r) { routePath = r.path; });
      addMsg('user', '我想了解推荐给我的型号：' + esc(rec.main.model) + '<span class="src">从推荐卡自动发送</span>');
      addMsg('bot', '好的，关于这款型号，你想了解什么？<div class="chips"><button class="chip hl" data-recq>适合我的情况吗</button><button class="chip hl" data-recq>该配什么刷头</button><button class="chip hl" data-recq>第一次用要注意什么</button></div><div class="small" style="margin-top:6px">也可以直接在下面输入</div>');
    }
  }
  function stripLabel(text, mode) {
    var label = { mock: LABELS.mock, fallback: LABELS.fallback, kb_summary: LABELS.kb_summary }[mode];
    return label ? text.split(label).join('').trim() : text;
  }
  function citeHtml(cits) {
    if (!cits || !cits.length) return '';
    return '<div class="sec"><span class="k">出处</span><br>' + cits.map(function (c, i) {
      var links = (c.sources || []).map(function (s) { return s.url ? '<a href="' + s.url + '" target="_blank">' + esc(s.name) + '</a>' : esc(s.name); }).join('、');
      return '<div class="small">[' + (i + 1) + '] ' + esc(c.title) + '｜' + links + '（' + esc(c.fetched) + '）</div>';
    }).join('') + '</div>';
  }
  function genNote(r) {
    var t = r.llm_model ? '由 ' + esc(r.llm_model) + ' 生成' + (META.llm_primary && r.llm_model !== META.llm_primary ? '（主模型限流，已换用备用模型）' : '') : '';
    if (r.mode === 'mock') t = 'mock 模式（未配置大模型 Key）';
    return t ? '<div class="gen">' + t + '</div>' : '';
  }
  function answerCard(r) {
    var html = '';
    var notices = (r.notices || []).slice();
    if (r.simulated) {
      var simNote = notices.length && /模拟设备数据/.test(notices[0]) ? notices.shift() : '';
      html += '<div class="simdata"><b>⚠ 模拟设备数据，仅作演示，非真实用户</b><span class="tag v2s">V2</span><br>' + esc(simNote.replace('（模拟设备数据，仅作演示，非真实用户）', '')) + '</div>';
    }
    var pill = { mock: '未配置大模型 Key，以下为检索到的官方资料要点', fallback: '大模型暂时繁忙，以下为官方资料要点，未经大模型整理', kb_summary: '大模型没有整理出可靠回答，以下为相关官方资料要点' }[r.mode];
    html += '<div class="sec">' + (pill ? '<span class="modepill">' + pill + '</span><br>' : '') + '<span class="k">结论</span><br>' + val(stripLabel(r.answer, r.mode)) + '</div>';
    if (notices.length) html += '<div class="sec"><span class="k">补充说明</span><br>' + notices.map(function (n) { return '· ' + esc(n); }).join('<br>')
      + ((r.actions || []).indexOf('go_app') >= 0 ? '<br><button class="appbtn" data-app>去笑容加 App 设置 ›</button>' : '') + '</div>';
    else if ((r.actions || []).indexOf('go_app') >= 0) html += '<div class="sec"><button class="appbtn" data-app>去笑容加 App 设置 ›</button></div>';
    html += citeHtml(r.citations) + genNote(r) + DISC + '<div class="feedback"><button>已解决</button><button>没解决</button></div>';
    return html;
  }
  function ask(question, opts) {
    opts = opts || {};
    lastQ = question; lastFromExample = !!opts.example;
    if (!opts.silent) addMsg('user', esc(question) + (opts.srcLabel ? '<span class="src">' + opts.srcLabel + '</span>' : ''));
    var wait = addMsg('bot', '<span class="small">正在查找官方资料…</span>');
    var m = model && model !== 'unsure' ? model : null;
    api('/ask', { question: question, model: m, followup_done: !!opts.followupDone, use_device_data: routePath === 'smart', profile: chatProfile })
      .then(function (r) { wait.remove(); renderAnswer(r, question, opts); })
      .catch(function () { wait.innerHTML = '服务暂时不可用，请稍后再试。'; });
  }
  function renderAnswer(r, question, opts) {
    if (r.type === 'followup') {
      addMsg('bot', esc(r.answer) + ' 答案因型号不同而不同。<div class="chips">' + r.followup_options.map(function (o) {
        return '<button class="chip" data-model="' + esc(o) + '">' + esc(o) + '</button>';
      }).join('') + '</div>');
    } else if (r.type === 'subjective') {
      addMsg('bot', '体验因人而异，我不下“好用 / 不好用”的结论。<div class="sec">可以告诉我你最在意什么（如续航、噪音、牙龈护理），或者<a href="#quiz">做 1 分钟选购测评 ›</a></div>' + DISC);
    } else if (r.type === 'boundary') {
      var cat = r.category;
      addMsg('bot', (cat === 'medical' || cat === 'urgent') ? '这个情况需要医生判断，我给你弹出了就医提示。' : cat === 'competitor' ? '我不评价其他品牌，详见弹出的提示。' : '这个问题我不能直接处理，详见弹出的提示。');
      openBoundary(r, question, opts.example);
    } else {
      addMsg('bot', answerCard(r));
    }
  }
  $('#chatBox').addEventListener('click', function (e) {
    if (e.target.closest('[data-app]')) { toast('Demo 不跳转笑容加 App · 跳转方式' + PENDING); return; }
    var fb = e.target.closest('.feedback button'); if (fb) { $$('button', fb.parentNode).forEach(function (b) { b.classList.remove('sel'); }); fb.classList.add('sel'); return; }
    var rq = e.target.closest('[data-recq]');
    if (rq && !rq.disabled) { $$('[data-recq]', rq.parentNode).forEach(function (b) { b.disabled = true; }); ask(rq.textContent); return; }
    var mb = e.target.closest('[data-model]'); if (mb && !mb.disabled) {
      $$('[data-model]', mb.parentNode).forEach(function (b) { b.disabled = true; }); mb.classList.add('hl');
      var pick = mb.dataset.model;
      model = pick === '我不确定' ? 'unsure' : pick; renderCtx();
      addMsg('user', esc(pick));
      api('/route', { model: model === 'unsure' ? null : model }).then(function (r) { routePath = r.path; ask(lastQ, { silent: true, followupDone: true, example: lastFromExample }); });
    }
  });
  $('#exampleChips').onclick = function (e) {
    var c = e.target.closest('.chip'); if (!c) return;
    var text = c.textContent.trim().replace(/^「|」$/g, '');
    ask(text, { example: true, srcLabel: /R\d{3}/.test(c.innerHTML) ? '京东评论原文' : '京东买家提问原文' });
  };
  $('#sendBtn').onclick = function () { var v = $('#chatInput').value.trim(); if (!v) return; $('#chatInput').value = ''; ask(v); };
  $('#chatInput').addEventListener('keydown', function (e) { if (e.key === 'Enter') $('#sendBtn').click(); });

  // ---------- 安全边界弹窗：类别由后端规则判断 ----------
  var svcUrl = '';
  function openBoundary(r, question, example) {
    var cat = r.category;
    $('#bQuote').innerHTML = '「' + esc(question) + '」<span class="small">' + (example ? '京东买家提问 / 评论原文（示例输入）' : '你的提问') + '</span>';
    $('#bKind').textContent = { medical: '安全边界 · 就医提示', urgent: '安全边界 · 急症', service: '安全边界 · 转官方客服', authenticity: '安全边界 · 转官方渠道', competitor: '安全边界 · 不评价竞品' }[cat] || '安全边界';
    var med = cat === 'medical' || cat === 'urgent', svc = cat === 'service' || cat === 'authenticity';
    $('#bMedical').style.display = med ? 'block' : 'none';
    $('#bService').style.display = svc ? 'block' : 'none';
    $('#bCompetitor').style.display = cat === 'competitor' ? 'block' : 'none';
    $('#bMedNormal').style.display = cat === 'urgent' ? 'none' : 'block';
    $('#bMedUrgent').style.display = cat === 'urgent' ? 'block' : 'none';
    if (svc) {
      var fake = cat === 'authenticity';
      $('#svcTitle').textContent = fake ? '助手不判断真伪' : '这个问题请联系官方客服';
      $('#svcText').textContent = fake ? '请通过官方渠道查询，助手不对真伪下结论。' : '售后、退换、价保、物流问题助手不处理，也不承诺任何保修或退换结果。';
      $('#svcBtn').textContent = fake ? '去官方渠道查询' : '联系官方客服';
      var body = (r.answer || '').split('\n').slice(1).join('\n');   // 第 1 行是边界说明，后面是知识库里的官方入口
      var c = (r.citations || [])[0], s = c && c.sources && c.sources[0];
      svcUrl = (s && s.url) || '';
      $('#svcPh').innerHTML = val(body || PENDING) + (s ? '<br>出处：' + (s.url ? '<a href="' + s.url + '" target="_blank">' + esc(s.name) + '</a>' : esc(s.name)) + '（' + esc(c.fetched) + '）' : '');
    }
    $('#bMask').classList.add('on');
  }
  $('#svcBtn').onclick = function () { if (svcUrl) window.open(svcUrl, '_blank'); else toast('官方入口' + PENDING); };
  $('#bClose').onclick = function () { $('#bMask').classList.remove('on'); };
  $('#bMask').onclick = function (e) { if (e.target === this) this.classList.remove('on'); };

  // ---------- 启动：读取页脚、标注文案和测评题 ----------
  Promise.all([api('/health'), api('/quiz'), api('/kb/KB-APP-01')]).then(function (res) {
    META = res[0]; LABELS = { mock: META.mock_label, fallback: META.fallback_label, kb_summary: META.kb_summary_label };
    var qz = res[1]; ASSUME = qz.business_assumption || [];
    Q = qz.questions.map(function (q, k) {
      return {
        t: q.text.replace(/（可多选）$/, ''), multi: q.type === 'multi', req: !!q.required, opts: q.options,
        none: q.exclusive ? q.options.indexOf(q.exclusive) : undefined,
        custom: k >= 1 && k <= 3,   // 第 1 题不能自己填写（D46 ①），第 5 题是是 / 否
        hint: (q.type === 'multi' ? '多选' : '单选') + (q.required ? ' · 必答' : '') + (q.note ? ' · ' + q.note : '') + (k === 4 ? ' · 影响起始模式建议' : '')
      };
    });
    ans = Q.map(function () { return []; }); customText = Q.map(function () { return ''; });
    (res[2].citations || []).forEach(function (c) { (c.sources || []).forEach(function (s) { SOURCES[s.id] = s; }); });
    return api('/sources').then(function (all) { Object.keys(all).forEach(function (k) { SOURCES[k] = all[k]; }); }).catch(function () {});
  }).finally(function () { show(location.hash.slice(1) || 'home'); });
})();
