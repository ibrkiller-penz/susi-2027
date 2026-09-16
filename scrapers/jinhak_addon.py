"""
진학어플라이 부가서비스(addon.jinhakapply.com) 경쟁률 위젯 파서.

URL 형태: https://addon.jinhakapply.com/RatioV1/RatioH/Ratio{ID}.html
실제 표 파싱 로직은 scrapers/common_ratio.py 를 공유한다 (유웨이 위젯과 구조가 같음).
"""
from __future__ import annotations

import requests

import common_ratio

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
}


def fetch_html(ratio_id: str, timeout: int = 15) -> str:
    url = f"https://addon.jinhakapply.com/RatioV1/RatioH/Ratio{ratio_id}.html"
    resp = requests.get(url, headers=HEADERS, timeout=timeout)
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding or "utf-8"
    return resp.text


def parse(html: str, university: str, ratio_id: str, campus=None):
    source_url = f"https://addon.jinhakapply.com/RatioV1/RatioH/Ratio{ratio_id}.html"
    return common_ratio.parse_ratio_html(html, university, source_url, campus)


def fetch_university(university: str, ratio_id: str, campus=None) -> list[dict]:
    html = fetch_html(ratio_id)
    return common_ratio.records_to_dicts(parse(html, university, ratio_id, campus))


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
