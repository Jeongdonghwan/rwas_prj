# 수원개인회생 사이트

수원 지역(구·동)·직업별 개인회생 랜딩 페이지를 대량 생성하는 Flask SSR 사이트.
전체 기획은 [suwon-gaein-hoesaeng-plan.md](suwon-gaein-hoesaeng-plan.md) — **작업 전 반드시 해당 문서의 Phase 표(§9)와 규정(§1-1)을 확인할 것.**

## 실행

```bash
pip install -r requirements.txt
python run.py            # http://127.0.0.1:5000 (SQLite: instance/dev.db 자동 생성)
```

- 환경변수: `.env.example` 참고. `DATABASE_URL` 비우면 SQLite, 운영은 MariaDB(pymysql).
- 어드민: `/admin/inquiries` — HTTP Basic, 기본 admin/admin (`ADMIN_USER`/`ADMIN_PASSWORD`로 변경).
- 배포는 `/deploy` 스킬 사용 (Cafe24 멀티사이트 서버).

## 구조

```
app/
  __init__.py        create_app 팩토리, site 컨텍스트 주입, db.create_all()
  config.py          Config + SITE_DEFAULTS(업체명·전화·주소 — 업체 확정 시 여기 교체)
  models.py          Gu/Dong/Job/CaseType/ContentBlock/Faq/Post/Inquiry
  routes/            main.py(고정) ko.py(한글 URL 리졸버) board.py(사례) contact.py(폼) admin.py(접수·사례 관리) area.py/job.py(구 URL 301)
  templates/         base.html + _header/_footer/_cta/_mobile_bar/_breadcrumb 파셜
  static/css/site.css  static/js/site.js
suwon-proto/         HTML 프로토타입 5장 (메인·동·직업·블로그 리스트·상세) — 디자인 원본
seed/                (Phase 3) dong.csv, job.csv, faq.csv
```

## Phase 진행 상태 (2026-09-14)

| Phase | 내용 | 상태 |
|---|---|---|
| 0 | 골격, config, DB 연결, base.html, CSS 토큰 | ✅ 완료 |
| 1 | 메인 + 고정 페이지 10 (하드코딩) | ✅ 완료 |
| 2 | 상담폼 POST + inquiry 저장 + 어드민 접수 목록 | ✅ 완료 (기본형) |
| 3 | DB 모델 + seed 커맨드 (gu/dong/job/faq/content_block) | ✅ 완료 — `flask seed` (FLASK_APP=run.py) |
| 4 | /area/ 허브·구·동 31페이지 + variant 로직 | ✅ 완료 |
| 5 | /job/ 허브·상세 16 + /case-type/ 8 | ✅ 완료 |
| 6 | 진행 사례 게시판(블로그형, 단일 보드) + 어드민 글쓰기(Toast UI) | ✅ 완료 — 블로그는 사용자 결정으로 생략 |
| 7 | sitemap·robots·RSS·canonical·JSON-LD·OG | ⬜ 다음 (canonical·OG·FAQPage JSON-LD는 선반영됨) |
| 8 | Claude API 콘텐츠 생성 (선택) | ⬜ |
| 9 | Cafe24 배포, 서치어드바이저 등록 | ⬜ |

### Phase 3~5 구현 메모
- 시드 데이터: `seed/*.csv` + `seed/content_blocks/{key}_{variant}.html`. 수정 후 `FLASK_APP=run.py flask seed`로 재적재(전체 삭제 후 재삽입).
- 동은 법정동 통합 31개. `dong.adjacent_slugs`(JSON)로 인접 동 링크, `variant_set`(A/B/C)으로 본문 블록·FAQ 회전 선택 → 중복 콘텐츠 방지.
- FAQ 풀: `faq.kind` = `qa`(Q&A) / `concern`(상단 "자주 묻는 것" 리스트, question_tpl만 사용). 변수는 Jinja(`{{dong}}` `{{gu}}` `{{job}}` `{{name}}`) — `app/content.py`의 `pick_faqs`/`get_block`.
- 동→직업 크로스링크 3개는 `(dong.id + i*5) % len(jobs)` 회전.
- FAQPage JSON-LD는 `partials/faq_jsonld.html` (동·구·직업·상황 페이지 head에 포함).

