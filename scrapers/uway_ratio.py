"""
유웨이어플라이(ratio.uwayapply.com) 경쟁률 위젯 파서.

URL이 학교마다 완전히 다른 opaque 문자열이라(예: ratio.uwayapply.com/Sl5K...==)
ID를 조립할 수 없다. data/universities.json에 전체 URL을 그대로 저장해서 쓴다.
표 파싱 로직은 scrapers/common_ratio.py 를 공유한다 (진학어플라이 addon과 구조가 같음).
"""
from __future__ import annotations

import requests

import common_ratio

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
}


def fetch_html(url: str, timeout: int = 15) -> str:
    resp = requests.get(url, headers=HEADERS, timeout=timeout)
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding or "utf-8"
    return resp.text


def parse(html: str, university: str, url: str, campus=None):
    return common_ratio.parse_ratio_html(html, university, url, campus)


def fetch_university(university: str, url: str, campus=None) -> list[dict]:
    html = fetch_html(url)
    return common_ratio.records_to_dicts(parse(html, university, url, campus))


if __name__ == "__main__":
    import json
    import sys

    if len(sys.argv) < 3:
        print("usage: python uway_ratio.py <university_name> <url> [campus]")
        raise SystemExit(1)

    uni, url = sys.argv[1], sys.argv[2]
    campus_arg = sys.argv[3] if len(sys.argv) > 3 else None
    result = fetch_university(uni, url, campus_arg)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"\n총 {len(result)}개 모집단위 레코드 수집", file=sys.stderr)
