const TABS = [
  ["runs", "tab.runs", "mdi:play-circle-outline"],
  ["policies", "tab.policies", "mdi:shield-check-outline"],
  ["scenarios", "tab.scenarios", "mdi:clipboard-text-search-outline"],
  ["search", "tab.search", "mdi:web"],
  ["memory", "tab.memory", "mdi:database-eye-outline"],
  ["earcons", "tab.earcons", "mdi:music-note-outline"],
  ["regression", "tab.regression", "mdi:chart-timeline-variant"],
];

const DEFAULT_EXPECTED = {
  must_search: false,
  spoken_response: {
    max_sentences: 2,
    must_not_mention: ["entity_id"],
  },
};

const I18N = {
  en: {
    "app.title": "Voice Harness",
    "aria.views": "Voice Harness views",
    "common.refresh": "Refresh",
    "tab.runs": "Runs",
    "tab.policies": "Prompt Policies",
    "tab.scenarios": "Scenarios",
    "tab.search": "Search Lab",
    "tab.memory": "Memory Lab",
    "tab.earcons": "Earcons",
    "tab.regression": "Regression",
    "status.loading": "Reading integration status",
    "status.waiting": "Waiting for Home Assistant",
    "status.no_entries": "No LLM Gateway config entries loaded yet",
    "status.entries": "{count} config entries loaded",
    "runs.empty": "No configured LLM Gateway entries.",
    "entry.base_url_missing": "Base URL not configured",
    "policies.empty": "No prompt policies.",
    "scenario.user": "User input",
    "scenario.response": "Assistant response",
    "scenario.expected": "Expected JSON",
    "scenario.run": "Run scenario",
    "search.gating": "Search gating",
    "search.no_providers": "No search provider key exposed",
    "search.evaluate": "Evaluate gating",
    "memory.turns": "{count} turns",
    "memory.user": "User",
    "memory.assistant": "Assistant",
    "memory.empty": "No active memory sessions.",
    "earcon.no_pack": "No earcon pack",
    "earcon.meta": "{sampleRate} Hz · target {targetLufs} LUFS · peak limit {peakDbfs} dBFS",
    "earcon.play": "Play {name}",
    "earcon.peak": "{peak} dBFS peak",
    "earcon.empty": "No rendered earcons.",
    "regression.run": "Run",
    "route.timeout": "{seconds}s timeout",
    "result.empty": "No run result yet.",
    "result.passed": "Passed",
    "result.failed": "Failed",
    "result.meta": "Route: {route} · Search: {search}",
    "search.allowed": "allowed",
    "search.blocked": "blocked",
    "error.invalid_expected_json": "Expected JSON is not valid.",
    "policy.low_risk_success.title": "Low-risk success",
    "policy.low_risk_success.spoken": "Done.",
    "policy.state_query.title": "State query",
    "policy.state_query.spoken": "Answer the conclusion first without long explanation.",
    "policy.clarification.title": "Minimal clarification",
    "policy.clarification.spoken": "Ask only one minimal clarification question.",
    "policy.high_risk_confirmation.title": "High-risk confirmation",
    "policy.high_risk_confirmation.spoken": "Do you want to operate {target}? Please confirm.",
    "policy.search_summary.title": "Search summary",
    "policy.search_summary.spoken": "Say the conclusion first; put sources and long lists on screen.",
    "policy.error_repair.title": "Error repair",
    "policy.error_repair.spoken": "Give the next step instead of only saying you did not understand.",
    "policy.deep_task.title": "Deep task",
    "policy.deep_task.spoken": "I will keep analyzing and send the result to Home Assistant notifications.",
    "sample.fast-light.name": "Basic light control",
    "sample.mid-search.name": "Fresh information query",
    "sample.risk-confirmation.name": "High-risk action confirmation",
    "earcon.clarification.purpose": "The assistant needs one missing detail before acting.",
    "earcon.confirmation.purpose": "High-risk action needs explicit user confirmation.",
    "earcon.deep_task.purpose": "Long reasoning has been handed off to a background task.",
    "earcon.failure.purpose": "Request failed or the assistant cannot continue safely.",
    "earcon.listening_end.purpose": "Speech capture ended and the assistant is processing.",
    "earcon.listening_start.purpose": "Microphone is open and the user can speak.",
    "earcon.search.purpose": "Web search is being used for current external information.",
    "earcon.success.purpose": "Low-risk command completed.",
    "earcon.wake.purpose": "Wake word accepted; assistant is entering the voice path.",
  },
  "zh-Hans": {
    "app.title": "语音测试台",
    "aria.views": "语音测试台视图",
    "common.refresh": "刷新",
    "tab.runs": "运行记录",
    "tab.policies": "提示策略",
    "tab.scenarios": "场景测试",
    "tab.search": "搜索实验室",
    "tab.memory": "记忆实验室",
    "tab.earcons": "提示音",
    "tab.regression": "回归测试",
    "status.loading": "正在读取集成状态",
    "status.waiting": "等待 Home Assistant",
    "status.no_entries": "尚未加载 LLM Gateway 配置项",
    "status.entries": "已加载 {count} 个配置项",
    "runs.empty": "没有已配置的 LLM Gateway 条目。",
    "entry.base_url_missing": "未配置 Base URL",
    "policies.empty": "没有提示策略。",
    "scenario.user": "用户输入",
    "scenario.response": "助手回复",
    "scenario.expected": "期望 JSON",
    "scenario.run": "运行场景",
    "search.gating": "搜索门控",
    "search.no_providers": "未暴露搜索 provider key",
    "search.evaluate": "评估门控",
    "memory.turns": "{count} 轮",
    "memory.user": "用户",
    "memory.assistant": "助手",
    "memory.empty": "没有活跃记忆会话。",
    "earcon.no_pack": "没有提示音包",
    "earcon.meta": "{sampleRate} Hz · 目标 {targetLufs} LUFS · 峰值上限 {peakDbfs} dBFS",
    "earcon.play": "播放 {name}",
    "earcon.peak": "{peak} dBFS 峰值",
    "earcon.empty": "没有已渲染的提示音。",
    "regression.run": "运行",
    "route.timeout": "{seconds}s 超时",
    "result.empty": "还没有运行结果。",
    "result.passed": "通过",
    "result.failed": "失败",
    "result.meta": "路由：{route} · 搜索：{search}",
    "search.allowed": "允许",
    "search.blocked": "阻止",
    "error.invalid_expected_json": "期望 JSON 格式不正确。",
    "policy.low_risk_success.title": "低风险成功",
    "policy.low_risk_success.spoken": "好了。",
    "policy.state_query.title": "状态查询",
    "policy.state_query.spoken": "先回答结论，不展开长解释。",
    "policy.clarification.title": "最小澄清",
    "policy.clarification.spoken": "一次只问一个最小澄清问题。",
    "policy.high_risk_confirmation.title": "高风险确认",
    "policy.high_risk_confirmation.spoken": "要操作{target}吗？请确认。",
    "policy.search_summary.title": "搜索摘要",
    "policy.search_summary.spoken": "先说结论，来源和长列表放到屏幕。",
    "policy.error_repair.title": "错误修复",
    "policy.error_repair.spoken": "说明下一步，而不是只说没听懂。",
    "policy.deep_task.title": "深度任务",
    "policy.deep_task.spoken": "我会继续分析，完成后发到 Home Assistant 通知里。",
    "sample.fast-light.name": "普通灯光控制",
    "sample.mid-search.name": "最新信息查询",
    "sample.risk-confirmation.name": "高风险动作确认",
    "earcon.clarification.purpose": "执行前需要补一个缺失信息。",
    "earcon.confirmation.purpose": "高风险动作需要用户显式确认。",
    "earcon.deep_task.purpose": "长推理已交给后台任务继续处理。",
    "earcon.failure.purpose": "请求失败，或助手无法安全继续。",
    "earcon.listening_end.purpose": "语音采集结束，助手正在处理。",
    "earcon.listening_start.purpose": "麦克风已打开，用户可以开始说话。",
    "earcon.search.purpose": "正在为当前外部信息使用联网搜索。",
    "earcon.success.purpose": "低风险指令已完成。",
    "earcon.wake.purpose": "唤醒词已确认，助手进入语音流程。",
  },
};

