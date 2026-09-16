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
  typePills: document.getElementById("typePills"),
  regionPills: document.getElementById("regionPills"),
  sortSelect: document.getElementById("sortSelect"),
  summary: document.getElementById("summary"),
  univSections: document.getElementById("univSections"),
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
      const regions = Array.isArray(r.region) ? r.region.filter(Boolean) : (r.region ? [r.region] : []);
      map.set(key, {
        key,
        university: r.university,
        campus: r.campus || null,
        regions: regions.length ? regions : ["기타"],
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

function escapeHtml(str) {
  return String(str).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[c]);
}

/* ---------- 목록 화면 ---------- */

// 검색어만 반영한 목록 (지역/유형 pill의 개수 표시는 서로의 선택을 반영하지 않고
// 항상 "검색어 기준 전체"에서 세므로, pill을 눌러도 다른 pill 개수가 안 튀지 않는다)
function getSearchedUniversities() {
  const q = state.search.trim().toLowerCase();
  if (!q) return state.universities;
  return state.universities.filter((u) => u.university.toLowerCase().includes(q));
}

function getFilteredUniversities() {
  return getSearchedUniversities().filter((u) => {
    if (state.region && !u.regions.includes(state.region)) return false;
    if (state.type && u.univ_type !== state.type) return false;
    return true;
  });
}

function sortUniversities(list) {
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

function renderPills() {
  const searched = getSearchedUniversities();

  const typeCounts = new Map();
  for (const u of searched) {
    if (state.region && !u.regions.includes(state.region)) continue;
    typeCounts.set(u.univ_type, (typeCounts.get(u.univ_type) || 0) + 1);
  }
  const typeTotal = [...typeCounts.values()].reduce((a, b) => a + b, 0);
  const typeList = [["", "전체", typeTotal], ...Array.from(typeCounts, ([k, v]) => [k, k || "기타", v])];
  renderPillGroup(els.typePills, typeList, state.type, (val) => { state.type = val; render(); });

  // 지역은 대학 하나가 여러 지역에 걸칠 수 있어서(한국폴리텍 등), 각 지역마다 개별 집계한다.
  const regionCounts = new Map();
  const countedUnivs = new Set();
  for (const u of searched) {
    if (state.type && u.univ_type !== state.type) continue;
    countedUnivs.add(u.key);
    for (const r of u.regions) regionCounts.set(r, (regionCounts.get(r) || 0) + 1);
  }
  const regionTotal = countedUnivs.size;
  const regionEntries = Array.from(regionCounts, ([k, v]) => [k, k || "기타", v])
    .sort((a, b) => b[2] - a[2]);
  const regionList = [["", "전체 지역", regionTotal], ...regionEntries];
  renderPillGroup(els.regionPills, regionList, state.region, (val) => { state.region = val; render(); });
}

function renderPillGroup(container, entries, activeVal, onPick) {
  container.innerHTML = "";
  const frag = document.createDocumentFragment();
  entries.forEach(([val, label, count]) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "pill" + (val === activeVal ? " active" : "");
    btn.textContent = `${label} ${count}`;
    btn.addEventListener("click", () => onPick(val));
    frag.appendChild(btn);
  });
  container.appendChild(frag);
}

function renderList() {
  renderPills();

  const filtered = getFilteredUniversities();
  els.summary.textContent = `표시 중: ${filtered.length}개 대학(캠퍼스)`;
  els.univSections.innerHTML = "";
  els.emptyState.hidden = filtered.length > 0;

  // 특정 지역을 골랐으면 섹션 하나, "전체"면 지역별 섹션으로 묶어서 원본 사이트처럼 보여준다.
  // 대학 하나가 여러 지역에 걸치면(한국폴리텍 등) 해당하는 지역 섹션 모두에 나타난다.
  const groups = new Map();
  for (const u of filtered) {
    const groupKeys = state.region ? [state.region] : u.regions;
    for (const groupKey of groupKeys) {
      if (!groups.has(groupKey)) groups.set(groupKey, []);
      groups.get(groupKey).push(u);
    }
  }
  const groupOrder = Array.from(groups.entries()).sort((a, b) => b[1].length - a[1].length);

  const frag = document.createDocumentFragment();
  for (const [regionName, list] of groupOrder) {
    const section = document.createElement("section");
    section.className = "region-section";
    const header = document.createElement("h2");
    header.className = "region-heading";
    header.innerHTML = `${escapeHtml(regionName)} <span>${list.length}개</span>`;
    section.appendChild(header);

    const grid = document.createElement("div");
    grid.className = "univ-grid";
    sortUniversities(list).forEach((u) => grid.appendChild(buildUnivCard(u)));
    section.appendChild(grid);

    frag.appendChild(section);
  }
  els.univSections.appendChild(frag);
}

function buildUnivCard(u) {
  const card = document.createElement("article");
  card.className = "univ-card";
  card.tabIndex = 0;
  card.innerHTML = `
    <div class="univ-card-top">
      <h3>${escapeHtml(u.university)}${u.campus ? `<span class="campus-badge">${escapeHtml(u.campus)}</span>` : ""}</h3>
      <span class="ratio-cell">${u.maxRatio.toFixed(2)} : 1<small> 최고</small></span>
    </div>
    <div class="univ-card-meta">
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
  return card;
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
els.sortSelect.addEventListener("change", (e) => { state.sort = e.target.value; render(); });
els.backBtn.addEventListener("click", closeDetail);
els.deptSearchInput.addEventListener("input", (e) => { state.deptSearch = e.target.value; renderDetail(); });
els.deptSortSelect.addEventListener("change", (e) => { state.deptSort = e.target.value; renderDetail(); });

loadData();
