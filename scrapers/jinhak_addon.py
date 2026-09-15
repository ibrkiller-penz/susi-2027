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


def parse(html: str, university: str, ratio_id: str, campus: Optional[str] = None) -> list[RatioRecord]:
    soup = BeautifulSoup(html, "html.parser")
    source_url = f"https://addon.jinhakapply.com/RatioV1/RatioH/Ratio{ratio_id}.html"
    records: list[RatioRecord] = []

    for table in soup.find_all("table"):
        header_cells = [th.get_text(strip=True) for th in table.find_all(["th"])]
        header_text = " ".join(header_cells)
        # 상세표는 "대학"과 "모집단위" 컬럼을 함께 가진다.
        if "모집단위" not in header_text or "대학" not in header_text:
            continue

        current_admission_type = None
        current_college = None

        for row in table.find_all("tr"):
            cells = row.find_all("td")
            if not cells:
                continue
            cell_text = [c.get_text(strip=True) for c in cells]

            # 총계 행은 스킵 (rowspan 첫 컬럼이 "총계"인 경우 포함)
            if any(t.startswith("총계") for t in cell_text):
                continue

            # rowspan으로 생략된 컬럼(전형/대학)을 보정하기 위해
            # 컬럼 수가 6개(전형,대학,모집단위,모집,지원,경쟁률)가 아니면
            # 앞에서부터 누락된 컬럼을 이전 값으로 채운다.
            n = len(cell_text)
            if n == 6:
                admission_type, college, dept, cap, app, ratio = cell_text
                current_admission_type, current_college = admission_type, college
            elif n == 5:
                # 전형 또는 대학 하나가 rowspan으로 생략된 경우
                # 대학이 생략됐다고 가정 (같은 대학 내 다음 모집단위)
                college, dept, cap, app, ratio = cell_text
                admission_type = current_admission_type
                current_college = college
            elif n == 4:
                dept, cap, app, ratio = cell_text
                admission_type = current_admission_type
                college = current_college
            else:
                continue

            capacity = _to_int(cap)
            applicants = _to_int(app)
            ratio_val = _to_ratio(ratio)
            if capacity is None or not dept:
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
