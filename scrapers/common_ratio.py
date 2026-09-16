"""
경쟁률 위젯류(진학어플라이 addon, 유웨이어플라이 ratio 등) 공통 표 파서.

두 벤더 모두 구조가 사실상 같다 — 전형별로 표가 따로 있고, 표 헤더가
[ (전형)? (대학/계열)? (접수단위)? 모집단위 모집인원 지원인원 경쟁률 ] 조합이며,
전형 컬럼이 없는 경우 표 바로 앞의 "OOO 경쟁률 현황" 제목에서 전형명을 가져와야 한다.
그래서 대학/벤더별 분기 없이 헤더 텍스트를 읽어서 컬럼 위치를 판단하는 로직 하나로 처리한다.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from typing import Optional

from bs4 import BeautifulSoup

_HEADING_SUFFIX_RE = re.compile(r"(경쟁률|지원율)\s*현황$")


@dataclass
class RatioRecord:
    university: str
    campus: Optional[str]
    admission_type: str
    college: Optional[str]
    department: str
    capacity: int
    applicants: int
    ratio: float
    source_url: str


def _to_int(text: str) -> Optional[int]:
    text = text.strip().replace(",", "")
    if not text or text == "-":
        return None
    try:
        return int(text)
    except ValueError:
        return None


def _to_ratio(text: str) -> Optional[float]:
    text = text.strip()
    m = re.match(r"([\d.]+)\s*:\s*1", text)
    if m:
        return float(m.group(1))
    return None


def _heading_admission_type(table) -> str:
    node = table.find_previous_sibling()
    seen = 0
    while node is not None and seen < 5:
        text = node.get_text(strip=True)
        if text and _HEADING_SUFFIX_RE.search(text):
            return _HEADING_SUFFIX_RE.sub("", text).strip()
        if node.name == "table":
            break
        node = node.find_previous_sibling()
        seen += 1
    return ""


_DEPT_NAMES = ("모집단위", "모집학과")


def _find_dept_header(headers: list[str]) -> Optional[str]:
    """'모집단위(주간)'처럼 접미사가 붙는 경우도 있어서 부분일치로 찾는다."""
    for h in headers:
        if any(d in h for d in _DEPT_NAMES):
            return h
    return None


def _ratio_col_index(headers: list[str]) -> Optional[int]:
    """경쟁률/지원율 컬럼 위치를 찾는다. 그 앞 두 칸은 항상 모집/지원 인원이고,
    그 뒤에 '학과 홈페이지' 같은 부가 컬럼이 더 붙어도(유한대 등) 무시할 수 있다."""
    for i, h in enumerate(headers):
        if h in ("경쟁률", "지원율") and i >= 2:
            return i
    return None


def _is_detail_table(headers: list[str]) -> bool:
    if _find_dept_header(headers) is None:
        return False
    return _ratio_col_index(headers) is not None


def _try_wide_format(
    table, university: str, campus_default: Optional[str], source_url: str
) -> Optional[list[RatioRecord]]:
    """한국폴리텍/청강문화산업대 등 일부는 표 하나에 전형별 (모집/지원/경쟁률) 3열 세트가
    옆으로 나란히 붙는 '와이드' 형태를 쓴다 (스크린리더용 숨김 캡션 행이 섞여 있어서
    th만 있고 td는 없는 '순수 헤더 행'만 골라 마지막 두 개를 2단 헤더로 쓴다).
    """
    rows = table.find_all("tr")
    pure_header_rows = [r for r in rows if r.find_all("th") and not r.find_all("td")]
    if len(pure_header_rows) < 2:
        return None
    row_a, row_b = pure_header_rows[-2], pure_header_rows[-1]
    header_a = [th.get_text(strip=True) for th in row_a.find_all("th")]
    header_b = [th.get_text(strip=True) for th in row_b.find_all("th")]
    if not header_b or len(header_b) % 3 != 0:
        return None
    n_groups = len(header_b) // 3
    if not all(header_b[i * 3 : i * 3 + 3] == ["모집인원", "지원인원", "경쟁률"] for i in range(n_groups)):
        return None
    lead_count = len(header_a) - n_groups
    if lead_count < 1 or "모집단위" not in header_a[:lead_count]:
        return None

    lead_names = header_a[:lead_count]
    group_names = header_a[lead_count:]
    dept_idx = lead_names.index("모집단위")
    campus_idx = lead_names.index("캠퍼스") if "캠퍼스" in lead_names else None

    b_pos = rows.index(row_b)
    tail_len = n_groups * 3
    sticky_lead: list[Optional[str]] = [None] * lead_count
    records: list[RatioRecord] = []

    for row in rows[b_pos + 1 :]:
        tds = row.find_all("td")
        if not tds:
            continue
        vals = [c.get_text(strip=True) for c in tds]
        if len(vals) < tail_len:
            continue
        lead_vals = vals[:-tail_len] if len(vals) > tail_len else []
        rest = vals[-tail_len:]
        offset = lead_count - len(lead_vals)
        if offset < 0:
            continue
        sticky_lead[offset:] = lead_vals
        full_lead = sticky_lead[:]

        dept = full_lead[dept_idx]
        if not dept or dept.startswith("총계") or dept.startswith("소계"):
            continue
        row_campus = (full_lead[campus_idx] if campus_idx is not None else None) or campus_default

        for gi, gname in enumerate(group_names):
            cap_s, app_s, ratio_s = rest[gi * 3 : gi * 3 + 3]
            capacity = _to_int(cap_s)
            if not capacity:
                continue
            applicants = _to_int(app_s) or 0
            ratio_val = _to_ratio(ratio_s)
            if ratio_val is None:
                ratio_val = round(applicants / capacity, 2) if capacity else 0.0
            records.append(
                RatioRecord(
                    university=university,
                    campus=row_campus,
                    admission_type=gname,
                    college=None,
                    department=dept,
                    capacity=capacity,
                    applicants=applicants,
                    ratio=ratio_val,
                    source_url=source_url,
                )
            )

    return records


def parse_ratio_html(
    html: str, university: str, source_url: str, campus: Optional[str] = None
) -> list[RatioRecord]:
    soup = BeautifulSoup(html, "html.parser")
    records: list[RatioRecord] = []

    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if not rows:
            continue
        headers = [th.get_text(strip=True) for th in rows[0].find_all("th")]
        if not _is_detail_table(headers):
            wide = _try_wide_format(table, university, campus, source_url)
            if wide:
                records.extend(wide)
            continue

        ratio_idx = _ratio_col_index(headers)
        n_trailing = len(headers) - ratio_idx - 1  # 예: 유한대 "학과 홈페이지" 같은 꼬리 컬럼
        lead_headers = headers[: ratio_idx - 2]

        dept_name = _find_dept_header(lead_headers)
        if "접수단위" in lead_headers:
            dept_idx = lead_headers.index("접수단위")
            college_idx = lead_headers.index(dept_name) if dept_name in lead_headers else None
            type_idx = lead_headers.index("전형") if "전형" in lead_headers else None
        else:
            dept_idx = lead_headers.index(dept_name)
            # 모집단위 앞에 컬럼이 더 있으면(대학/계열 등, 이름 무관) 그게 college,
            # 그 앞에 하나 더 있으면 전형 컬럼이다.
            before = lead_headers[:dept_idx]
            college_idx = dept_idx - 1 if before else None
            type_idx = 0 if len(before) >= 2 else None

        heading_type = "" if type_idx is not None else _heading_admission_type(table)

        sticky: list[Optional[str]] = [None] * len(lead_headers)

        for row in rows[1:]:
            cells = row.find_all("td")
            if not cells:
                continue
            vals = [c.get_text(strip=True) for c in cells]
            if any(v.startswith("총계") or v.startswith("소계") for v in vals):
                continue
            core_len = len(vals) - n_trailing
            if core_len < 3:
                continue

            cap_s, app_s, ratio_s = vals[core_len - 3], vals[core_len - 2], vals[core_len - 1]
            lead_vals = vals[: core_len - 3]
            offset = len(lead_headers) - len(lead_vals)
            if offset < 0:
                continue
            sticky[offset:] = lead_vals
            full_lead = sticky[:]

            dept = full_lead[dept_idx] if dept_idx is not None else None
            if not dept:
                continue
            college = full_lead[college_idx] if college_idx is not None else None
            admission_type = full_lead[type_idx] if type_idx is not None else heading_type

            capacity = _to_int(cap_s)
            applicants = _to_int(app_s)
            ratio_val = _to_ratio(ratio_s)
            if capacity is None:
                continue
            if applicants is None:
                applicants = 0
            if ratio_val is None:
                ratio_val = round(applicants / capacity, 2) if capacity else 0.0

            records.append(
                RatioRecord(
                    university=university,
                    campus=campus,
                    admission_type=admission_type or "",
                    college=college or None,
                    department=dept,
                    capacity=capacity,
                    applicants=applicants,
                    ratio=ratio_val,
                    source_url=source_url,
                )
            )

    return records


def records_to_dicts(records: list[RatioRecord]) -> list[dict]:
    return [asdict(r) for r in records]