const DEFAULT_DRAFTS = {
  en: {
    user: "Turn on the living room light",
    response: "**Done.** Living room light is on.",
    expected: JSON.stringify(DEFAULT_EXPECTED, null, 2),
  },
  "zh-Hans": {
    user: "打开客厅灯",
    response: "**已打开** 客厅灯。",
    expected: JSON.stringify(DEFAULT_EXPECTED, null, 2),
  },
};

class VoiceHarnessPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._activeTab = "runs";
    this._data = null;
    this._error = "";
    this._busy = false;
    this._result = null;
    this._draftLocale = this._locale();
    this._draftTouched = false;
    this._draft = this._defaultDraft(this._draftLocale);
  }

  set hass(value) {
    this._hass = value;
    const locale = this._locale();
    if (!this._draftTouched && this._draftLocale !== locale) {
      this._draftLocale = locale;
      this._draft = this._defaultDraft(locale);
    }
    if (this.isConnected && !this._data && !this._busy) {
      this._load();
    }
  }

  get hass() {
    return this._hass;
  }

  set panel(value) {
    this._panel = value;
  }

  connectedCallback() {
    this.shadowRoot.addEventListener("click", (event) => this._onClick(event));
    this.shadowRoot.addEventListener("input", (event) => this._onInput(event));
    this.shadowRoot.addEventListener("submit", (event) => this._onSubmit(event));
    this._render();
    this._load();
  }

  async _load() {
    if (!this.hass || this._busy) {
      return;
    }
    this._busy = true;
    this._error = "";
    this._render();
    try {
      this._data = await this._api("GET", "llm_gateway/harness/status");
    } catch (err) {
      this._error = err.message || String(err);
    } finally {
      this._busy = false;
      this._render();
    }
  }

  async _evaluate(payload) {
    this._busy = true;
    this._error = "";
    this._render();
    try {
      this._result = await this._api("POST", "llm_gateway/harness/evaluate", payload);
    } catch (err) {
      this._error = err.message || String(err);
    } finally {
      this._busy = false;
      this._render();
    }
  }

  async _api(method, path, payload) {
    if (this.hass?.callApi) {
      return this.hass.callApi(method, path, payload);
    }
    const response = await fetch(`/api/${path}`, {
      method,
      credentials: "same-origin",
      headers: payload ? { "Content-Type": "application/json" } : undefined,
      body: payload ? JSON.stringify(payload) : undefined,
    });
    if (!response.ok) {
      throw new Error(`${response.status} ${response.statusText}`);
    }
    return response.json();
  }

  _onClick(event) {
    const button = event.target.closest("button");
    if (!button) {
      return;
    }
    const tab = button.dataset.tab;
    if (tab) {
      this._activeTab = tab;
      this._render();
      return;
    }
    if (button.dataset.action === "refresh") {
      this._load();
      return;
    }
    if (button.dataset.earcon) {
      this._playEarcon(button.dataset.earcon);
      return;
    }
    const sampleId = button.dataset.sample;
    if (sampleId) {
      const sample = this._data?.sample_scenarios?.find((item) => item.id === sampleId);
      if (sample) {
        const user = this._sampleUser(sample);
        const response = this._sampleResponse(sample);
        const expected = this._sampleExpected(sample);
        this._draft = {
          user,
          response,
          expected: JSON.stringify(expected, null, 2),
        };
        this._activeTab = "scenarios";
        this._evaluate({
          user,
          response,
          expected,
        });
      }
    }
  }

  _onInput(event) {
    const field = event.target.dataset.field;
    if (!field) {
      return;
    }
    this._draftTouched = true;
    this._draft = { ...this._draft, [field]: event.target.value };
  }

  _onSubmit(event) {
    event.preventDefault();
    const form = event.target;
    if (form.dataset.form !== "scenario") {
      return;
    }
    let expected = {};
    try {
      expected = JSON.parse(this._draft.expected || "{}");
    } catch (err) {
      this._error = this._t("error.invalid_expected_json");
      this._render();
      return;
    }
    this._evaluate({
      user: this._draft.user,
      response: this._draft.response,
      expected,
    });
  }

  _playEarcon(name) {
    const file = this._data?.earcons?.files?.[name];
    if (!file?.url) {
      return;
    }
    const audio = new Audio(file.url);
    audio.play().catch((err) => {
      this._error = err.message || String(err);
      this._render();
    });
  }

  _render() {
    const entries = this._data?.entries || [];
    this.shadowRoot.innerHTML = `
      <style>${styles}</style>
      <main class="shell">
        <header class="topbar">
          <div>
            <h1>${escapeHtml(this._t("app.title"))}</h1>
            <div class="subline">${escapeHtml(this._statusLine(entries))}</div>
          </div>
          <button class="iconButton" data-action="refresh" title="${escapeHtml(this._t("common.refresh"))}">
            <ha-icon icon="mdi:refresh"></ha-icon>
          </button>
        </header>
        ${this._error ? `<div class="banner error">${escapeHtml(this._error)}</div>` : ""}
        <nav class="tabs" aria-label="${escapeHtml(this._t("aria.views"))}">
          ${TABS.map(([id, labelKey, icon]) => `
            <button class="tab ${this._activeTab === id ? "active" : ""}" data-tab="${id}">
              <ha-icon icon="${icon}"></ha-icon>
              <span>${escapeHtml(this._t(labelKey))}</span>
            </button>
          `).join("")}
        </nav>
        <section class="content">
          ${this._busy && !this._data ? this._renderLoading() : this._renderActive(entries)}
        </section>
      </main>
    `;
  }

  _statusLine(entries) {
    if (!this._data) {
      return this._busy ? this._t("status.loading") : this._t("status.waiting");
    }
    if (!entries.length) {
      return this._t("status.no_entries");
    }
    return this._t("status.entries", { count: entries.length });
  }

  _renderActive(entries) {
    if (!this._data) {
      return this._renderLoading();
    }
    if (this._activeTab === "runs") {
      return this._renderRuns(entries);
    }
    if (this._activeTab === "policies") {
      return this._renderPolicies(entries);
    }
    if (this._activeTab === "scenarios") {
      return this._renderScenarioLab();
    }
    if (this._activeTab === "search") {
      return this._renderSearch(entries);
    }
    if (this._activeTab === "memory") {
      return this._renderMemory(entries);
    }
    if (this._activeTab === "earcons") {
      return this._renderEarcons();
    }
    return this._renderRegression();
  }

  _renderLoading() {
    return `
      <div class="grid">
        <div class="surface skeleton"></div>
        <div class="surface skeleton"></div>
        <div class="surface skeleton wide"></div>
      </div>
    `;
  }

  _renderRuns(entries) {
    if (!entries.length) {
      return `<div class="empty">${escapeHtml(this._t("runs.empty"))}</div>`;
    }
    return `
      <div class="entryGrid">
        ${entries.map((entry) => `
          <article class="surface entry">
            <div class="sectionHead">
              <div>
                <h2>${escapeHtml(entry.title)}</h2>
                <div class="meta">${escapeHtml(entry.base_url || this._t("entry.base_url_missing"))}</div>
              </div>
              <span class="chip ok">${escapeHtml(entry.state || "unknown")}</span>
            </div>
            <div class="routeGrid">
              ${(entry.routes || []).map((route) => this._routeCard(route)).join("")}
            </div>
          </article>
        `).join("")}
      </div>
    `;
  }

  _renderPolicies(entries) {
    const policies = this._data?.prompt_policies || [];
    return `
      <div class="policyGrid">
        ${policies.map((policy) => `
          <article class="surface">
            <div class="sectionHead">
              <div>
                <h2>${escapeHtml(this._policyTitle(policy))}</h2>
                <div class="meta">${escapeHtml(this._policySpoken(policy))}</div>
              </div>
              <span class="chip ${policy.risk === "high" ? "bad" : "muted"}">${escapeHtml(policy.risk)}</span>
            </div>
            <div class="ruleList">
              ${(policy.rules || []).map((rule) => `<span>${escapeHtml(rule)}</span>`).join("")}
            </div>
          </article>
        `).join("") || `<div class="empty">${escapeHtml(this._t("policies.empty"))}</div>`}
      </div>
      ${entries.length ? `<div class="surface modelSurface">${entries.map((entry) => this._modelRows(entry.options)).join("")}</div>` : ""}
    `;
  }

  _renderScenarioLab() {
    return `
      <div class="workbench">
        <form class="surface form" data-form="scenario">
          <label>
            <span>${escapeHtml(this._t("scenario.user"))}</span>
            <textarea data-field="user" rows="3">${escapeHtml(this._draft.user)}</textarea>
          </label>
          <label>
            <span>${escapeHtml(this._t("scenario.response"))}</span>
            <textarea data-field="response" rows="4">${escapeHtml(this._draft.response)}</textarea>
          </label>
          <label>
            <span>${escapeHtml(this._t("scenario.expected"))}</span>
            <textarea class="codeInput" data-field="expected" rows="9">${escapeHtml(this._draft.expected)}</textarea>
          </label>
          <button class="primary" type="submit">
            <ha-icon icon="mdi:play"></ha-icon>
            <span>${escapeHtml(this._t("scenario.run"))}</span>
          </button>
        </form>
        ${this._renderResult()}
      </div>
    `;
  }

  _renderSearch(entries) {
    const providers = entries.flatMap((entry) => entry.search.providers || []);
    return `
      <div class="workbench">
        <article class="surface">
          <div class="sectionHead">
            <div>
              <h2>${escapeHtml(this._t("search.gating"))}</h2>
              <div class="meta">${providers.length ? providers.join(", ") : escapeHtml(this._t("search.no_providers"))}</div>
            </div>
          </div>
          <form class="compactForm" data-form="scenario">
            <textarea data-field="user" rows="3">${escapeHtml(this._draft.user)}</textarea>
            <textarea data-field="response" rows="3">${escapeHtml(this._draft.response)}</textarea>
            <button class="primary" type="submit">
              <ha-icon icon="mdi:magnify"></ha-icon>
              <span>${escapeHtml(this._t("search.evaluate"))}</span>
            </button>
          </form>
        </article>
        ${this._renderResult()}
      </div>
    `;
  }

  _renderMemory(entries) {
    const blocks = entries.flatMap((entry) =>
      (entry.memory?.sessions || []).map((session) => ({ entry, session }))
    );
    return `
      <div class="memoryGrid">
        ${blocks.map(({ entry, session }) => `
          <article class="surface">
            <div class="sectionHead">
              <div>
                <h2>${escapeHtml(entry.title)}</h2>
                <div class="meta">${escapeHtml(session.conversation_id)}</div>
              </div>
              <span class="chip muted">${escapeHtml(this._t("memory.turns", { count: (session.turns || []).length }))}</span>
            </div>
            ${session.summary ? `<p class="summary">${escapeHtml(session.summary)}</p>` : ""}
            <div class="turns">
              ${(session.turns || []).map((turn) => `
                <div class="turn">
                  <strong>${escapeHtml(this._t("memory.user"))}</strong>
                  <p>${escapeHtml(turn.user)}</p>
                  <strong>${escapeHtml(this._t("memory.assistant"))}</strong>
                  <p>${escapeHtml(turn.assistant)}</p>
                </div>
              `).join("")}
            </div>
          </article>
        `).join("") || `<div class="empty">${escapeHtml(this._t("memory.empty"))}</div>`}
      </div>
    `;
  }

  _renderEarcons() {
    const pack = this._data?.earcons || {};
    const files = Object.entries(pack.files || {});
    return `
      <div class="surface earconHeader">
        <div>
          <h2>${escapeHtml(pack.pack || this._t("earcon.no_pack"))}</h2>
          <div class="meta">${escapeHtml(this._t("earcon.meta", {
            sampleRate: pack.sample_rate || 0,
            targetLufs: pack.target_lufs || "?",
            peakDbfs: pack.true_peak_dbfs || "?",
          }))}</div>
        </div>
      </div>
      <div class="earconGrid">
        ${files.map(([name, file]) => `
          <article class="surface earcon">
            <div class="sectionHead">
              <div>
                <h2>${escapeHtml(name)}</h2>
                <div class="meta">${escapeHtml(this._earconPurpose(name, file))}</div>
              </div>
              <button class="iconButton" data-earcon="${escapeHtml(name)}" title="${escapeHtml(this._t("earcon.play", { name }))}">
                <ha-icon icon="mdi:play"></ha-icon>
              </button>
            </div>
            <div class="meterRow">
              <span>${escapeHtml(file.duration_ms)} ms</span>
              <span>${escapeHtml(file.lufs)} LUFS</span>
              <span>${escapeHtml(this._t("earcon.peak", { peak: file.peak_dbfs }))}</span>
            </div>
          </article>
        `).join("") || `<div class="empty">${escapeHtml(this._t("earcon.empty"))}</div>`}
      </div>
    `;
  }

  _renderRegression() {
    const samples = this._data?.sample_scenarios || [];
    return `
      <div class="regressionList">
        ${samples.map((sample) => `
          <article class="surface sample">
            <div>
              <h2>${escapeHtml(this._sampleName(sample))}</h2>
              <p>${escapeHtml(this._sampleUser(sample))}</p>
            </div>
            <button class="secondary" data-sample="${escapeHtml(sample.id)}">
              <ha-icon icon="mdi:play-outline"></ha-icon>
              <span>${escapeHtml(this._t("regression.run"))}</span>
            </button>
          </article>
        `).join("")}
      </div>
    `;
  }

  _routeCard(route) {
    return `
      <div class="route ${escapeHtml(route.kind)}">
        <span class="routeKind">${escapeHtml(route.kind)}</span>
        <strong>${escapeHtml(route.model)}</strong>
        <span>${route.max_tokens} tokens · ${escapeHtml(this._t("route.timeout", { seconds: route.timeout_s }))}</span>
      </div>
    `;
  }

  _modelRows(options) {
    const tiers = ["fast", "mid", "deep"];
    return `
      <div class="table">
        ${tiers.map((tier) => `
          <div class="row">
            <span class="tier ${tier}">${tier}</span>
            <strong>${escapeHtml(options.models[tier])}</strong>
            <span>${options.max_tokens[tier]} tokens</span>
            <span>${options.timeouts[tier]}s</span>
          </div>
        `).join("")}
      </div>
    `;
  }

  _renderResult() {
    if (!this._result) {
      return `<article class="surface result emptyState">${escapeHtml(this._t("result.empty"))}</article>`;
    }
    const result = this._result;
    const passed = result.passed ? this._t("result.passed") : this._t("result.failed");
    const search = result.search.allowed ? this._t("search.allowed") : this._t("search.blocked");
    return `
      <article class="surface result">
        <div class="sectionHead">
          <div>
            <h2>${escapeHtml(passed)}</h2>
            <div class="meta">${escapeHtml(this._t("result.meta", { route: result.route.kind, search }))}</div>
          </div>
          <span class="chip ${result.passed ? "ok" : "bad"}">${escapeHtml(passed)}</span>
        </div>
        <div class="spoken">${escapeHtml(result.spoken || "")}</div>
        ${(result.violations || []).length ? `
          <ul class="violations">
            ${result.violations.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}
          </ul>
        ` : ""}
        <pre>${escapeHtml(JSON.stringify(result, null, 2))}</pre>
      </article>
    `;
  }

  _locale() {
    const language = this.hass?.locale?.language || this.hass?.language || navigator.language || "en";
    return String(language).toLowerCase().startsWith("zh") ? "zh-Hans" : "en";
  }

  _t(key, params = {}) {
    const table = I18N[this._locale()] || I18N.en;
    const fallback = I18N.en[key] || key;
    return String(table[key] || fallback).replace(/\{(\w+)\}/g, (_match, name) =>
      params[name] ?? ""
    );
  }

  _defaultDraft(locale) {
    return { ...(DEFAULT_DRAFTS[locale] || DEFAULT_DRAFTS.en) };
  }

  _localize(value, fallback = "") {
    if (!value || typeof value !== "object") {
      return value || fallback;
    }
    const locale = this._locale();
    return value[locale] || value.en || value["zh-Hans"] || fallback;
  }

  _policyTitle(policy) {
    const key = `policy.${policy.id}.title`;
    return this._localize(policy.title_i18n, this._lookup(key, policy.title));
  }

  _policySpoken(policy) {
    const key = `policy.${policy.id}.spoken`;
    return this._localize(policy.spoken_i18n, this._lookup(key, policy.spoken));
  }

  _sampleName(sample) {
    const key = `sample.${sample.id}.name`;
    return this._localize(sample.name_i18n, this._lookup(key, sample.name));
  }

  _sampleUser(sample) {
    return this._localize(sample.user_i18n, sample.user);
  }

  _sampleResponse(sample) {
    return this._localize(sample.response_i18n, sample.response);
  }

  _sampleExpected(sample) {
    const value = sample.expected_i18n;
    if (!value || typeof value !== "object") {
      return sample.expected || {};
    }
    const locale = this._locale();
    return value[locale] || value.en || value["zh-Hans"] || sample.expected || {};
  }

  _earconPurpose(name, file) {
    const key = `earcon.${name}.purpose`;
    return this._localize(file.purpose_i18n, this._lookup(key, file.purpose || ""));
  }

  _lookup(key, fallback = "") {
    const table = I18N[this._locale()] || I18N.en;
    return table[key] || I18N.en[key] || fallback || "";
  }
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

