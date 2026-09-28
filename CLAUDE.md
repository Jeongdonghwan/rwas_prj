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
| 7 | sitemap·robots·RSS·canonical·JSON-LD·OG | ✅ 완료 (2026-09-24) |
| 8 | Claude API 콘텐츠 생성 (선택) | ⬜ |
| 9 | Cafe24 배포, 서치어드바이저 등록 | ⬜ |

### Phase 3~5 구현 메모
- 시드 데이터: `seed/*.csv` + `seed/content_blocks/{key}_{variant}.html`. 수정 후 `FLASK_APP=run.py flask seed`로 재적재(전체 삭제 후 재삽입).
- 동은 법정동 통합 31개. `dong.adjacent_slugs`(JSON)로 인접 동 링크. ~~`variant_set`(A/B/C)~~ → **해시 회전으로 대체됨**(아래 "중복 콘텐츠 방지" 참고). `variant_set` 컬럼·CSV 값은 남아 있지만 **더 이상 선택에 쓰지 않는다**.
- FAQ 풀: `faq.kind` = `qa`(Q&A) / `concern`(상단 "자주 묻는 것" 리스트, question_tpl만 사용). 변수는 Jinja(`{{dong}}` `{{gu}}` `{{job}}` `{{name}}`) — `app/content.py`의 `pick_faqs`/`get_block`.
- 동→직업 크로스링크 3개는 `(dong.id + i*5) % len(jobs)` 회전.
- FAQPage JSON-LD는 `partials/faq_jsonld.html` (동·구·직업·상황 페이지 head에 포함).

