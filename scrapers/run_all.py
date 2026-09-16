"""
data/universities.json 레지스트리를 읽어 등록된 모든 대학의 경쟁률을 수집하고
data/latest.json 으로 저장한다. GitHub Actions에서 주기적으로 이 스크립트를 실행한다.

새 대학 추가 방법은 README.md 참고.
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import jinhak_addon  # noqa: E402
import uway_ratio  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
UNIVERSITIES_PATH = ROOT / "data" / "universities.json"
# docs/ 가 GitHub Pages 배포 루트이므로 프론트엔드가 바로 fetch할 수 있도록
# 결과 JSON을 docs/ 아래에 둔다. data/universities.json은 스크래퍼 설정(입력)이고
# docs/data.json은 스크래핑 결과(출력)라는 점을 구분할 것.
OUTPUT_PATH = ROOT / "docs" / "data.json"

KST = timezone(timedelta(hours=9))

SCRAPERS = {
    "jinhak_addon": lambda uni: jinhak_addon.fetch_university(
        university=f"{uni['name']}",
        ratio_id=uni["params"]["ratio_id"],
        campus=uni.get("campus"),
    ),
    "uway_ratio": lambda uni: uway_ratio.fetch_university(
        university=f"{uni['name']}",
        url=uni["params"]["url"],
        campus=uni.get("campus"),
    ),
}


def load_registry() -> list[dict]:
    return json.loads(UNIVERSITIES_PATH.read_text(encoding="utf-8"))


def run() -> None:
    registry = load_registry()
    all_records: list[dict] = []
    errors: list[dict] = []

    for uni in registry:
        scraper_name = uni.get("scraper")
        fn = SCRAPERS.get(scraper_name)
        label = f"{uni['name']} ({uni.get('campus') or '-'})"
        if fn is None:
            errors.append({"university": label, "error": f"unknown scraper: {scraper_name}"})
            continue
        try:
            records = fn(uni)
            for r in records:
                r["region"] = uni.get("region")
                r["univ_type"] = uni.get("type")
                r["univ_id"] = uni.get("id")
            all_records.extend(records)
            print(f"[OK] {label}: {len(records)}건", file=sys.stderr)
        except Exception as e:  # noqa: BLE001
            errors.append({"university": label, "error": str(e)})
            print(f"[FAIL] {label}: {e}", file=sys.stderr)
        time.sleep(1)  # 서버 부하를 주지 않도록 간격을 둔다

    output = {
        "updated_at": datetime.now(tz=KST).isoformat(),
        "university_count": len({r["univ_id"] for r in all_records}),
        "record_count": len(all_records),
        "records": all_records,
        "errors": errors,
    }
    OUTPUT_PATH.write_text(
        json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\n총 {len(all_records)}건 저장 완료 -> {OUTPUT_PATH}", file=sys.stderr)


if __name__ == "__main__":
    run()
