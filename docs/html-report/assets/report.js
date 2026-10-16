// html-report 런타임 하나: 테마 전환, 도표 높이·테마 메시지, 비교 보고서 판정·필터·저장·결과 복사.
// 판정은 브라우저 저장소에만 두며 외부로 보내지 않는다.
(() => {
  const THEME_KEY = 'html-report-theme';
  const THEMES = [['system', '시스템'], ['light', '라이트'], ['dark', '다크']];
  const FILTERS = [['all', '전체'], ['chosen', '선택'], ['open', '미선택'], ['rework', '재작업'], ['hold', '보류']];
  const LETTERS = ['A', 'B', 'C', 'D', 'E', 'F'];

  // cost: time O(1), heap O(1), stack O(1)
  // vars: 없음
  // basis: estimate
  /** 판정 저장 키. 대상·버전이 바뀌면 다른 키라 이전 판정을 이어받지 않는다 */
  const storageKey = (report) => `html-report:${report.target}:${report.version}`;

  // cost: time O(q), heap O(q), stack O(1)
  // vars: q = 판정 절 수
  // basis: estimate
  /** 결과 복사 형식. 미판정은 choice null, 미판정·보류를 승인으로 바꾸지 않는다 */
  function result(report, state) {
    return {
      target: report.target,
      version: report.version,
      questions: report.questions.map((question) => ({
        title: question.title,
        choice: state[question.id]?.choice ?? null,
        note: state[question.id]?.note ?? '',
      })),
    };
  }

  // cost: time O(1), heap O(1), stack O(1)
  // vars: 없음
  // basis: estimate
  /** 필터 분류: 선택(후보·승인), 미선택, 재작업, 보류 */
  function category(choice) {
    if (!choice) return 'open';
    if (choice === '재작업') return 'rework';
    if (choice === '보류') return 'hold';
    return 'chosen';
  }

  // cost: time O(1), heap O(1), stack O(1)
  // vars: 없음
  // basis: estimate
  /** 판정 버튼. 선택 비교는 그림 수만큼 A·B·C…, 전후 확인은 승인 */
  function choices(kind, figures) {
    const picks = kind === 'decision' ? LETTERS.slice(0, Math.max(1, figures)) : ['승인'];
    return [...picks, '재작업', '보류'];
  }

  // cost: time O(q), heap O(q), stack O(1)
  // vars: q = 저장된 절 수
  // basis: estimate
  /** 저장 값 복원. 옛 형식·깨진 값은 버리고 빈 값으로 시작(choice 문자열, note 문자열만) */
  function restore(raw) {
    let parsed;
    try {
      parsed = JSON.parse(raw ?? '{}');
    } catch {
      return {};
    }
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) return {};
    const state = {};
    for (const [id, entry] of Object.entries(parsed)) {
      if (!entry || typeof entry !== 'object') continue;
      const choice = typeof entry.choice === 'string' ? entry.choice : null;
      const note = typeof entry.note === 'string' ? entry.note : '';
      if (choice || note) state[id] = { choice, note };
    }
    return state;
  }

  globalThis.ReportCore = Object.freeze({ storageKey, result, category, choices, restore });
  if (typeof document === 'undefined') return;

  const root = document.documentElement;
  const report = JSON.parse(document.getElementById('report-data').textContent);

  // cost: time O(1), heap O(1), stack O(1), io 1
  // vars: 없음
  // basis: estimate
  function read(key) {
    try {
      return localStorage.getItem(key);
    } catch {
      return null;
    }
  }

  // cost: time O(1), heap O(1), stack O(1), io 1
  // vars: 없음
  // basis: estimate
  function write(key, value) {
    try {
      localStorage.setItem(key, value);
    } catch {
      // 저장소를 쓸 수 없는 환경은 이번 화면에서만 유지
    }
  }

  // cost: time O(n), heap O(1), stack O(1)
  // vars: n = 문서 안 요소 수
  // basis: estimate
  function button(label, attributes = {}) {
    const element = document.createElement('button');
    element.type = 'button';
    element.textContent = label;
    for (const [name, value] of Object.entries(attributes)) element.setAttribute(name, value);
    return element;
  }

  // cost: time O(1), heap O(1), stack O(1)
  // vars: 없음
  // basis: estimate
  /** 정본 분할 버튼 묶음(app-tablist is-segmented). 선택 모양은 디자인 저장소 CSS가 aria-pressed로 그림 */
  function segmented(label) {
    const group = document.createElement('div');
    group.className = 'app-tablist is-segmented';
    group.setAttribute('role', 'group');
    group.setAttribute('aria-label', label);
    return group;
  }

  // ---- 테마 ----
  const frames = () => [...document.querySelectorAll('iframe[data-diagram]')];
  const theme = () => root.dataset.theme ?? 'system';
  // cost: time O(f), heap O(1), stack O(1)
  // vars: f = 도표 수
  // basis: estimate
  const sendTheme = (frame) => frame.contentWindow?.postMessage({ theme: theme() }, '*');
  // cost: time O(f), heap O(1), stack O(1), io 1
  // vars: f = 도표 수
  // basis: estimate
  function applyTheme(mode, save) {
    if (mode === 'light' || mode === 'dark') root.dataset.theme = mode;
    else delete root.dataset.theme;
    if (save) write(THEME_KEY, mode);
    for (const item of document.querySelectorAll('[data-theme-choice]')) item.setAttribute('aria-pressed', String(item.dataset.themeChoice === mode));
    frames().forEach(sendTheme);
    fit();
  }

  // ---- 도표 높이: 도표가 보내는 높이 메시지, 같은 출처면 문서 전체 높이(여백 포함) 직접 읽기 ----
  // cost: time O(f), heap O(1), stack O(1)
  // vars: f = 도표 수
  // basis: estimate
  function fit() {
    for (const frame of frames()) {
      try {
        const height = frame.contentDocument?.documentElement?.scrollHeight;
        if (Number.isFinite(height) && height > 0) frame.height = String(Math.ceil(height));
      } catch {
        // 다른 출처(file:// 포함)는 높이 메시지로만 맞춤
      }
    }
  }
  addEventListener('message', (event) => {
    const frame = frames().find((item) => item.contentWindow === event.source);
    if (!frame || !event.data || typeof event.data !== 'object') return;
    if (event.data.themeRequest === true) sendTheme(frame);
    const height = event.data.figureHeight;
    if (Number.isFinite(height) && height > 0) frame.height = String(Math.ceil(height));
  });
  for (const frame of frames()) {
    frame.addEventListener('load', () => {
      sendTheme(frame);
      fit();
      setTimeout(() => fit(), 500);
    });
  }
  addEventListener('resize', fit);

  // ---- 상단 막대 ----
  const bar = document.querySelector('[data-report-bar]');
  const themeCell = bar.querySelector('[data-bar-theme]');
  const themeGroup = segmented('테마');
  for (const [mode, label] of THEMES) {
    const item = button(label, { 'data-theme-choice': mode, 'aria-pressed': 'false' });
    item.addEventListener('click', () => applyTheme(mode, true));
    themeGroup.append(item);
  }
  themeCell.append(themeGroup);
  applyTheme(read(THEME_KEY) ?? 'system', false);

  if (report.kind === 'explain') return;

  // ---- 판정 ----
  const key = storageKey(report);
  const state = restore(read(key));
  const save = () => write(key, JSON.stringify(state));
  const sections = new Map();
  let filter = 'all';

  const control = bar.querySelector('[data-bar-judge]');
  const progress = document.createElement('span');
  progress.className = 'report-progress';
  progress.setAttribute('role', 'status');
  const filters = segmented('판정 필터');
  for (const [value, label] of FILTERS) {
    const item = button(label, { 'data-filter': value, 'aria-pressed': String(value === filter) });
    item.addEventListener('click', () => {
      filter = value;
      refresh();
    });
    filters.append(item);
  }
  const copy = button('결과 복사');
  copy.addEventListener('click', copyResult);
  const actions = segmented('결과');
  actions.append(copy);
  const scroller = document.createElement('div');
  scroller.className = 'report-bar-scroll';
  scroller.append(filters);
  control.append(progress, scroller, actions);

  const marks = report.kind === 'decision' ? LETTERS : ['전', '후'];
  for (const question of report.questions) {
    const section = document.querySelector(`[data-report-section="${CSS.escape(question.id)}"]`);
    if (!section) continue;
    section.querySelectorAll('.app-figure-grid-item').forEach((item, at) => {
      if (marks[at]) item.dataset.mark = marks[at];
    });
    const judge = document.createElement('div');
    judge.className = 'report-judge';
    const row = segmented(`${question.title} 판정`);
    for (const choice of choices(report.kind, question.figures)) {
      const item = button(choice, { 'data-choice': choice, 'aria-pressed': 'false' });
      item.addEventListener('click', () => {
        const entry = state[question.id] ?? { choice: null, note: '' };
        entry.choice = entry.choice === choice ? null : choice;
        state[question.id] = entry;
        save();
        refresh();
      });
      row.append(item);
    }
    const note = document.createElement('input');
    note.type = 'text';
    note.className = 'app-input report-judge-note';
    note.placeholder = '의견을 작성해 주세요';
    note.setAttribute('aria-label', `${question.title} 의견`);
    note.value = state[question.id]?.note ?? '';
    note.addEventListener('input', () => {
      state[question.id] = { choice: state[question.id]?.choice ?? null, note: note.value };
      save();
    });
    judge.append(row, note);
    section.append(judge);
    sections.set(question.id, section);
  }

  // cost: time O(q * c), heap O(1), stack O(1)
  // vars: q = 판정 절 수, c = 절마다 버튼 수
  // basis: estimate
  function refresh() {
    let done = 0;
    for (const question of report.questions) {
      const section = sections.get(question.id);
      if (!section) continue;
      const choice = state[question.id]?.choice ?? null;
      if (choice) done += 1;
      section.dataset.choice = category(choice);
      section.hidden = filter !== 'all' && category(choice) !== filter;
      for (const item of section.querySelectorAll('[data-choice]')) item.setAttribute('aria-pressed', String(item.dataset.choice === choice));
      for (const item of section.querySelectorAll('.app-figure-grid-item[data-mark]')) item.classList.toggle('is-chosen', item.dataset.mark === choice);
    }
    progress.textContent = `${done}/${report.questions.length} 판정`;
    for (const item of filters.querySelectorAll('[data-filter]')) item.setAttribute('aria-pressed', String(item.dataset.filter === filter));
  }

  // cost: time O(q), heap O(q), stack O(1), io 1
  // vars: q = 판정 절 수
  // basis: estimate
  async function copyResult() {
    const text = JSON.stringify(result(report, state), null, 2);
    try {
      await navigator.clipboard.writeText(text);
      copy.textContent = '복사됨';
      setTimeout(() => { copy.textContent = '결과 복사'; }, 1500);
    } catch {
      let box = document.querySelector('.report-result');
      if (!box) {
        box = document.createElement('textarea');
        box.className = 'report-result';
        box.readOnly = true;
        box.setAttribute('aria-label', '판정 결과');
        document.querySelector('.app-document-body')?.append(box);
      }
      box.value = text;
      box.focus();
      box.select();
    }
  }

  refresh();
})();
