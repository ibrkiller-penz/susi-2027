const state = {
  records: [],
  universities: [], // 대학+캠퍼스 단위로 집계된 목록
  search: "",
  region: "",
  type: "",
  sort: "ratio-desc",
  view: "list", // "list" | "detail"
  selectedKey: null,
  deptSearch: "",
  deptSort: "ratio-desc",
};

const els = {
  updatedAt: document.getElementById("updatedAt"),
  listView: document.getElementById("listView"),
  detailView: document.getElementById("detailView"),
  searchInput: document.getElementById("searchInput"),
  regionFilter: document.getElementById("regionFilter"),
  typeFilter: document.getElementById("typeFilter"),
  sortSelect: document.getElementById("sortSelect"),
  summary: document.getElementById("summary"),
  univGrid: document.getElementById("univGrid"),
  emptyState: document.getElementById("emptyState"),
  backBtn: document.getElementById("backBtn"),
  detailTitle: document.getElementById("detailTitle"),
  detailSource: document.getElementById("detailSource"),
  deptSearchInput: document.getElementById("deptSearchInput"),
  deptSortSelect: document.getElementById("deptSortSelect"),
  tableBody: document.getElementById("tableBody"),
};

function univKey(r) {
  return `${r.university}::${r.campus || ""}`;
}

