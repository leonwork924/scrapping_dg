(() => {
  const CATEGORIES = [
    { id: "work", label: "Work" },
    { id: "exchange", label: "Exchange" },
    { id: "study", label: "Study" },
    { id: "research", label: "Research" },
  ];
  const MAX_ROWS_RENDERED = 300;

  const el = {
    tabs: document.getElementById("categoryTabs"),
    statTotal: document.getElementById("statTotal"),
    statNew: document.getElementById("statNew"),
    statSourceUpdated: document.getElementById("statSourceUpdated"),
    statChecked: document.getElementById("statChecked"),
    newList: document.getElementById("newEntriesList"),
    search: document.getElementById("registerSearch"),
    registerCount: document.getElementById("registerCount"),
    registerBody: document.getElementById("registerBody"),
  };

  let currentCategory = "work";
  let currentRows = [];
  let newSponsorsSummary = null;

  function buildTabs() {
    el.tabs.innerHTML = "";
    CATEGORIES.forEach(({ id, label }) => {
      const btn = document.createElement("button");
      btn.textContent = label;
      btn.setAttribute("aria-selected", id === currentCategory ? "true" : "false");
      btn.addEventListener("click", () => {
        if (id === currentCategory) return;
        currentCategory = id;
        [...el.tabs.children].forEach((b) =>
          b.setAttribute("aria-selected", b === btn ? "true" : "false")
        );
        loadCategory(id);
      });
      el.tabs.appendChild(btn);
    });
  }

  function fmtDate(iso) {
    if (!iso) return "—";
    const d = new Date(iso);
    if (isNaN(d)) return iso;
    return d.toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });
  }

  async function loadJSON(path) {
    const res = await fetch(path, { cache: "no-store" });
    if (!res.ok) throw new Error(`${path} -> ${res.status}`);
    return res.json();
  }

  function renderEmptyRegister(message) {
    el.registerBody.innerHTML = `<tr><td colspan="2" class="empty-state">${message}</td></tr>`;
    el.registerCount.textContent = "";
    el.search.disabled = true;
  }

  function renderTable(rows) {
    const q = el.search.value.trim().toLowerCase();
    const filtered = q
      ? rows.filter(
          (r) =>
            r.organisation.toLowerCase().includes(q) || r.kvk.includes(q)
        )
      : rows;

    const shown = filtered.slice(0, MAX_ROWS_RENDERED);
    el.registerBody.innerHTML = shown
      .map(
        (r) =>
          `<tr><td>${escapeHTML(r.organisation)}</td><td>${escapeHTML(r.kvk)}</td></tr>`
      )
      .join("") || `<tr><td colspan="2" class="empty-state">No matches.</td></tr>`;

    el.registerCount.textContent =
      filtered.length > MAX_ROWS_RENDERED
        ? `Showing ${MAX_ROWS_RENDERED} of ${filtered.length.toLocaleString()} matches — refine your search to see more.`
        : `${filtered.length.toLocaleString()} of ${rows.length.toLocaleString()} organisations.`;
  }

  function escapeHTML(str) {
    const d = document.createElement("div");
    d.textContent = str;
    return d.innerHTML;
  }

  function renderNewEntries(entry) {
    if (!entry || entry.is_baseline) {
      el.newList.innerHTML = `<li class="empty-state">${
        entry ? "Baseline just seeded — new organisations will show up after the next check." : "No data yet — waiting on the first scheduled run."
      }</li>`;
      return;
    }
    if (entry.new_count === 0) {
      el.newList.innerHTML = `<li class="empty-state">No new organisations since the last check.</li>`;
      return;
    }
    el.newList.innerHTML = entry.new_organisations
      .map(
        (r) =>
          `<li><span class="new-entries__org">${escapeHTML(r.organisation)}</span><span class="new-entries__kvk">KVK ${escapeHTML(r.kvk)}</span></li>`
      )
      .join("");
  }

  async function loadCategory(category) {
    renderEmptyRegister("Loading…");
    try {
      const data = await loadJSON(`data/sponsors_${category}.json`);
      currentRows = data.organisations || [];
      el.statTotal.textContent = data.count?.toLocaleString() ?? "—";
      el.statSourceUpdated.textContent = data.source_last_updated || "—";
      el.statChecked.textContent = fmtDate(data.scraped_at);

      const entry = newSponsorsSummary?.categories?.[category];
      el.statNew.textContent = entry && !entry.is_baseline ? `+${entry.new_count}` : "—";
      renderNewEntries(entry);

      el.search.disabled = false;
      el.search.value = "";
      renderTable(currentRows);
    } catch (err) {
      renderEmptyRegister("No data yet for this category — waiting on the first scheduled run.");
      el.statTotal.textContent = "—";
      el.statSourceUpdated.textContent = "—";
      el.statChecked.textContent = "—";
      el.statNew.textContent = "—";
      renderNewEntries(null);
    }
  }

  el.search.addEventListener("input", () => renderTable(currentRows));

  (async function init() {
    buildTabs();
    try {
      newSponsorsSummary = await loadJSON("data/new_sponsors.json");
    } catch (err) {
      newSponsorsSummary = null;
    }
    loadCategory(currentCategory);
  })();
})();
