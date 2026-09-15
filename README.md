# 수시 실시간 경쟁률 대시보드 (연습용)

[taehoon8832.github.io/2026_susi](https://taehoon8832.github.io/2026_susi/) 같은 "수시 실시간 경쟁률" 사이트를
내년(2027학년도 수시)에 직접 운영해보기 전에, 올해(2026학년도 수시) 데이터로 미리 연습해보는 프로젝트입니다.

## 어떻게 동작하나

1. `data/universities.json` 에 등록된 대학 목록을 기준으로
2. `scrapers/` 안의 스크래퍼가 각 대학의 공개 경쟁률 페이지를 읽어서
3. `docs/data.json` 으로 결과를 합쳐 저장하고
4. `docs/` (GitHub Pages 루트)의 정적 대시보드가 그 JSON을 읽어 화면에 표로 보여준다.

갱신은 자동 주기 실행이 아니라 **수동 버튼**으로만 한다 — GitHub 저장소의 Actions 탭 →
"Update ratio data" → **Run workflow** 버튼을 누르면 2번 과정이 실행되어 `docs/data.json`을 갱신하고
커밋한다. (`gh workflow run "Update ratio data"` 로 터미널에서 눌러도 된다.) GitHub Pages는 그 커밋을
자동으로 반영하지만, Firebase Hosting 쪽은 별도로 `npx firebase-tools deploy --only hosting --project susi-3c093`를
로컬에서 한 번 더 실행해야 최신 데이터가 올라간다.

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
대학별 스크래퍼를 하나씩 추가하는 식으로 점진적으로 넓혀가야 한다. 현재 등록: 건국대(서울/글로컬),
한양대(서울), 홍익대, 동국대(서울), 서강대 — 6개 캠퍼스.

같은 `addon.jinhakapply.com` 위젯이라도 대학마다 표 컬럼 구성이 다르다는 걸 확인했다
(전형 컬럼이 아예 없고 `<h2>OOO경쟁률 현황</h2>` 제목에서 전형명을 가져와야 하는 곳도 있고,
"대학" 컬럼 없이 모집단위만 있는 곳도 있음). `jinhak_addon.py`의 `parse()`는 고정된 컬럼 개수로
분기하지 않고, 각 표의 헤더 텍스트를 읽어서 전형/대학/모집단위/접수단위 위치를 그때그때 찾는
방식으로 짜여 있다 — 새 대학을 추가했는데 `admission_type`이 비거나 레코드가 0건이면 먼저
`_is_detail_table`과 헤더 매핑 로직이 그 대학의 표 구조를 인식하는지부터 확인할 것.

### 후보를 찾았다고 바로 등록하면 안 되는 이유

검색으로 나오는 `addon.jinhakapply.com/.../Ratio{ID}.html` 후보 중 상당수가 과거 학년도(정시 포함)
캐시 페이지다. 등록 전에 반드시 `jinhak_addon.fetch_html(id)`로 받아서 `TitleYear`가 올해 수시
학년도인지, `TitleService`가 "수시모집"인지 확인할 것. (예: 성균관대 `10920451`은 2026학년도라 제외함 —
2027학년도 ID를 아직 못 찾았다.)

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

## 배포 (Firebase Hosting, 도메인 선점용)

내년 실사용을 위해 Firebase Hosting 사이트 이름을 미리 선점해뒀다: `2027susi`, `2028susi`,
`2029susi`, `susi-2028` (모두 같은 Firebase 프로젝트 `susi-3c093` 아래, `firebase.json`의
hosting 배열에 타겟으로 매핑되어 있음). 로컬에서 `firebase login` 후:

```bash
python scrapers/run_all.py
npx firebase-tools deploy --only hosting --project susi-3c093
```

하면 네 도메인 모두에 `docs/` 내용이 그대로 배포된다.