### 2026-09-21 대규모 수정 (원문: Downloads/사이트(수정).hwpx — 의뢰인 수정요청서)
- **팔레트 (최종): 화이트/차콜 뉴트럴 + 골드는 포인트만** — 공식 로고(골드)에 맞추되, UI 전반에 골드를 깔면 "AI스럽다" 피드백(9-21) → 골드는 **로고·CTA 버튼(--green-bright)·히어로 강조(em/kicker)·다크섹션 라벨**에만. 액센트/아이콘/링크(--green-2)는 차콜(#4c4a44), 틴트(--mint)는 뉴트럴 그레이. 골드 배경 버튼은 어두운 글자(#1c1b16).
- **로고 투명화 주의**: 흰배경 로고를 투명화할 때 밝기 비례 알파를 쓰면 골드 중간톤까지 반투명해져 로고가 뿌옇게 깨짐 → **알파는 거의 이진**(밝기 232 이하 완전 불투명, 232~246만 램프)으로 처리할 것. logo.png는 표시폭의 4배(920px)로 저장.
- **로고**: `img/logo.png`(가로형, 흰배경→투명 처리), `img/emblem.png`(기둥 엠블럼). 헤더·푸터에 이미지 로고, 파비콘=흰 라운드+엠블럼. OG도 로고 포함 재생성.
- **브랜드명 "수원개인회생파산 법률사무소 레이"** / 주소 **1002호** / **24시간 상담·주말 예약제**.
- **"무료" 표현 전면 금지(변호사법, 의뢰인 지시)** — 무료상담·상담무료 등 사용 불가. 대체: "전국 비대면 상담", "익명 상담". 전 템플릿·시드에서 제거 완료, 재도입 금지.
- **자가진단 v2 "1분 자격진단"** (site.js initQuiz): 분기형 — Q1 소득 유무로 회생/파산 트랙 분기. 회생 트랙: 실수령액·월상환액 **숫자 입력**(콤마 포맷) → 채무 구간 → 재산 **멀티선택**(자동차/부동산 선택 시 가액 팔로업) → 최근대출(있으면 시기→사용처 팔로업) → 연체 → 부양가족. 결과 = "나의 채무상황 분석" 카드(상환부담 % 계산) + 판정문 + ✓/! 3칸 + "왜 이런 결과가 나왔나요?" 접기 + 순화 문구("자가진단은 여기까지입니다…"). 영업성 문구 금지.
- 메인 개편: 진행방식 4카드(맞춤형 채무진단/합리적인 변제계획/체계적인 사건관리/신속한 상담안내), "한눈에 보기" 삭제→"이런 경우에도" 4카드(연체 전에도/신규채무 확인/재산이 있어도/법적조치 확인), 고민 체크 8문항 교체, 제도비교는 .specs 행형(회생 변제기간 "2년(24개월)까지 가능", 파산 면책 "비면책채권 제외" 명시, 레퍼런스 카피 제거), 비용 4행+"비용만 먼저 결정하지 않습니다", 일하는 방식 01~04.
- 히어로: 키커 "개인회생 상담 · 개인파산 상담 · 채무조정 · 법률상담", 칩(비대면/익명/직접상담/분할), 네임카드 삭제, 버튼 "1분 자격진단"·"전화상담". 변호사 사진 태그·about에서 "제1회 변호사시험" 삭제(스트립 통계엔 유지). about 사무소 정보 표 삭제. FAQ "배우자 재산과 소득은"으로 수정.
- 미해결: 수정요청서의 "키워드별 페이지에 오타" — 위치 미특정, 의뢰인 확인 필요.
- **2차 수정(같은 날)**: 헤더/푸터 로고는 이미지 텍스트 축소가 깨져 보여 **엠블럼 이미지+웹폰트 텍스트 조합(.lname/.flogo)**으로 확정. 히어로 문구 "감당하기 어려워진 채무, 개인회생으로 다시 시작할 수 있습니다"+새 서브카피. "이런 경우에도" 4카드는 **파스텔 4색(.pastel .t1~t4)+하단 인포바(.infobar)**, 제도비교는 탭 폐기→**3열 컬러헤더 카드(.pcmp/.pcol c1~c3, 블루/퍼플/그린+01~03 뱃지+아이콘 rows+파스텔 풋터)**, 진행절차는 메인=**아이콘 타임라인(.tl, 7단계+연결선)** / process 페이지=**8단계 상세 rows(.prows2, 주요 확인사항 박스)+속도 요인+단계별 안내 카드**. 비용은 카드형 리스트(.costcard). 직업별은 지역과 같은 4열 카테고리 그리드(job_groups), 상황별 2카드. **자격진단은 의뢰인이 준 9문항 고정형으로 확정(분기·숫자입력 폐기)** + "← 이전으로" 뒤로가기, 선택 답 하이라이트(.picked), Q2/Q5 소글씨 노트 포함. 멀티컬러 파스텔은 이 두 섹션(이런경우에도/제도비교)+process 안내 카드에만 허용.

### 브랜딩·디자인 (2026-09-14 리디자인 — 색상은 위 9-21 항목이 우선)
- **실제 업체 확정**: 수원개인회생 법률사무소 레이(LEI), 대표변호사 이재열, 사업자 333-41-00086, 2016년 개업, 원희캐슬광교 D동 10층 1001호. 값은 `app/config.py` SITE_DEFAULTS·LAWYER에 (약력·경력·자문기업 포함).
- **컬러는 네이비+블루 (2026-09-14 최종)**: 그린 톤은 사용자가 거부("초록색톤 별론데") → 테헤란 레퍼런스처럼 네이비(#1c3d6e)+브라이트 블루(#2f6fe8)+라이트블루 틴트로 전환. **주의: CSS 변수명은 --green/--green-2/--green-bright/--mint 등을 그대로 쓰지만 실값은 네이비/블루임** (전면 치환 비용 때문). 새 색 추가 시 블루 계열로.
- **디자인 참고 프로젝트: `C:\side_Prj\ortho_prj`** (사용자 지정) — 그 문법을 이식함: 실사진 풀블리드 히어로+켄번즈 줌+어두운 오버레이, 우측 중앙 세로형 퀵메뉴(흰 카드, 아이콘+라벨, TOP 버튼), 카드 상단 그라데이션 바 scaleX 호버, 혼합 굵기 헤드라인(`.thin`), SCROLL 힌트(세로 텍스트+애니 라인).
- **이미지 정책(2026-09-14)**: 대표변호사 사진은 히어로에서 빼고(모바일에서 얼굴 클로즈업 이상하다는 피드백) **소개 페이지·메인 변호사 섹션·동 페이지 사이드에만** 사용. 나머지는 Unsplash 무료 스톡(상업용 무료·저작자표시 불요): `hero-justice.webp`(정의의 여신, 히어로 배경), `bg-library.webp`(자가진단 다크 섹션 배경), `bg-court.webp`(CTA밴드 배경), `consult.webp`(체크리스트 imgsplit), `books.webp`(예비). 원본 ID는 Unsplash photo-1589829545856-d10d557cf95f / 1505664194779 / 1436450412740 / 1450101499163 / 1479142506502.
- **제도 비교 탭 섹션**(사용자 요청으로 추가): 메인 "개인회생·파산·신용회복, 뭐가 다를까?" — `.tabbox`+`.tabs2`(data-tabs/data-target, site.js)+`.minis` 4칸+`.whofor`+`.corebox`. 내용 수정 시 index.html의 cmp-rehab/cmp-bankruptcy/cmp-workout 패널.
- **히어로(최종 v6)**: 정의의 여신 스톡사진(hero-justice.webp)이 우측 60% 배경(kb 줌), 좌→우 네이비 그라데이션 오버레이, 좌측에 kicker+헤드라인+버튼(자가진단·전화)+칩, 우하단 흰 네임카드, 하단 SCROLL 힌트. 모바일(≤960)은 사진 풀배경+진한 오버레이+센터 정렬, 네임카드·힌트 숨김. **헤더 상담버튼·히어로 무료상담 버튼 없음(퀵메뉴·하단 폼이 대체)** — 초록 점 배지류 금지 유지. 헤드라인: "감당할 수 없는 빚, 법으로 정리할 수 있습니다".
- **플로팅 퀵메뉴**: `_mobile_bar.html`의 `.float` — 전화/상담 신청/TOP 세로 카드(ortho식, 카톡 없음), <960에서 숨고 하단 mbar(전화/상담신청 2분할)로 대체. TOP 스크롤은 site.js.
- **주의: headless 크롬은 최소 창폭(~500px) 클램프가 있어 좁은 모바일 스크린샷이 잘려 보임** → 모바일 확인은 scratchpad의 iframe 기법(390px iframe을 넓은 창에서 캡처) 사용. 클릭 시뮬레이션은 same-origin이 필요하므로 wrapper를 app/static/에 임시로 두고 테스트 후 삭제.
- **버그 이력(재발 주의)**: ① 모바일 풀스크린 메뉴 — `.hdr`의 backdrop-filter가 fixed 자식(.gnb)의 containing block이 되어 메뉴가 안 펼쳐짐 → `body.nav-open .hdr{backdrop-filter:none}`으로 해제(헤더에 filter/transform 추가 시 재발 가능). ② 리빌 관찰자 — threshold 0.12는 세로로 긴 요소에서 영영 발화 안 할 수 있음 → `threshold:0 + rootMargin -60px` 사용 유지.
- 프로필 사진 크롭: 원본(Downloads/CSY_5372, EXIF 회전 주의)은 머리 위 여백이 큼 → **y180부터 4:5 크롭**한 `lawyer-card.webp`(720×900)를 모든 곳(히어로·소개·동 사이드)에 사용. lawyer-900.webp는 원본 비율 백업.
- 스탯 스트립·3단계 카드·기준 카드에는 인라인 SVG 라인 아이콘(index.html 상단 `ico()` 매크로: shield/award/landmark/briefcase/clipboard/phone/banknote/calendar/percent/clock). 새 아이콘 필요 시 매크로에 추가.
- **디자인 v3 (2026-09-14 확정, 테헤란 랜딩 참고)**: 화이트 기반, **부드럽게** — 라운드 카드(--r:16px)·소프트 섀도우·필 버튼/칩·볼드 산세리프(세리프 폰트 제거, Pretendard 800 헤딩). 히어로는 다크그린 라디얼 + 센터 정렬(배지 필 + 칩 4개 + 로드 시 heroUp 스태거 애니메이션), 그 아래 4열 스탯 스트립 + 라운드 상담바. 카드 그리드는 `.cards`/`.card`(+`.num`), 스크롤 시 `.stagger`(자식 순차 등장)·`.reveal`. FAQ 아코디언은 개별 라운드 카드형.
- 베이지/크림 금지("AI티" 피드백). **골드는 전면 퇴출(2026-09-14 최종)** — 액센트 전부 블루(--green-2/--green-bright)·라이트블루(--mint). 영문 장식 라벨(AT A GLANCE 등)·장식 원 금지. CSS `--navy`/`--red`/`--serif`는 구명칭 별칭.
- **동적 요소 허용으로 방침 변경**(사용자 지시): 스크롤 리빌(.reveal), 카운트업(data-count), FAQ 아코디언(dl.qa 자동, 콘텐츠는 DOM 상주라 SEO 무관, `.qa.static`은 제외), 1분 자가진단(#quiz, site.js) — 기획서 §6-1의 "애니메이션 배제"는 폐기.
- 대표 사진: `app/static/img/lawyer-900.webp`(세로), `lawyer-card.webp`(4:5). 원본 Downloads/CSY_5372 (EXIF 회전 주의).
- suwon-proto/는 구(네이비) 디자인 — 참고용으로만. 현행 디자인 소스는 `app/static/css/site.css`.
- 자가진단 결과 문구는 "가능성/참고용, 법적 판단 아님" 워딩 유지(광고규정).

### Phase 6 구현 메모 (사례 게시판)
- **블로그 없음** — 진행 사례 단일 보드(사용자 결정). 모델 `Post`(post 테이블), 공개 라우트 `app/routes/board.py`: `/사례/`(8개/페이지, /사례/page/N/), `/사례/<slug>/`(조회수 증가, 이전/다음, 최신 5). 블로그형 카드 리스트(.blog-grid/.bcard) + 글 상세(.post-*) — CSS는 기존 클래스 재사용.
- 어드민: `/admin/cases` 목록·공개토글·삭제, `/admin/cases/new|<id>/edit` — **Toast UI Editor**(uicdn CDN, WYSIWYG→HTML), 본문 이미지 드래그 업로드 `/admin/upload`(webp 1400w), 썸네일 업로드(webp 960w), 저장 경로 `app/static/uploads/YYYY/MM/`. 슬러그는 제목에서 자동(한글 허용, 중복 시 -2). 요약 비우면 본문 앞 120자.
- 메인에 "결과가 궁금하다면, 진행 사례부터" 최신 4건 섹션(글 없으면 숨김), GNB에 진행 사례 추가.
- **주의**: 로컬 dev.db에 예시 사례 3건 있음(디자인 확인용) — **운영 배포 시 이 글들은 없음(flask seed에 post 미포함), 실제 사례는 어드민에서 작성**. 사례 글에는 "사실 위주·결과 보장 없음" 고지 박스가 상세 하단에 자동 출력됨.
- 본문 HTML은 sanitize 없이 저장(어드민 전용 작성 전제) — 어드민 계정 관리 주의, 필요 시 bleach 추가.

### 확정 사항 (2026-09-14)
- **상담 전화 1644-6755로 통일** (SITE_DEFAULTS phone/phone_link). **카카오톡 상담은 전면 제거** — 버튼·링크·문구·seed 데이터 모두 삭제, kakao_url 키도 없음. 다시 넣지 말 것.
- **오시는 길/지도 전면 제거** — 메인 오시는길 섹션·contact 지도 삭제, /contact/는 "상담 신청" 페이지(GNB 라벨도 변경). 주소는 푸터·소개·상담신청 표에만 텍스트로.
- **상담 폼은 메인 맨 하단** (#consult 섹션, .quick.bottom) — 히어로의 #form 앵커도 여기로 스크롤.
- **변호사 프로필 리디자인**: 골드 제거(사이트에서 골드 전면 퇴출) — 사진 위 네이비 반투명 네임태그(.lawyer-photo .tag), 약력 2열 리스트, 경력/주요활동 카드는 회색 헤더+파란 바(.bio-card h3::before).

### 미결 사항
- **이메일·도메인** → `app/config.py` SITE_DEFAULTS 교체
- **동별 transit_note의 소요시간·경로는 추정치** — 오픈 전 실측/지도 확인 필요 (seed/dong.csv 수정 후 재시드)
- 폰트 self-host(woff2) 전환은 배포 전(Phase 7~9)에 — 현재 CSS @import CDN

## 규칙 (요약 — 원문은 기획서 §1-1, §6)

**콘텐츠(변호사 광고규정):**
- "100% 인가", "무조건 면책", "최저가", 타 사무소 비교, 결과 보장 표현 금지
- 전문분야 등록 없이 "전문" 표기 금지 → "개인회생 사건을 다룹니다" 식으로
- 지역 페이지가 지점처럼 오인되지 않게: "OO동에서 오시는 길" 표현. 푸터에 지점 아님 고지

**디자인:**
- ~~기획서 §6의 "무장식·명조·각진" 규칙은 폐기됨~~ → **위 "브랜딩·디자인" 섹션이 현행 기준** (네이비+블루, 화이트 기반, 라운드+소프트 섀도우, ortho_prj 문법). suwon-proto/는 참고용 구버전.
- 블로그용 CSS 클래스는 site.css에 준비되어 있음: .blog-grid .bcard .post-head .post-body .tags .pn .pager .cat-tabs .side-list

**기술:**
- **URL: 지역·직업·상황 페이지는 한글이 정식** (사용자 결정, 2026-09-14 — 기획서 §2의 "한글 URL 금지" 폐기): `/{이름}-개인회생/` 플랫 구조. 예: `/매탄동-개인회생/`, `/장안구-개인회생/`, `/직장인-개인회생/`, `/도박빚-개인회생/`. 허브는 `/지역별-개인회생/` `/직업별-개인회생/` `/상황별-개인회생/`. 라우트는 `app/routes/ko.py`(단일 리졸버: gu.name → dong.name → job.slug_ko → case.slug_ko 순 매칭). 구 영문 URL(/area/... /job/... /case-type/...)은 area.py/job.py에서 **301 리다이렉트**. 직업·상황은 `slug_ko` 컬럼(seed CSV에 포함), 동·구는 name 그대로. 새 링크는 `url_for('ko.page', name=...)` / `url_for('ko.area_hub')` 등 사용.
- 고정 페이지 URL은 영문 유지(/about/ 등). 트레일링 슬래시 통일. FAQ 콘텐츠는 DOM 상주(아코디언은 JS 표시용). H1 페이지당 1개
- 상담폼은 `partials/consult_form.html` 재사용, hidden `source_path`로 유입 페이지 추적
- 템플릿 변수 치환은 Jinja2 (`{{dong}}` 형식으로 DB 저장)