const styles = `
  :host {
    color: var(--primary-text-color);
    display: block;
    min-height: 100vh;
    background: var(--primary-background-color);
  }

  * {
    box-sizing: border-box;
    letter-spacing: 0;
  }

  .shell {
    width: min(1280px, 100%);
    margin: 0 auto;
    padding: 20px;
  }

  .topbar {
    min-height: 68px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    border-bottom: 1px solid var(--divider-color);
    margin-bottom: 14px;
  }

  h1, h2, p {
    margin: 0;
  }

  h1 {
    font-size: 24px;
    font-weight: 650;
    line-height: 1.2;
  }

  h2 {
    font-size: 15px;
    font-weight: 650;
    line-height: 1.3;
  }

  .subline,
  .meta,
  .route span,
  .row span,
  .sample p {
    color: var(--secondary-text-color);
    font-size: 13px;
    line-height: 1.35;
  }

  button {
    min-height: 40px;
    border: 1px solid var(--divider-color);
    border-radius: 8px;
    background: var(--card-background-color);
    color: var(--primary-text-color);
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    font: inherit;
    cursor: pointer;
    white-space: nowrap;
  }

  button:hover {
    border-color: var(--primary-color);
  }

  button ha-icon {
    width: 20px;
    height: 20px;
    pointer-events: none;
  }

  .iconButton {
    width: 44px;
    padding: 0;
  }

  .primary {
    background: var(--primary-color);
    border-color: var(--primary-color);
    color: var(--text-primary-color);
    padding: 0 16px;
  }

  .secondary {
    padding: 0 14px;
  }

  .tabs {
    display: grid;
    grid-template-columns: repeat(7, minmax(0, 1fr));
    gap: 8px;
    margin: 14px 0 18px;
  }

  .tab {
    height: 44px;
    padding: 0 10px;
  }

  .tab.active {
    border-color: var(--primary-color);
    background: color-mix(in srgb, var(--primary-color) 14%, var(--card-background-color));
  }

  .tab span {
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .content {
    min-height: 420px;
  }

  .surface,
  .empty {
    background: var(--card-background-color);
    border: 1px solid var(--divider-color);
    border-radius: 8px;
  }

  .surface {
    padding: 16px;
  }

  .empty,
  .emptyState {
    min-height: 180px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--secondary-text-color);
  }

  .banner {
    border-radius: 8px;
    padding: 12px 14px;
    margin: 12px 0;
    border: 1px solid var(--divider-color);
  }

  .banner.error {
    color: var(--error-color);
    background: color-mix(in srgb, var(--error-color) 10%, var(--card-background-color));
  }

  .grid,
  .entryGrid,
  .policyGrid,
  .memoryGrid,
  .earconGrid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
    gap: 14px;
  }

  .workbench {
    display: grid;
    grid-template-columns: minmax(320px, 0.92fr) minmax(340px, 1.08fr);
    gap: 14px;
    align-items: start;
  }

  .sectionHead {
    min-height: 42px;
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 14px;
  }

  .chip {
    min-height: 26px;
    border-radius: 999px;
    display: inline-flex;
    align-items: center;
    padding: 0 10px;
    font-size: 12px;
    font-weight: 650;
    border: 1px solid var(--divider-color);
  }

  .chip.ok {
    color: var(--success-color);
    background: color-mix(in srgb, var(--success-color) 12%, transparent);
  }

  .chip.bad {
    color: var(--error-color);
    background: color-mix(in srgb, var(--error-color) 12%, transparent);
  }

  .chip.muted {
    color: var(--secondary-text-color);
  }

  .routeGrid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 10px;
  }

  .route {
    min-height: 112px;
    border: 1px solid var(--divider-color);
    border-radius: 8px;
    padding: 12px;
    display: grid;
    align-content: start;
    gap: 8px;
  }

  .route strong {
    min-width: 0;
    font-size: 13px;
    line-height: 1.35;
    overflow-wrap: anywhere;
  }

  .routeKind,
  .tier {
    width: max-content;
    min-height: 22px;
    border-radius: 999px;
    padding: 2px 8px;
    font-size: 12px;
    font-weight: 700;
    text-transform: uppercase;
  }

  .fast .routeKind,
  .tier.fast {
    color: #0b7a53;
    background: color-mix(in srgb, #0b7a53 13%, transparent);
  }

  .mid .routeKind,
  .tier.mid {
    color: #1d5fd1;
    background: color-mix(in srgb, #1d5fd1 13%, transparent);
  }

  .deep .routeKind,
  .tier.deep {
    color: #a25500;
    background: color-mix(in srgb, #a25500 15%, transparent);
  }

  .table {
    display: grid;
    gap: 8px;
  }

  .modelSurface {
    margin-top: 14px;
  }

  .ruleList {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }

  .ruleList span,
  .meterRow span {
    min-height: 26px;
    border-radius: 999px;
    border: 1px solid var(--divider-color);
    display: inline-flex;
    align-items: center;
    padding: 0 10px;
    color: var(--secondary-text-color);
    font-size: 12px;
  }

  .row {
    min-height: 46px;
    display: grid;
    grid-template-columns: 68px minmax(160px, 1fr) 96px 56px;
    align-items: center;
    gap: 10px;
    border-top: 1px solid var(--divider-color);
    padding-top: 8px;
  }

  .row strong {
    min-width: 0;
    overflow-wrap: anywhere;
    font-size: 13px;
  }

  .form,
  .compactForm {
    display: grid;
    gap: 12px;
  }

  label {
    display: grid;
    gap: 6px;
  }

  label span {
    font-size: 13px;
    color: var(--secondary-text-color);
  }

  textarea {
    width: 100%;
    resize: vertical;
    min-height: 76px;
    border: 1px solid var(--divider-color);
    border-radius: 8px;
    padding: 10px 12px;
    background: var(--primary-background-color);
    color: var(--primary-text-color);
    font: inherit;
    line-height: 1.45;
  }

  .codeInput,
  pre {
    font-family: var(--code-font-family, Menlo, Consolas, monospace);
    font-size: 12px;
  }

  .result {
    min-height: 260px;
    display: grid;
    align-content: start;
    gap: 12px;
  }

  .spoken {
    min-height: 44px;
    border-radius: 8px;
    padding: 12px;
    background: var(--primary-background-color);
    line-height: 1.45;
  }

  .violations {
    margin: 0;
    padding: 0 0 0 20px;
    color: var(--error-color);
  }

  pre {
    margin: 0;
    max-height: 320px;
    overflow: auto;
    border-radius: 8px;
    padding: 12px;
    background: var(--primary-background-color);
    color: var(--secondary-text-color);
  }

  .turns {
    display: grid;
    gap: 10px;
  }

  .turn {
    border-top: 1px solid var(--divider-color);
    padding-top: 10px;
    display: grid;
    gap: 4px;
  }

  .turn strong {
    color: var(--secondary-text-color);
    font-size: 12px;
    text-transform: uppercase;
  }

  .turn p,
  .summary {
    line-height: 1.45;
    overflow-wrap: anywhere;
  }

  .regressionList {
    display: grid;
    gap: 10px;
  }

  .earconHeader {
    min-height: 72px;
    display: flex;
    align-items: center;
    margin-bottom: 14px;
  }

  .earcon {
    min-height: 146px;
  }

  .meterRow {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }

  .sample {
    min-height: 78px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
  }

  .skeleton {
    min-height: 180px;
    background: linear-gradient(90deg, var(--card-background-color), var(--primary-background-color), var(--card-background-color));
  }

  .skeleton.wide {
    grid-column: 1 / -1;
  }

  @media (max-width: 900px) {
    .tabs {
      grid-template-columns: repeat(3, minmax(0, 1fr));
    }

    .workbench {
      grid-template-columns: 1fr;
    }

    .routeGrid {
      grid-template-columns: 1fr;
    }
  }

  @media (max-width: 560px) {
    .shell {
      padding: 12px;
    }

    .tabs {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .tab {
      justify-content: flex-start;
    }

    .grid,
    .entryGrid,
    .policyGrid,
    .memoryGrid,
    .earconGrid {
      grid-template-columns: 1fr;
    }

    .row {
      grid-template-columns: 1fr;
      align-items: start;
    }

    .sample {
      align-items: stretch;
      flex-direction: column;
    }
  }
`;

customElements.define("voice-harness-panel", VoiceHarnessPanel);