async function loadData() {
  try {
    const res = await fetch(`data.json?t=${Date.now()}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const payload = await res.json();
    state.records = payload.records || [];
    buildUniversities();
    renderMeta(payload);
    populateRegionOptions();
    render();
  } catch (err) {
    els.updatedAt.textContent = "데이터를 불러오지 못했습니다.";
    console.error(err);
  }
}

function buildUniversities() {
  const map = new Map();
  for (const r of state.records) {
    const key = univKey(r);
    if (!map.has(key)) {
      map.set(key, {
        key,
        university: r.university,
        campus: r.campus || null,
        region: r.region,
        univ_type: r.univ_type,
        source_url: r.source_url,
        deptCount: 0,
        maxRatio: 0,
        totalApplicants: 0,
        totalCapacity: 0,
      });
    }
    const u = map.get(key);
    u.deptCount += 1;
    u.maxRatio = Math.max(u.maxRatio, r.ratio);
    u.totalApplicants += r.applicants;
    u.totalCapacity += r.capacity;
  }
  state.universities = Array.from(map.values());
}

function renderMeta(payload) {
  const updated = payload.updated_at
    ? new Date(payload.updated_at).toLocaleString("ko-KR")
    : "-";
  els.updatedAt.textContent = `업데이트: ${updated} · 대학 ${payload.university_count ?? 0}곳 · ${payload.record_count ?? 0}개 모집단위`;
}

function populateRegionOptions() {
  const regions = Array.from(new Set(state.universities.map((u) => u.region).filter(Boolean))).sort();
  for (const region of regions) {
    const opt = document.createElement("option");
    opt.value = region;
    opt.textContent = region;
    els.regionFilter.appendChild(opt);
  }
}

function escapeHtml(str) {
  return String(str).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[c]);
}

/* ---------- 목록 화면 ---------- */

function getFilteredUniversities() {
  const q = state.search.trim().toLowerCase();
  return state.universities.filter((u) => {
    if (state.region && u.region !== state.region) return false;
    if (state.type && u.univ_type !== state.type) return false;
    if (q && !u.university.toLowerCase().includes(q)) return false;
    return true;
  });
}

function getSortedUniversities(list) {
  const sorted = [...list];
  switch (state.sort) {
    case "ratio-asc":
      sorted.sort((a, b) => a.maxRatio - b.maxRatio);
      break;
    case "applicants-desc":
      sorted.sort((a, b) => b.totalApplicants - a.totalApplicants);
      break;
    case "university":
      sorted.sort((a, b) => a.university.localeCompare(b.university, "ko"));
      break;
    case "ratio-desc":
    default:
      sorted.sort((a, b) => b.maxRatio - a.maxRatio);
      break;
  }
  return sorted;
}

function renderList() {
  const filtered = getSortedUniversities(getFilteredUniversities());
  els.summary.textContent = `표시 중: ${filtered.length}개 대학(캠퍼스)`;
  els.univGrid.innerHTML = "";
  els.emptyState.hidden = filtered.length > 0;

  const frag = document.createDocumentFragment();
  filtered.forEach((u) => {
    const card = document.createElement("article");
    card.className = "univ-card";
    card.tabIndex = 0;
    card.innerHTML = `
      <div class="univ-card-top">
        <h3>${escapeHtml(u.university)}${u.campus ? `<span class="campus-badge">${escapeHtml(u.campus)}</span>` : ""}</h3>
        <span class="ratio-cell">${u.maxRatio.toFixed(2)} : 1<small> 최고</small></span>
      </div>
      <div class="univ-card-meta">
        <span>${escapeHtml(u.region || "-")}</span>
        <span>${escapeHtml(u.univ_type || "-")}</span>
        <span>${u.deptCount}개 모집단위</span>
        <span>지원 ${u.totalApplicants.toLocaleString("ko-KR")}명</span>
      </div>
      <a class="source-link" href="${escapeHtml(u.source_url)}" target="_blank" rel="noopener" onclick="event.stopPropagation()">출처 페이지 →</a>
    `;
    card.addEventListener("click", () => openDetail(u.key));
    card.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") openDetail(u.key);
    });
    frag.appendChild(card);
  });
  els.univGrid.appendChild(frag);
}

/* ---------- 상세 화면 ---------- */

function openDetail(key) {
  state.selectedKey = key;
  state.view = "detail";
  state.deptSearch = "";
  els.deptSearchInput.value = "";
  render();
}

function closeDetail() {
  state.view = "list";
  state.selectedKey = null;
  render();
}

function getDetailRecords() {
  const q = state.deptSearch.trim().toLowerCase();
  const rows = state.records.filter((r) => univKey(r) === state.selectedKey);
  const filtered = rows.filter((r) => {
    if (!q) return true;
    return `${r.admission_type} ${r.department}`.toLowerCase().includes(q);
  });
  switch (state.deptSort) {
    case "ratio-asc":
      filtered.sort((a, b) => a.ratio - b.ratio);
      break;
    case "applicants-desc":
      filtered.sort((a, b) => b.applicants - a.applicants);
      break;
    case "ratio-desc":
    default:
      filtered.sort((a, b) => b.ratio - a.ratio);
      break;
  }
  return filtered;
}

function renderDetail() {
  const univ = state.universities.find((u) => u.key === state.selectedKey);
  if (!univ) {
    closeDetail();
    return;
  }
  els.detailTitle.textContent = `${univ.university}${univ.campus ? ` (${univ.campus})` : ""}`;
  els.detailSource.href = univ.source_url;

  const rows = getDetailRecords();
  els.tableBody.innerHTML = "";
  const frag = document.createDocumentFragment();
  rows.forEach((r, i) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${i + 1}</td>
      <td>${escapeHtml(r.admission_type)}</td>
      <td>${escapeHtml(r.department)}</td>
      <td>${r.capacity}</td>
      <td>${r.applicants.toLocaleString("ko-KR")}</td>
      <td class="ratio-cell">${r.ratio.toFixed(2)} : 1</td>
    `;
    frag.appendChild(tr);
  });
  els.tableBody.appendChild(frag);
}

/* ---------- 공통 렌더 ---------- */

function render() {
  const isList = state.view === "list";
  els.listView.hidden = !isList;
  els.detailView.hidden = isList;
  if (isList) {
    renderList();
  } else {
    renderDetail();
  }
}

els.searchInput.addEventListener("input", (e) => { state.search = e.target.value; render(); });
els.regionFilter.addEventListener("change", (e) => { state.region = e.target.value; render(); });
els.typeFilter.addEventListener("change", (e) => { state.type = e.target.value; render(); });
els.sortSelect.addEventListener("change", (e) => { state.sort = e.target.value; render(); });
els.backBtn.addEventListener("click", closeDetail);
els.deptSearchInput.addEventListener("input", (e) => { state.deptSearch = e.target.value; renderDetail(); });
els.deptSortSelect.addEventListener("change", (e) => { state.deptSort = e.target.value; renderDetail(); });

loadData();
