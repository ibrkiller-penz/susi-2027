# 수시 실시간 경쟁률 대시보드 (연습용)

[taehoon8832.github.io/2026_susi](https://taehoon8832.github.io/2026_susi/) 같은 "수시 실시간 경쟁률" 사이트를
내년(2027학년도 수시)에 직접 운영해보기 전에, 올해(2026학년도 수시) 데이터로 미리 연습해보는 프로젝트입니다.

## 어떻게 동작하나

1. `data/universities.json` 에 등록된 대학 목록을 기준으로
2. `scrapers/` 안의 스크래퍼가 각 대학의 공개 경쟁률 페이지를 읽어서
3. `docs/data.json` 으로 결과를 합쳐 저장하고
4. `docs/` (GitHub Pages 루트)의 정적 대시보드가 그 JSON을 읽어 화면에 표로 보여준다.

갱신은 자동 주기 실행이 아니라 **수동 버튼**으로만 한다 — GitHub 저장소의 Actions 탭 →
"Update ratio data" → **Run workflow** 버튼을 누르면 2·3번 과정(스크래핑 → `docs/data.json` 커밋 →
Firebase Hosting 배포)이 한 번에 실행된다. (`gh workflow run "Update ratio data"` 로 터미널에서 눌러도 된다.)
GitHub Pages는 커밋만 반영하면 되니 별도 배포 단계 없이 자동으로 최신화된다.

Firebase 배포 단계는 저장소 시크릿 `FIREBASE_TOKEN`이 있어야 동작한다. 없으면 그 스텝만 실패하고
데이터 커밋 자체는 정상적으로 끝난다. 시크릿 만드는 법은 아래 "Firebase Hosting 자동 배포 설정" 참고.

## 데이터 소스에 대해 알아둘 것

대학마다 경쟁률을 공개하는 방식이 다르다. 조사해보니 크게 세 갈래다.

- **진학어플라이 부가서비스 (`addon.jinhakapply.com/RatioV1/RatioH/Ratio{ID}.html`)** —
  4년제 상당수가 자기 입학처 페이지에 이 위젯을 그대로 임베드해서 쓴다.
  `scrapers/jinhak_addon.py`가 담당. **새 대학 추가**: `"<대학명> 경쟁률 서비스"`로 검색해서
  `addon.jinhakapply.com` 링크를 찾고, URL 끝의 숫자 ID를 등록.
- **유웨이어플라이 (`ratio.uwayapply.com/<opaque 문자열>`)** — 주로 전문대가 쓰는 동일 계열 위젯.
  URL이 base64 비슷한 opaque 문자열이라 ID를 조립할 수 없어서, 전체 URL을 그대로 저장한다.
  `scrapers/uway_ratio.py`가 담당.
- **전문대학 스마트경쟁률 포털 (`apply.jinhakapply.com/SmartRatio`)** — 위 두 위젯을 쓰는 전문대를
  한 번에 찾을 수 있는 곳. 이 페이지의 `a.rate` 요소마다 `data-label`(학교명), `data-link`(실제
  경쟁률 URL) 속성이 있어서, 브라우저 콘솔에서 한 번에 긁으면 여러 학교를 동시에 찾을 수 있다.
  단, 여기 없는 4년제(서울대/연세대/고려대 등)는 계속 개별 검색으로 찾아야 하고,
  이 포털에 있어도 앞의 두 위젯이 아닌 대학 자체 시스템(gyu.ac.kr, ccn.ac.kr 등)을 쓰는 학교는
  그 학교 전용 스크래퍼를 따로 만들어야 한다 (아직 미구현).

진학어플라이/유웨이 위젯 파싱 로직은 `scrapers/common_ratio.py` 하나에 모아뒀고,
`jinhak_addon.py`/`uway_ratio.py`는 URL 조립 방식만 다른 얇은 래퍼다. 같은 위젯이라도 표 구조가
대학마다 미묘하게 다르다는 걸 확인했다 — 컬럼 이름(모집단위/모집학과, 경쟁률/지원율), 전형 컬럼의
유무(없으면 "OOO 경쟁률(지원율) 현황" 제목에서 가져옴), 끝에 "학과 홈페이지" 같은 여분 컬럼이 붙는
경우, 심지어 전형별 (모집/지원/경쟁률) 3열 세트가 한 표에 옆으로 나란히 붙는 "와이드" 형태(한국폴리텍,
청강문화산업대)까지 있다. 그래서 고정 컬럼 개수로 분기하지 않고 헤더 텍스트를 읽어서 그때그때
위치를 판단한다 — 새 대학을 추가했는데 레코드가 0건이거나 `admission_type`이 비면
`common_ratio.py`의 `_is_detail_table`/`_ratio_col_index`/`_try_wide_format`이 그 학교의 표
구조를 인식 못 하는 것이니 먼저 `BeautifulSoup`으로 실제 헤더를 찍어볼 것.

### 후보를 찾았다고 바로 등록하면 안 되는 이유

검색으로 나오는 `addon.jinhakapply.com/.../Ratio{ID}.html` 후보 중 상당수가 과거 학년도(정시 포함)
캐시 페이지다. 등록 전에 반드시 `jinhak_addon.fetch_html(id)`로 받아서 `TitleYear`가 올해 수시
학년도인지, `TitleService`가 "수시모집"인지 확인할 것. (예: 성균관대 `10920451`은 2026학년도라 제외함 —
2027학년도 ID를 아직 못 찾았다.) 반대로 `SmartRatio` 포털에서 뽑은 링크는 "지금 접수중"인 것만
긁은 거라 이 검증이 따로 필요 없다.

## 로컬에서 실행하기

```bash
pip install -r requirements.txt
python scrapers/run_all.py        # docs/data.json 생성/갱신
python -m http.server 8000 --directory docs   # http://localhost:8000 에서 확인
```

## 새 대학 추가하기

1. `"<대학명> 경쟁률 서비스"`로 검색하거나(4년제), `apply.jinhakapply.com/SmartRatio`에서
   `a.rate` 요소의 `data-label`/`data-link`를 긁어서(전문대, 여러 개 한 번에) 데이터 소스를 찾는다.
2. `addon.jinhakapply.com` 위젯이면 `data/universities.json`에 추가:
   ```json
   { "id": "고유id", "name": "학교명", "campus": "캠퍼스명 또는 null", "region": "지역", "type": "4년제|전문대", "scraper": "jinhak_addon", "params": { "ratio_id": "URL 끝 숫자" } }
   ```
3. `ratio.uwayapply.com` 위젯이면:
   ```json
   { "id": "고유id", "name": "학교명", "campus": null, "region": "지역", "type": "전문대", "scraper": "uway_ratio", "params": { "url": "전체 URL 그대로" } }
   ```
4. 둘 다 아니면(대학 자체 시스템) `scrapers/`에 새 모듈을 만들고 `scrapers/run_all.py`의
   `SCRAPERS` 딕셔너리에 등록한다.

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

## Firebase Hosting 자동 배포 설정 (`FIREBASE_TOKEN` 시크릿)

Actions의 Run workflow 버튼으로 Firebase 배포까지 자동으로 하려면, CI용 토큰을 발급해서
저장소 시크릿으로 등록해야 한다. **토큰은 채팅이나 다른 사람 손을 거치지 않고, 본인 터미널에서
바로 GitHub로 넣는 게 안전**하다 — 아래 두 명령을 본인 컴퓨터 터미널에서 순서대로 실행:

```bash
firebase login:ci
```

브라우저가 열리면 로그인/동의하고, 터미널에 출력되는 토큰 문자열을 복사한다. 그다음:

```bash
gh secret set FIREBASE_TOKEN --repo ibrkiller-penz/susi-2027
```

실행하면 토큰을 붙여넣으라고 뜨는데, 그때 붙여넣으면 끝. (`gh`가 없으면 GitHub 저장소 →
Settings → Secrets and variables → Actions → New repository secret 에서 이름 `FIREBASE_TOKEN`,
값에 토큰을 붙여넣어도 된다.)

토큰은 계정 전체에 대한 Firebase 배포 권한을 가지므로 절대 코드에 커밋하거나 다른 사람과
공유하지 말 것. 재발급하려면 `firebase login:ci` 를 다시 실행하면 된다.
