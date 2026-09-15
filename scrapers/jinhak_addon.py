"""
진학어플라이 부가서비스(addon.jinhakapply.com) 경쟁률 위젯 파서.

많은 대학이 자체 입학처 홈페이지에 이 위젯을 그대로 임베드해서 씁니다.
URL 형태: https://addon.jinhakapply.com/RatioV1/RatioH/Ratio{ID}.html
같은 HTML 구조(표 기반)를 공유하므로 대학마다 파서를 새로 짤 필요 없이
이 모듈 하나로 여러 대학을 커버할 수 있습니다.

표는 세 종류가 섞여 있습니다:
  1) "전형별 경쟁률 현황" 총괄표 (전형명 / 모집인원 / 지원인원 / 경쟁률)
  2) 전형별 상세표 (전형 / 대학(단과대) / 모집단위 / 모집인원 / 지원인원 / 경쟁률)
  3) 특수교육대상자처럼 모집단위별 지원인원이 비어있고 총계만 있는 표

상세표(2)를 기준으로 모집단위 단위 레코드를 뽑아낸다.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from typing import Optional

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
}


@dataclass
class RatioRecord:
    university: str
    campus: Optional[str]
    admission_type: str  # 전형 (교과/종합/논술/실기 등 대분류가 아니라 전형명 원문)
    college: Optional[str]  # 단과대/대학
    department: str  # 모집단위
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


def fetch_html(ratio_id: str, timeout: int = 15) -> str:
    url = f"https://addon.jinhakapply.com/RatioV1/RatioH/Ratio{ratio_id}.html"
    resp = requests.get(url, headers=HEADERS, timeout=timeout)
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding or "utf-8"
    return resp.text


_HEADING_SUFFIX_RE = re.compile(r"경쟁률\s*현황$")


def _heading_admission_type(table) -> str:
    """표 앞의 <h2>학생부교과(추천형)경쟁률 현황</h2> 같은 제목에서 전형명을 뽑는다.
    전형 컬럼이 표 자체에 없는 대학(예: 한양대, 성균관대)에 필요하다.
    """
    node = table.find_previous_sibling()
    seen = 0
    while node is not None and seen < 3:
        text = node.get_text(strip=True)
        if text and _HEADING_SUFFIX_RE.search(text):
            return _HEADING_SUFFIX_RE.sub("", text).strip()
        if node.name == "table":
            break
        node = node.find_previous_sibling()
        seen += 1
    return ""


def _is_detail_table(headers: list[str]) -> bool:
    header_text = " ".join(headers)
    if "모집단위" not in header_text:
        return False
    if not any(k in header_text for k in ("모집인원", "모집")):
        return False
    if not any(k in header_text for k in ("지원인원", "지원")):
        return False
    return "경쟁률" in header_text


def parse(html: str, university: str, ratio_id: str, campus: Optional[str] = None) -> list[RatioRecord]:
    """대학마다 표 컬럼 구성이 다르다 (예: 건국대 전형/대학/모집단위 6열,
    한양대 대학/모집단위 5열 + 전형은 표 위 <h2> 제목, 서강대 모집단위/접수단위 5열,
    성균관대 모집단위 4열만). 컬럼 이름을 직접 읽어서 위치를 판단하므로
    대학별 분기 없이 이 로직 하나로 처리한다.
    """
    soup = BeautifulSoup(html, "html.parser")
    source_url = f"https://addon.jinhakapply.com/RatioV1/RatioH/Ratio{ratio_id}.html"
    records: list[RatioRecord] = []

    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if not rows:
            continue
        headers = [th.get_text(strip=True) for th in rows[0].find_all("th")]
        if not _is_detail_table(headers):
            continue

        # 마지막 3개 컬럼은 항상 모집인원/지원인원/경쟁률이고, 그 앞쪽
        # (lead_headers)이 전형/대학/모집단위/접수단위 조합이다.
        lead_headers = headers[:-3]

        dept_idx: Optional[int]
        college_idx: Optional[int]
        if "접수단위" in lead_headers:
            dept_idx = lead_headers.index("접수단위")
            college_idx = lead_headers.index("모집단위") if "모집단위" in lead_headers else None
        elif "모집단위" in lead_headers:
            dept_idx = lead_headers.index("모집단위")
            college_idx = lead_headers.index("대학") if "대학" in lead_headers else None
        else:
            dept_idx = None
            college_idx = None
        type_idx = lead_headers.index("전형") if "전형" in lead_headers else None

        heading_type = "" if type_idx is not None else _heading_admission_type(table)

        # rowspan으로 생략된 왼쪽 컬럼을 직전 행 값으로 채우기 위한 캐시.
        sticky: list[Optional[str]] = [None] * len(lead_headers)

        for row in rows[1:]:
            cells = row.find_all("td")
            if not cells:
                continue
            vals = [c.get_text(strip=True) for c in cells]
            if any(v.startswith("총계") for v in vals):
                continue
            if len(vals) < 3:
                continue

            cap_s, app_s, ratio_s = vals[-3], vals[-2], vals[-1]
            lead_vals = vals[:-3]
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


def fetch_university(university: str, ratio_id: str, campus: Optional[str] = None) -> list[dict]:
    html = fetch_html(ratio_id)
    return [asdict(r) for r in parse(html, university, ratio_id, campus)]


if __name__ == "__main__":
    import json
    import sys

    if len(sys.argv) < 3:
        print("usage: python jinhak_addon.py <university_name> <ratio_id> [campus]")
        raise SystemExit(1)

    uni, rid = sys.argv[1], sys.argv[2]
    campus_arg = sys.argv[3] if len(sys.argv) > 3 else None
    result = fetch_university(uni, rid, campus_arg)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"\n총 {len(result)}개 모집단위 레코드 수집", file=sys.stderr)
