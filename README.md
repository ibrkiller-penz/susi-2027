# 수시 실시간 경쟁률 대시보드 (연습용)

[taehoon8832.github.io/2026_susi](https://taehoon8832.github.io/2026_susi/) 같은 "수시 실시간 경쟁률" 사이트를
내년(2027학년도 수시)에 직접 운영해보기 전에, 올해(2026학년도 수시) 데이터로 미리 연습해보는 프로젝트입니다.

## 어떻게 동작하나

1. `data/universities.json` 에 등록된 대학 목록을 기준으로
2. `scrapers/` 안의 스크래퍼가 각 대학의 공개 경쟁률 페이지를 읽어서
3. `docs/data.json` 으로 결과를 합쳐 저장하고
4. `docs/` (GitHub Pages 루트)의 정적 대시보드가 그 JSON을 읽어 화면에 표로 보여준다.

GitHub Actions(`.github/workflows/update.yml`)가 20분마다 2번 과정을 자동 실행해서 `docs/data.json`을 갱신하고
커밋 → Pages가 자동으로 최신 데이터를 서빙한다.

## 데이터 소스에 대해 알아둘 것

대학마다 경쟁률을 공개하는 방식이 다르다. 조사해보니 크게 두 갈래다.

- **진학어플라이 부가서비스 (`addon.jinhakapply.com/RatioV1/RatioH/Ratio{ID}.html`)**
  꽤 많은 대학이 이 위젯을 자기 입학처 페이지에 그대로 임베드해서 쓴다. HTML 표 구조가 대부분 동일해서
  `scrapers/jinhak_addon.py` 하나로 여러 대학을 커버할 수 있다. **새 대학을 추가하려면**
  `"<대학명> 경쟁률 서비스"`로 검색해서 `addon.jinhakapply.com` 링크를 찾고, URL 끝의 숫자 ID를
  `data/universities.json`에 등록하면 끝.
- **대학 자체 시스템**: 서울대·연세대·고려대 등 상당수는 자체 입학처 사이트에 직접 표를 그린다.
  이런 곳은 페이지 구조가 제각각이라 대학별로 `scrapers/` 안에 파서를 하나씩 더 만들어야 한다.
  (아직 미구현 — 이번 연습에서 다음 단계로 추가해나갈 부분)

즉 "전체 대학 풀 클론"은 한 번에 되는 게 아니라, `jinhak_addon` 계열부터 채우고 나머지는
대학별 스크래퍼를 하나씩 추가하는 식으로 점진적으로 넓혀가야 한다. 지금은 건국대(서울/글로컬) 2곳만
등록된 상태 — 골격이 맞는지 확인하는 첫 단계.

### 알려진 파싱 이슈

- 건국대 글로컬(충주) 캠퍼스 페이지는 표 컬럼 구성이 서울캠퍼스와 살짝 달라서 `전형`(admission_type)
  값이 비어 있다. `jinhak_addon.py`의 컬럼 개수 분기(`n == 6/5/4`) 로직을 그 페이지에 맞춰 한 번 더
  다듬어야 한다.

## 로컬에서 실행하기

```bash
pip install -r requirements.txt
python scrapers/run_all.py        # docs/data.json 생성/갱신
python -m http.server 8000 --directory docs   # http://localhost:8000 에서 확인
```

## 새 대학 추가하기

1. `"<대학명> 경쟁률 서비스"`로 검색해서 데이터 소스를 찾는다.
2. `addon.jinhakapply.com` 위젯이면 `data/universities.json`에 아래 형태로 한 줄 추가:
   ```json
   { "id": "고유id", "name": "학교명", "campus": "캠퍼스명 또는 null", "region": "지역", "type": "4년제|전문대", "scraper": "jinhak_addon", "params": { "ratio_id": "URL 끝 숫자" } }
   ```
3. 자체 시스템이면 `scrapers/`에 새 모듈을 만들고 `scrapers/run_all.py`의 `SCRAPERS` 딕셔너리에 등록한다.

## 배포 (GitHub Pages)

저장소 Settings → Pages → Source를 `Deploy from a branch`, 브랜치는 `main`, 폴더는 `/docs`로 설정하면 된다.