### 2026-09-21 대규모 수정 (원문: Downloads/사이트(수정).hwpx — 의뢰인 수정요청서)
- **팔레트 (9-23 최종): 화이트 + 딥 버건디(#7c2231, CTA #b13a4a) + 무채 차콜 다크섹션. 골드는 로고에서만.** 블루도 거부됨("블루 말고, AI티 안 나게") → 국내 로펌 관행색인 버건디/와인 채택. 파스텔 정보 섹션(4색 카드·제도비교 블루/퍼플/그린)은 의뢰인 레퍼런스라 유지. 대안 후보(요청 시 토큰만 교체): 무채 모노크롬+레드 포인트. ~~이전: 화이트+네이비/블루~~ — 브라운/골드 UI도 "AI스럽다"고 거부됨. 토큰은 네이비(#1c3d6e)/블루(#2f6fe8)/라이트블루 틴트로 복귀(의뢰인이 보낸 레퍼런스 이미지 3장이 전부 화이트+블루 계열). 파스텔 멀티컬러 섹션(이런경우에도/제도비교/절차 안내 카드)은 유지. **골드(#8a6a34 계열)는 헤더/푸터 로고 텍스트(.lname/.flogo)와 엠블럼·OG 로고에서만 사용 — UI 색으로 재사용 금지.**
- 헤더 로고 겹침 방지: .logo{flex:0 0 auto} 필수. ≤1280px에서 GNB 압축, ≤1080px에서 hdr-tel 숨김.
- **로고 투명화 주의**: 흰배경 로고를 투명화할 때 밝기 비례 알파를 쓰면 골드 중간톤까지 반투명해져 로고가 뿌옇게 깨짐 → **알파는 거의 이진**(밝기 232 이하 완전 불투명, 232~246만 램프)으로 처리할 것. logo.png는 표시폭의 4배(920px)로 저장.
- **로고**: `img/logo.png`(가로형, 흰배경→투명 처리), `img/emblem.png`(기둥 엠블럼). 헤더·푸터에 이미지 로고, 파비콘=흰 라운드+엠블럼. OG도 로고 포함 재생성.
- **브랜드명 "수원개인회생파산 법률사무소 레이"** / 주소 **1002호** / **24시간 상담·주말 예약제**.
- **"무료" 표현 전면 금지(변호사법, 의뢰인 지시)** — 무료상담·상담무료 등 사용 불가. 대체: "전국 비대면 상담", "익명 상담". 전 템플릿·시드에서 제거 완료, 재도입 금지.
- **자가진단 v2 "1분 자격진단"** (site.js initQuiz): 분기형 — Q1 소득 유무로 회생/파산 트랙 분기. 회생 트랙: 실수령액·월상환액 **숫자 입력**(콤마 포맷) → 채무 구간 → 재산 **멀티선택**(자동차/부동산 선택 시 가액 팔로업) → 최근대출(있으면 시기→사용처 팔로업) → 연체 → 부양가족. 결과 = "나의 채무상황 분석" 카드(상환부담 % 계산) + 판정문 + ✓/! 3칸 + "왜 이런 결과가 나왔나요?" 접기 + 순화 문구("자가진단은 여기까지입니다…"). 영업성 문구 금지.
- 메인 개편: 진행방식 4카드(맞춤형 채무진단/합리적인 변제계획/체계적인 사건관리/신속한 상담안내), "한눈에 보기" 삭제→"이런 경우에도" 4카드(연체 전에도/신규채무 확인/재산이 있어도/법적조치 확인), 고민 체크 8문항 교체, 제도비교는 .specs 행형(회생 변제기간 "2년(24개월)까지 가능", 파산 면책 "비면책채권 제외" 명시, 레퍼런스 카피 제거), 비용 4행+"비용만 먼저 결정하지 않습니다", 일하는 방식 01~04.
- 히어로: 키커 "개인회생 상담 · 개인파산 상담 · 채무조정 · 법률상담", 칩(비대면/익명/직접상담/분할), 네임카드 삭제, 버튼 "1분 자격진단"·"전화상담". 변호사 사진 태그·about에서 "제1회 변호사시험" 삭제(스트립 통계엔 유지). about 사무소 정보 표 삭제. FAQ "배우자 재산과 소득은"으로 수정.
- 미해결: 수정요청서의 "키워드별 페이지에 오타" — 위치 미특정, 의뢰인 확인 필요.
- **2차 수정(같은 날)**: 헤더/푸터 로고는 이미지 텍스트 축소가 깨져 보여 **엠블럼 이미지+웹폰트 텍스트 조합(.lname/.flogo)**으로 확정. 히어로 문구 "감당하기 어려워진 채무, 개인회생으로 다시 시작할 수 있습니다"+새 서브카피. "이런 경우에도" 4카드는 **파스텔 4색(.pastel .t1~t4)+하단 인포바(.infobar)**, 제도비교는 탭 폐기→**3열 컬러헤더 카드(.pcmp/.pcol c1~c3, 블루/퍼플/그린+01~03 뱃지+아이콘 rows+파스텔 풋터)**, 진행절차는 메인=**아이콘 타임라인(.tl, 7단계+연결선)** / process 페이지=**8단계 상세 rows(.prows2, 주요 확인사항 박스)+속도 요인+단계별 안내 카드**. 비용은 카드형 리스트(.costcard). 직업별은 지역과 같은 4열 카테고리 그리드(job_groups), 상황별 2카드. 자격진단은 9문항 고정형으로 갔다가 **의뢰인 재지시(9-23)로 분기형이 최종**: Q1 소득 분기(회생/파산 트랙) → 실수령액·월상환액 **숫자 입력**(결과에 상환부담 % 계산) → 채무 구간 → 재산 멀티체크(부동산 선택 시 예상가액+**남은 담보대출**, 자동차 선택 시 차량가치 팔로업) → 최근대출 있다/없다(있으면 시기→사용처) → 연체 → 부양가족. **"← 이전으로" 뒤로가기 필수 유지**(history 스냅샷 방식). 결과: 분석 카드+판정+3칸+"왜?"접기+"자가진단은 여기까지입니다" 문구. 멀티컬러 파스텔은 이 두 섹션(이런경우에도/제도비교)+process 안내 카드에만 허용.

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

### Phase 7 구현 메모 (SEO, 2026-09-24)
- **타겟 키워드: `수원개인회생`, `수원개인회생파산`** (네이버 기준). 메인 타이틀이 두 키워드를 모두 정확 매칭, 서브페이지는 "{페이지 키워드} | 수원개인회생 법률사무소 레이" 패턴으로 전 페이지에 `수원개인회생` 포함. description 앞부분에도 키워드 배치. `site.keywords` 공통 + 페이지별 `{% block meta_keywords %}`.
- **SEO 라우트: `app/routes/seo.py`** — `/robots.txt`(Yeti·Daum 명시 허용, /admin·/inquiry 차단), `/sitemap.xml`(인덱스) + `sitemap-pages|area|job|case|board.xml`, `/rss.xml`(사례 RSS 2.0, content:encoded·enclosure 포함). **한글 URL은 url_for가 주는 퍼센트 인코딩 경로를 그대로 써야 함**(XML 규격).
- **구조화 데이터**: `partials/schema_org.html`의 LegalService(전 페이지, areaServed 수원 4개구), `_breadcrumb.html`에 BreadcrumbList 자동 생성, 동/구/직업/상황은 FAQPage, 사례글은 Article. 페이지당 평균 2.8블록.
- **도메인 확정: `https://suwonlei.com` (non-www), 운영 포트 8038.** config base_url 기본값이며 .env SITE_URL로 덮어쓸 수 있음. 네이버·구글 소유확인 메타값도 config에 기본 반영(공개값).
- SEO 진단 스크립트 결과(77페이지): 타이틀 평균 28.9자(전부 60자 이내), 설명 평균 71.5자, H1 정확히 1개, 타이틀·설명 중복 0, alt 누락 0, canonical 100%.
- 오픈 후 할 일: 네이버 서치어드바이저에 사이트 등록 → 소유확인 → 사이트맵·RSS 제출, 구글 서치콘솔 동일. 사례 글 발행 시 RSS 자동 반영(10분 캐시).

### 중복 콘텐츠 방지 + 롱폼 SEO (2026-09-28)

양산 페이지(동 31·직업 16·상황 8·구 4)가 서로 너무 비슷하면 검색엔진이 양산형으로 판정한다.
**측정 도구가 정답 — 콘텐츠를 건드렸으면 반드시 `python scripts/seo_qa.py`를 돌리고 PASS를 확인할 것.**

| | 개선 전 | 개선 후 |
|---|---|---|
| 동 유사도 | 평균 61% / 최대 90% | 평균 35% / 최대 49% |
| 구 유사도 | 평균 65% / 최대 67% | 평균 30% / 최대 42% |
| 동 본문 | 약 1,300자 | 6,000~8,300자 |
| QA 오류 | 187건 | 0건 |

**① 해시 회전** (`app/content.py`)
- `stable_hash()` = **blake2b**. ~~FNV-1a~~는 쓰지 말 것 — 하위 비트 확산이 약해 `% 4`가 편향된다. 실제로 `lf_sec1/5/9`가 같은 변형을 골라 두 페이지가 10개 섹션을 **전부** 공유하는 버그가 났다(0x31·0x35·0x39가 모두 4로 나눈 나머지 1).
- `get_block(key, seed)` / `pick_faqs(scope, seed, ...)` / `vtext(seed, key, **vars)` — 전부 **엔티티 이름을 시드**로 결정적 선택. 같은 페이지는 항상 같은 결과(멱등).
- `vtext(seed, key, rank=N)` — **페이지 수 ≤ 변형 수**인 유형(구 4개)에서만 rank를 넘긴다. `(hash(key)+rank)%n` 라틴 방진이라 한 섹션도 안 겹친다. 동(31개)처럼 페이지가 더 많으면 rank가 같은 페이지끼리 전부 겹치므로 **절대 넘기지 말 것**.
- FAQ는 회전(offset)이 아니라 **결정적 셔플** — 페이지마다 질문 구성 자체가 달라진다.

**② 문장 풀** (`app/variants.py` = 템플릿 하드코딩 문장, `app/variants_longform.py` = 롱폼 10섹션)
- 템플릿에서 `{{ vtext(seed, 'dong_docs', dong=dong.name) }}` 형태로 호출. Jinja 전역 등록은 `app/__init__.py`.
- 후보끼리 **사실관계가 어긋나면 안 됨**: 변제기간 원칙 3년·최장 5년·사정에 따라 2년까지 단축 / 무담보 10억·담보 15억 이하 / 금지명령 접수 후 1~2주 / 개시결정 평균 3~6개월 / 세금·벌금·양육비 비면책.
- `seed/content_blocks/{rehab_core,after_apply,why_us}_{A~F}.html` 6종씩 → 216가지 조합.

**③ 롱폼 구조** (경쟁사 `proseolb.kr` 벤치마크 — 사용자가 최우선 참고 지정)
- 그쪽 방식: **키워드가 들어간 번호 소제목 10개 + 핵심 확인사항 요약 + 비교표 + FAQ**, 본문을 아주 길게. 루트는 원페이지, 양산 페이지는 kboard(`?uid=N`) 2,200여 건.
- 이식한 파셜: `partials/lf_summary.html`(상단 핵심 요약 박스, AEO/LLM 인용 대상) → `partials/longform.html`(01~10 번호 섹션, 소제목마다 `{{kw}}` 포함) → `partials/lf_table.html`(개인회생·파산·신용회복 비교표).
- 동·구·직업·상황 4종 상세 템플릿에 모두 들어감. 호출 시 `{% with kw = 이름 ~ ' 개인회생' %}`.
- CSS는 site.css의 `.lf-sum` / `.prose.lf` / `.lf-tbl`.

**④ QA 게이트** (`scripts/seo_qa.py`)
- 타이틀 60자·설명 40~160자·H1 1개·canonical·img alt·핵심 키워드·본문 최소 800자 + **3-gram Jaccard 유사도**(SIM_WARN 0.55 / SIM_FAIL 0.70).
- 유사도는 **`<main>` 안쪽에서 `<aside>`를 뺀 본문**으로만 잰다(헤더·푸터·CTA 같은 공통 보일러플레이트는 어느 사이트나 같으므로 중복 판정 대상 아님). 그래서 `base.html`에 `<main id="main">` 래퍼가 있다 — **제거하지 말 것**.
- 비교 전 엔티티 이름을 지운다(이름만 바꾼 복제를 잡기 위함). 기준값: 손으로 따로 쓴 고정 페이지끼리는 3~11%.

### 관리자 화면 리디자인 (2026-09-28)
- **원칙: 행마다 폼을 펼쳐두지 않는다.** 이전 접수 목록은 모든 행에 `select + input + 저장 + 삭제`가
  항상 열려 있어 8건만 있어도 화면이 시끄러웠고, 정작 정의돼 있던 상태 뱃지(`.bd`)는 쓰이지 않아
  한눈에 상태가 안 보였다. 지금은 **읽기 모드(상태 뱃지 + 메모 한 줄)** 가 기본이고 `편집`을 누른
  행만 폼으로 바뀐다(`app/static/js/admin.js`, `data-view`/`data-edit`를 `hidden`으로 토글).
  한 번에 한 행만 열리고 Esc·취소로 닫힌다. **삭제 버튼은 편집 모드 안에만** 둬서 오클릭을 막는다.
- 폼은 처음부터 DOM에 있고 `hidden`만 토글하므로 JS가 죽어도 데이터는 살아 있다.
- 상단 헤더 2줄(`.ahead` + `.anav`)을 **한 줄(`.abar`)로 합쳤다** — 세로 공간만 먹던 구조.
- 행 오른쪽 작업 버튼(`.ract`)은 평소 `opacity:.45`, 행 hover/focus 시 또렷해진다(목록 훑을 땐 조용하게).
- 뱃지와 메모는 **같은 줄**(`.statline`)에 둔다. 세로로 쌓으면 행 높이가 두 배가 된다(실제로 100px까지 갔었음).
- 폰트는 공개 사이트와 동일한 self-host 서브셋. **admin.css에도 CDN `@import`가 남아 있었다 — 다시 넣지 말 것.**
- 모바일(≤600): 로고 글자·`관리자` 태그 숨김, 접수일시 열 숨기고 이름 아래에 날짜(`.only-sm`),
  메모 본문 숨김 — 이렇게 해야 `편집` 버튼이 화면 밖으로 안 밀린다.
- **주의**: `inquiries` 라우트는 `status_label`을 넘겨야 한다(뱃지 라벨용). 대시보드에만 있어서 500이 났었다.
- 어드민 화면 확인은 헤드리스 크롬이 URL 인증정보를 무시하므로, `curl -u admin:admin`으로 HTML을 받아
  `app/static/` 아래 임시로 두고 캡처한 뒤 **반드시 삭제**할 것.

### 크롤링·속도 점검과 수정 (2026-09-28)

크롤러 관점에서 실측한 결과와 고친 것. **재점검 시 같은 항목을 다시 재볼 것.**

**확인된 정상 항목** — 캐러셀은 슬라이드 11개가 원본 HTML에 그대로 있고 `display:none`이 0개라
JS를 못 돌리는 Yeti도 전부 읽는다(scroll-snap 방식이라 가능. JS로 슬라이드를 복제·은닉하는
캐러셀로 바꾸면 이 장점이 사라짐). 내부 링크는 77페이지 전부 홈에서 1클릭, 고아 0개,
동 페이지 평균 피인용 5.8회. 301·404·트레일링 슬래시 308 정상. 타이틀 전부 고유.
메인의 외부 호스트 참조 38건은 전부 SVG `xmlns`와 JSON-LD `@context`라 실제 네트워크 요청 아님.

**① 사이트맵 lastmod를 실제 수정 시각으로** (`app/routes/seo.py`)
- 이전엔 전 URL에 `datetime.now()`를 박아 77개가 매일 바뀐다고 주장 → 검색엔진이 신호를 무시한다.
- `content_mtime()`이 "그 페이지 본문을 만드는 파일들"의 mtime 최대값을 쓴다. 유형별 목록은 `CONTENT_SOURCES`.
- **`base.html`·헤더·푸터는 일부러 제외.** 메타태그 한 줄 고쳤다고 전 페이지 lastmod가 리셋되면
  원래 문제로 되돌아간다. 새 소스를 추가할 땐 "본문 내용을 바꾸는 파일인가"로 판단할 것.

**② canonical을 퍼센트 인코딩으로 통일** (`app/__init__.py`의 `canonical_url`)
- `request.path`는 디코딩된 한글이라 그대로 쓰면 canonical은 원시 한글, 사이트맵은 인코딩으로
  표기가 갈렸다. context_processor에서 `quote(request.path)`로 만들어 주입하고
  base.html·board/view.html·_breadcrumb.html이 모두 `{{ canonical_url }}`을 쓴다.

**③ 폰트 self-host + 한국어 서브셋** (`scripts/build_fonts.py`)
- CDN의 `pretendard.min.css`에는 `unicode-range`가 없어 굵기마다 전체 한글(약 750KB)을 통째로
  받았다. 400·600·700·800 네 굵기 = **첫 방문에 약 3MB**. 게다가 CSS `@import`라 site.css를
  다 받은 뒤에야 폰트 CSS를 발견하는 직렬 체인이었다.
- KS X 1001 상용 2,350자 + 사이트 실사용 글자로 서브셋 → **3.0MB → 722KB (76% 감소)**.
  `app/static/fonts/pretendard-{400,600,700,800}.woff2`, `@font-face`는 site.css 상단.
- **글자를 바꿔 서브셋에 없는 한글이 필요해지면 `python scripts/build_fonts.py`를 다시 돌릴 것.**
  파이썬 `euc-kr` 코덱은 실제로 CP949라 한글 전체를 통과시킨다 → 바이트 영역(선두 0xB0~0xC8)으로 걸러야 2,350자가 나온다.
- 원본 woff2는 저장소에 두지 않는다(스크립트가 CDN에서 받아 서브셋만 남김).

**④ 응답 압축** (`Flask-Compress`)
- HTML 51KB→12KB, site.css 52KB→12KB, site.js 25KB→8KB. br·gzip 모두 동작.
- Flask는 정적 파일을 스트리밍으로 내보내 br만 걸리고 gzip이 빠진다 → `_compressible_static`
  훅이 CSS·JS만 `get_data()`로 읽어 일반 응답으로 바꾼다. **after_request는 등록 역순 실행이라
  이 훅은 반드시 `Compress(app)`보다 뒤에 등록해야 한다.**

**⑤ 이미지** — og.png 407KB → og.jpg 97KB(참조처 4곳 교체, png 삭제). 히어로에 `fetchpriority="high"`,
접힌 화면 아래 이미지에 `loading="lazy"`, 사례 썸네일에 width/height.

**남은 것(코드로 해결 안 되는 것)** — 네이버 "수원개인회생" SERP는 파워링크·플레이스·블로그·카페가
상단을 차지하고 웹사이트 영역은 아래다. 기술 SEO만으로 네이버 유입에는 천장이 있고, 지역 업종은
**네이버 스마트플레이스 등록**이 가장 크다(사이트에서 지도를 뺀 결정과는 별개 건). 그리고 사례 글이
목업뿐이라 신선도 신호가 없다 — RSS·사이트맵 배관은 이미 깔려 있으니 어드민에서 글만 쓰면 된다.

### 캐러셀 (2026-09-28)
- 매크로 `partials/carousel.html` — `{% from "partials/carousel.html" import carousel %}` 후 `{% call carousel('id', label='…', per=3, autoplay=6500) %}<div class="carou-item">…{% endcall %}`.
- **scroll-snap이 실제 이동을 담당하고 JS(site.js 하단)는 화살표·점·자동재생만** 붙인다 → JS가 죽어도 스와이프로 볼 수 있고, 슬라이드는 복제·숨김 없이 전부 DOM에 남아 SEO 영향 없음.
- 자동재생은 호버·포커스·탭 비활성·`prefers-reduced-motion`에서 멈추고, 사용자가 한 번이라도 조작하면 완전 중단.
- 현재 사용처: 메인 "상황별 안내"(per=4, 자동재생 없음), 메인 "진행 사례"(per=3, 6.5초). 카드 CSS는 `.scard` / `.ccard`.
- 모바일(≤960)은 한 장 82% + 다음 장 살짝 보임, 화살표 숨김·점만 표시.

### 확정 사항 (2026-09-14)
- **상담 전화 1644-6755로 통일** (SITE_DEFAULTS phone/phone_link). **카카오톡 상담은 전면 제거** — 버튼·링크·문구·seed 데이터 모두 삭제, kakao_url 키도 없음. 다시 넣지 말 것.
- **오시는 길/지도 전면 제거** — 메인 오시는길 섹션·contact 지도 삭제, /contact/는 "상담 신청" 페이지(GNB 라벨도 변경). 주소는 푸터·소개·상담신청 표에만 텍스트로.
- **상담 폼은 메인 맨 하단** (#consult 섹션, .quick.bottom) — 히어로의 #form 앵커도 여기로 스크롤.
- **변호사 프로필 리디자인**: 골드 제거(사이트에서 골드 전면 퇴출) — 사진 위 네이비 반투명 네임태그(.lawyer-photo .tag), 약력 2열 리스트, 경력/주요활동 카드는 회색 헤더+파란 바(.bio-card h3::before).

### 미결 사항
- **이메일** → `app/config.py` SITE_DEFAULTS의 info@example.com 교체 (푸터·개인정보처리방침 노출)
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
