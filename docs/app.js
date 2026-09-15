const state = {
  records: [],
  search: "",
  region: "",
  type: "",
  sort: "ratio-desc",
};

const els = {
  updatedAt: document.getElementById("updatedAt"),
  searchInput: document.getElementById("searchInput"),
  regionFilter: document.getElementById("regionFilter"),
  typeFilter: document.getElementById("typeFilter"),
  sortSelect: document.getElementById("sortSelect"),
  summary: document.getElementById("summary"),
  tableBody: document.getElementById("tableBody"),
  emptyState: document.getElementById("emptyState"),
};

async function loadData() {
  try {
    const res = await fetch(`data.json?t=${Date.now()}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const payload = await res.json();
    state.records = payload.records || [];
    renderMeta(payload);
    populateRegionOptions();
    render();
  } catch (err) {
    els.updatedAt.textContent = "데이터를 불러오지 못했습니다.";
    console.error(err);
  }
}

function renderMeta(payload) {
  const updated = payload.updated_at
    ? new Date(payload.updated_at).toLocaleString("ko-KR")
    : "-";
  els.updatedAt.textContent = `업데이트: ${updated} · 대학 ${payload.university_count ?? 0}곳 · ${payload.record_count ?? 0}개 모집단위`;
}

function populateRegionOptions() {
  const regions = Array.from(new Set(state.records.map((r) => r.region).filter(Boolean))).sort();
  for (const region of regions) {
    const opt = document.createElement("option");
    opt.value = region;
    opt.textContent = region;
    els.regionFilter.appendChild(opt);
  }
}

function getFiltered() {
  const q = state.search.trim().toLowerCase();
  return state.records.filter((r) => {
    if (state.region && r.region !== state.region) return false;
    if (state.type && r.univ_type !== state.type) return false;
    if (q) {
      const haystack = `${r.university} ${r.department} ${r.admission_type}`.toLowerCase();
      if (!haystack.includes(q)) return false;
    }
    return true;
  });
}

function getSorted(rows) {
  const sorted = [...rows];
  switch (state.sort) {
    case "ratio-asc":
      sorted.sort((a, b) => a.ratio - b.ratio);
      break;
    case "applicants-desc":
      sorted.sort((a, b) => b.applicants - a.applicants);
      break;
    case "university":
      sorted.sort((a, b) => a.university.localeCompare(b.university, "ko"));
      break;
    case "ratio-desc":
    default:
      sorted.sort((a, b) => b.ratio - a.ratio);
      break;
  }
  return sorted;
}

function render() {
  const filtered = getSorted(getFiltered());

  els.summary.textContent = `표시 중: ${filtered.length}개 모집단위`;
  els.tableBody.innerHTML = "";
  els.emptyState.hidden = filtered.length > 0;

  const frag = document.createDocumentFragment();
  filtered.forEach((r, i) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${i + 1}</td>
      <td>${escapeHtml(r.university)}</td>
      <td>${escapeHtml(r.campus || "-")}</td>
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

function escapeHtml(str) {
  return String(str).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[c]);
}

els.searchInput.addEventListener("input", (e) => { state.search = e.target.value; render(); });
els.regionFilter.addEventListener("change", (e) => { state.region = e.target.value; render(); });
els.typeFilter.addEventListener("change", (e) => { state.type = e.target.value; render(); });
els.sortSelect.addEventListener("change", (e) => { state.sort = e.target.value; render(); });

loadData();
