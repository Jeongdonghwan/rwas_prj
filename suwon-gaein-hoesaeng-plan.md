# 수원개인회생 사이트 — 개발계획 · 디자인계획

작성일: 2026-09-09
목적: 법률상담.net 구조·내용을 토대로 "수원개인회생 + {업체명}" 사이트 제작. jd8.co.kr/homepage/ 의 허브→카테고리→상세 구조를 그대로 가져와 수원 지역(구·동) 페이지와 직업(업종)별 페이지를 대량 생성한다.
이관: 이 문서 → CLAUDE.md + HTML 프로토타입 → 클로드코드 Phase 단위 실행.

> 원본 사이트(법률상담.net)는 robots 차단으로 자동 수집이 안 됨. 아래 "메인 페이지 섹션"은 개인회생 사무소 사이트의 표준 구조로 잡아둔 것. 원본 페이지 텍스트를 따로 붙여주면 그 순서·문구에 맞춰 1:1로 치환.

---

## 1. 사이트 개요

| 항목 | 내용 |
|---|---|
| 사이트명 | 수원개인회생 {업체명} (예: 수원개인회생 법무법인 OO) |
| 도메인 | 미정 (한글도메인 병행 가능 — 수원개인회생.kr 등) |
| 타깃 키워드 | 수원개인회생, 수원 개인회생 비용, 수원 개인회생 변호사/법무사, {구}개인회생, {동} 개인회생, {직업} 개인회생 |
| 전환 목표 | 전화 / 카톡 / 상담신청 폼 (3개 CTA를 전 페이지 고정) |
| 총 페이지 수 (초기) | 메인 1 + 고정 페이지 ~10 + 구 4 + 동 ~30 + 직업 ~16 + 상황별 ~8 + 블로그·사례 N = 약 70 + 게시글 |

### 1-1. 반드시 지킬 규정
- 변호사(법무사)광고규정: "100% 인가", "무조건 면책", "최저가 보장", 타 사무소 비교 금지. 사례는 사실 위주·결과 보장 인상 금지.
- "전문" 표기는 전문분야 등록 없이 불가 → "개인회생 사건을 다룹니다", "회생·파산 업무" 식으로.
- 광고책임변호사(또는 법무사) 성명·사무소 주소·사업자번호를 푸터에 표기.
- 지역 페이지가 "지점이 있는 것처럼" 오인되지 않게: "OO동에서 오시는 길", "OO동 거주자 상담 안내"로 표현. 실제 사무소 주소는 한 곳만.

---

## 2. URL 구조 (jd8 /homepage/ 구조 이식)

```
/                                 메인 (수원개인회생 {업체명})
/about/                           사무소 소개 · 인사말 · 구성원
/service/rehab/                   개인회생
/service/bankruptcy/              개인파산
/service/docs/                    준비서류
/service/cost/                    비용 안내
/process/                         진행 절차 (수원지방법원 기준)
/cases/                           진행 사례 (게시판, 썸네일 리스트)
/cases/{slug}/                    사례 상세
/faq/                             자주 묻는 질문
/blog/                            블로그 (칼럼, 썸네일 리스트)
/blog/category/{cat}/             블로그 카테고리 (개인회생 / 개인파산 / 비용 / 법원소식 / 수원소식)
/blog/{slug}/                     블로그 글 상세
/blog/page/{n}/                   페이지네이션
/contact/                         상담신청 · 오시는 길

/area/                            ★ 허브: 수원 지역별 개인회생 (jd8 /homepage/ 대응)
/area/jangan/                     ★ 카테고리: 장안구 (jd8 /homepage/category/xxx/ 대응)
/area/jangan/jeongja/             ★ 상세: 정자동 (jd8 /homepage/xxx/ 대응)
/area/gwonseon/ ... /area/paldal/ ... /area/yeongtong/ ...

/job/                             ★ 허브: 직업별 개인회생
/job/self-employed/               ★ 상세: 자영업자 개인회생
/job/freelancer/ ...

/case-type/                       ★ 허브: 상황별 개인회생 (선택)
/case-type/gambling-debt/ ...

/sitemap.xml  /sitemap-{pages|area|job|blog|cases}.xml  /robots.txt  /rss.xml  /feed/cases.xml
```

- 슬러그는 전부 영문 소문자·하이픈. 한글 URL 금지(네이버 색인 안정성).
- 트레일링 슬래시 통일. `www` → non-www 301.

---

## 3. 페이지별 구성

### 3-1. 메인 (/)
원본(법률상담.net) 섹션 순서를 기준으로 하되, 확인 전까지 표준 구조:

1. **헤더**: 로고(텍스트형 "수원개인회생 {업체명}") · GNB · 우측 전화번호(대형) · 상담신청 버튼
2. **히어로**: 실사진(사무소 외관/상담실 실사 or 수원지방법원 인근 실사) 풀폭 + 1줄 헤드라인(명조) + 서브카피 + 상담폼(이름/연락처/채무액/지역 셀렉트) 우측 배치
3. **한눈에 보는 개인회생**: 자격 요건 / 변제기간 / 탕감 범위 / 소요 기간 — 4단 표(카드 아님)
4. **이런 분께 필요합니다**: 체크리스트 형태 8줄
5. **진행 절차**: 상담 → 서류 → 신청 → 금지명령 → 개시결정 → 변제계획 인가 → 면책. 숫자+선 형태의 단순 타임라인(아이콘 없음)
6. **비용 안내**: 표 1개 (착수금/성공보수/법원 예납금 항목). 금액은 "상담 시 안내" 처리 가능
7. **수원 지역별 안내** (허브 진입): 4개 구 → 동 링크 그리드 (jd8 업종 리스트와 동일한 텍스트 링크 나열)
8. **직업별 안내** (허브 진입): 직업 텍스트 링크 나열
9. **진행 사례** 최신 4건 (게시판 리스트형)
10. **자주 묻는 질문** 6개 (아코디언 없이 Q/A 그대로 노출 — 크롤링용)
11. **오시는 길**: 네이버 지도 임베드 + 주소 + 수원지방법원/수원역에서 오는 법
12. **푸터**: 사무소명·대표·광고책임자·사업자번호·주소·전화·개인정보처리방침·이메일무단수집거부
13. **모바일 하단 고정바**: 전화 / 카톡 / 상담신청 3분할 (PC는 우측 하단 플로팅 2버튼)

### 3-2. 지역 허브 (/area/)  ← jd8 /homepage/ 복제
- 브레드크럼: 홈 › 수원 지역별 개인회생
- 상단 라벨 "AREA GUIDE" + H1 "수원 지역별 개인회생 안내" + 리드문단 3~4줄
- 구 4개를 H2 섹션으로, 각 섹션 아래 동 링크를 인라인 텍스트 링크로 나열 (jd8와 동일)
- 하단: "우리 동네가 없나요?" → 상담 CTA

### 3-3. 구 페이지 (/area/{gu}/)  ← jd8 /homepage/category/xxx/ 복제
- H1 "{구} 개인회생 안내"
- 구 개요 2~3문단(수원지방법원 관할, 구 특성—예: 권선구는 자영업·물류, 영통구는 직장인 비중 등)
- 해당 구 동 링크 그리드
- 해당 구 관련 사례/칼럼 3건
- FAQ 3개 (구 단위 질문: "{구}에서 신청하면 어느 법원?")
- CTA

### 3-4. 동 페이지 (/area/{gu}/{dong}/)  ← jd8 /homepage/xxx/ 복제 (핵심 대량 페이지)
jd8 상세 페이지 섹션을 그대로 치환:

| jd8 섹션 | 동 페이지 대응 |
|---|---|
| 브레드크럼 | 홈 › 수원 지역별 › {구} › {동} |
| 카테고리 라벨 + H1 | "{구}" / **"{동} 개인회생 안내"** |
| 리드 문단 | {동} 거주·근무자 대상 1~2문장 + 사무소까지 거리·소요시간 |
| "사장님들이 겪는 고민" | **"{동}에서 상담 오시는 분들이 자주 묻는 것"** 4줄 |
| "필수 기능" (H3 5개) | **"{동} 거주자 개인회생 체크 포인트"** H3 5개 (관할법원 / 오시는 길 / 준비서류 / 예상 기간 / 비용) |
| "디자인 포인트" | **"{동} 상권·주거 특성과 개인회생"** 3~4줄 (아파트 밀집/원룸/상가 등 → 채무 유형 연결) |
| "관련 제작 사례" | 진행 사례 2~3건 (동 무관, 랜덤/최신) |
| 장문 H2 3~4개 | ① {동}에서 사무소까지 오시는 길(교통·주차) ② 개인회생 핵심 설명(공통 본문 + 지역 변수) ③ 신청 후 흐름 ④ {업체명}이 다르게 하는 점 |
| FAQ 5개 | 동 변수 삽입된 FAQ 5개 (Schema FAQPage) |
| "함께 보면 좋은 페이지" | 인접 동 3개 + 같은 구 페이지 |
| 최종 CTA | 상담신청 / 전화 / 카톡 |

**중복 콘텐츠 방지**: 동 45개 × 같은 본문이면 네이버 저품질. 본문 블록을 A/B/C 3~4개 변형으로 두고 동별로 조합 + 동 고유 변수(교통편·특성·인접동) 삽입. 필요 시 Claude API로 동별 "특성 문단"만 별도 생성.

### 3-5. 직업 허브 (/job/) & 직업 페이지 (/job/{slug}/)
동 페이지와 동일 템플릿, 변수만 "직업"으로:
- H1 "{직업} 개인회생 안내"
- 고민 4줄 → 체크포인트 5개(소득 증빙 방법 / 변제금 산정 / 영업·근무 계속 여부 / 자격 제한 여부 / 준비서류) → 장문 → FAQ → 관련 직업 → CTA
- 직업별 핵심 차별 변수: **소득 증빙 방식**(급여명세/사업소득/3.3%/현금소득), **직업 유지 가능 여부**(공무원·군인·금융권 결격 여부), **변제금 산정 기준**

### 3-6. 상황별 (/case-type/) — 선택
도박빚 / 사업실패 / 카드·현금서비스 / 대출 돌려막기 / 보증채무 / 코인·주식 손실 / 이혼 후 채무 / 의료비 채무

---

## 4. 데이터 정의 (MariaDB)

```sql
-- 지역
gu       (id, slug, name, intro_html, court_note, sort)
dong     (id, gu_id, slug, name, name_legal, transit_note, feature_note, adjacent_ids JSON, variant_set CHAR(1), sort)
-- 직업
job      (id, slug, name, category, income_proof_note, job_keep_note, repay_note, variant_set, sort)
-- 상황별
case_type(id, slug, name, intro, variant_set, sort)
-- 공통 콘텐츠 블록 (A/B/C 변형)
content_block (id, block_key, variant CHAR(1), body_html)   -- block_key: rehab_core, after_apply, why_us ...
-- FAQ 풀
faq      (id, scope ENUM('common','dong','gu','job','case'), question_tpl, answer_tpl, sort)
-- 게시판
post     (id, board ENUM('case','blog','notice'), slug UNIQUE, title, subtitle, body_html, excerpt,
          thumb_path, thumb_alt, category_id, tags JSON, meta_title, meta_desc, canonical,
          author, view_count, is_public, published_at, created_at, updated_at)
post_category (id, board, slug, name, sort)
post_image (id, post_id, path, alt, sort)              -- 본문 업로드 이미지
-- 상담 접수
inquiry  (id, name, phone, debt_range, area_text, source_path, utm JSON, memo, created_at, status)
-- 사이트 설정
site_config (key, value)   -- firm_name, phone, kakao_url, address, ad_lawyer, biz_no, map_embed ...
```

- 템플릿 변수 `{동}`, `{구}`, `{직업}`, `{업체명}` 은 Jinja2 렌더링 시 치환 (`question_tpl` 에 `{{dong}}` 형식으로 저장).
- 초기 데이터는 `seed/dong.csv`, `seed/job.csv`, `seed/faq.csv` 로 관리 → `flask seed` 커맨드로 적재.

### 4-1. 수원 동 리스트 (초기 시드 — 행정동 기준, 최종 확인 필요)
- **장안구**: 파장동, 정자1동, 정자2동, 정자3동, 영화동, 송죽동, 조원1동, 조원2동, 연무동, 율천동
- **권선구**: 세류1동, 세류2동, 세류3동, 평동, 서둔동, 구운동, 금곡동, 호매실동, 권선1동, 권선2동, 곡선동, 입북동
- **팔달구**: 매교동, 매산동, 고등동, 화서1동, 화서2동, 지동, 우만1동, 우만2동, 인계동, 행궁동
- **영통구**: 매탄1동, 매탄2동, 매탄3동, 매탄4동, 원천동, 이의동, 광교1동, 광교2동, 영통1동, 영통2동, 영통3동, 망포1동, 망포2동, 태장동

URL·검색 키워드용으로는 1동/2동을 합쳐 법정동 단위(정자동, 매탄동, 영통동…)로 1페이지씩 만드는 것을 권장 → 약 30개. 검색량이 확인되는 동만 분리.

### 4-2. 직업 리스트 (초기 16)
직장인 / 자영업자·소상공인 / 프리랜서(3.3%) / 공무원·교사 / 군인 / 간호사·의료종사자 / 택시·버스·화물 기사 / 배달라이더·플랫폼노동 / 건설일용직 / 주부 / 무직·구직자 / 학생·청년(20대) / 60대 이상 은퇴자 / 법인 대표·임원 / 금융권 종사자 / 유흥·서비스업 종사자

---

## 5. 기술 스택 · 아키텍처

| 구분 | 선택 |
|---|---|
| 백엔드 | Flask + Jinja2 SSR (Python 3.11) |
| DB | MariaDB (Cafe24 가상서버) |
| 프론트 | 순수 HTML/CSS + 최소 JS (프레임워크 없음, 빌드 없음) |
| 폰트 | 제목: Noto Serif KR / 본문: Pretendard (self-host, woff2) |
| 지도 | 네이버 지도 iframe 임베드 |
| 폼 | 서버 POST → DB 저장 + 카톡/메일 알림(선택) |
| 관리자 | Flask-Admin 또는 최소 자체 어드민 (/admin, 게시판·접수·설정만) |
| 배포 | gunicorn + nginx, Cafe24 |
| SEO | sitemap.xml 자동생성, robots.txt, canonical, OG, JSON-LD |

### 5-1. 디렉토리
```
app/
  __init__.py  config.py  models.py  seed.py
  routes/  main.py  area.py  job.py  board.py  contact.py  admin.py  seo.py
  templates/
    base.html  _header.html  _footer.html  _cta.html  _mobile_bar.html  _breadcrumb.html
    index.html  about.html  service/*.html  process.html  faq.html  contact.html
    area/hub.html  area/gu.html  area/dong.html
    job/hub.html   job/detail.html
    board/list.html  board/view.html
    partials/  block.html  faq_list.html  related_links.html
  static/  css/site.css  js/site.js  fonts/  img/
seed/  dong.csv  job.csv  faq.csv  content_blocks/*.html
```

### 5-2. 라우팅 규칙
- `/area/<gu>/<dong>/` → dong 조회, 없으면 404. variant_set에 따라 content_block 선택.
- 모든 상세 페이지는 `page_ctx` 딕셔너리(title, h1, meta_desc, breadcrumb, faq, related, cta_source)를 만들어 공통 템플릿에 주입.
- `source_path` 를 상담폼 hidden으로 넘겨 어느 동/직업 페이지에서 접수됐는지 추적.

### 5-3. SEO 세부
- `<title>`: `{동} 개인회생 | 수원개인회생 {업체명}` / 직업: `{직업} 개인회생 | 수원개인회생 {업체명}`
- meta description 동/직업별 템플릿 (변수 삽입, 80자 내).
- JSON-LD: `LegalService`(사무소, 주소, 전화, areaServed: 수원시 4개 구), `BreadcrumbList`, `FAQPage`(상세 페이지).
- 네이버 서치어드바이저 / 구글 서치콘솔 메타 태그 자리 확보 (`site_config`).
- 내부링크: 메인→허브→구→동 + 동↔인접동 + 동→직업 3개 크로스링크. 고아 페이지 0.
- 이미지 alt 전부 지정, lazy loading.

---

## 6. 디자인 계획

### 6-1. 방향
- "AI스럽지 않게": 아이콘·그라데이션·둥근 카드·스크롤 애니메이션 **전부 배제**.
- 국내 법무법인·법무사 사무소 사이트 문법 그대로: 인사말, 구성원, 게시판, 오시는 길, 하단 사업자정보.
- 실사진 크게(사무소·상담실·인물·수원지방법원 주변). 스톡 이미지 최소화, 쓰더라도 한국 배경.
- 정보 밀도 높게, 여백은 넉넉히. 표와 목록이 주 표현 수단.

### 6-2. 타이포
| 용도 | 폰트 | 크기(PC/모바일) | 굵기 |
|---|---|---|---|
| H1 | Noto Serif KR | 36/26px | 600 |
| H2 | Noto Serif KR | 26/20px | 600 |
| H3 | Pretendard | 18/16px | 700 |
| 본문 | Pretendard | 16/15px, 행간 1.8 | 400 |
| 라벨(영문 소제) | Pretendard | 12px, 자간 0.15em, 대문자 | 600 |
| 전화번호 | Pretendard | 22/18px | 800 |

### 6-3. 컬러
```
--ink:        #1a1a1a   본문
--ink-2:      #555555   보조 텍스트
--line:       #d9d9d9   구분선
--paper:      #ffffff   배경
--paper-2:    #f5f4f1   섹션 교차 배경 (따뜻한 회백)
--navy:       #14213d   헤더·H1·버튼 기본
--accent:     #8b1e1e   전화·강조 (짙은 적색, 1곳에만)
```
- 색은 3색 이내로 절제. 그라데이션 없음. 버튼은 각진 사각형(border-radius 0) 또는 2px.

### 6-4. 레이아웃 규칙
- 컨테이너 1080px, 좌우 패딩 20px. 그리드 12컬럼.
- 섹션 상하 여백 80px(PC) / 48px(모바일).
- 카드 대신 **선으로 구분된 표/리스트**. 링크 나열은 jd8와 같이 인라인 텍스트 + 구분점.
- 히어로: 사진 좌 60% + 상담폼 우 40% (모바일은 사진 → 헤드라인 → 폼 순 세로).
- 버튼: navy 채움 + 흰 글씨(기본), 흰 배경 + navy 테두리(보조), accent 채움(전화). hover는 명도만 살짝.
- 모바일 하단 고정바 높이 56px, 3분할 등폭.

### 6-5. 컴포넌트 목록 (프로토타입에 전부 포함)
헤더 / GNB(모바일 햄버거→풀스크린 목록) / 브레드크럼 / 라벨+H1+리드 / 표(2열, 4열) / 체크리스트 / 번호 타임라인 / 인라인 링크 나열 / 게시판 리스트(날짜·제목) / Q&A 블록 / 상담폼 / 지도 박스 / 푸터 / 하단 고정바 / 플로팅 버튼(PC)

---

## 7. 블로그·게시판 (썸네일 + 글쓰기)

### 7-1. 프론트 (/blog/, /cases/)
- 리스트: 썸네일(16:10, 480×300 webp) + 카테고리 + 제목 + 요약 2줄 + 날짜. 2열 그리드(PC) / 1열(모바일). 카드 테두리 없이 썸네일과 텍스트만, 항목 사이 1px 선.
- 상세: 브레드크럼 › H1 › 작성일·카테고리 › 대표 이미지(1200×750) › 본문 › 태그 › 이전/다음 글 › 같은 카테고리 3건 › CTA. 우측 sticky 사이드(상담 버튼 + 최신글 5).
- 본문 이미지 lazy, width/height 명시. 외부 링크 rel="noopener".
- 메인·구·동·직업 페이지에 "관련 글 3건" 자동 노출 (태그 매칭 → 없으면 최신).

### 7-2. 어드민 글쓰기 (/admin/posts)
- 목록: 게시판 탭(블로그/사례/공지), 공개 여부, 검색.
- 에디터: Toast UI Editor(마크다운+WYSIWYG, 국산, 오픈소스) → HTML 저장. 이미지 드래그 업로드 → `/static/uploads/YYYY/MM/` 저장 + webp 변환(Pillow) + post_image 기록.
- 입력 필드: 제목 / 부제 / 슬러그(자동 생성, 수정 가능, 영문·숫자·하이픈) / 카테고리 / 태그 / 썸네일 업로드(자동 480×300 · 1200×750 두 벌 생성) / 썸네일 alt / 요약(비우면 본문 앞 120자) / meta title(비우면 제목) / meta description / 공개 여부 / 발행일(예약 발행).
- 저장 시: slug 중복 검사, HTML sanitize(bleach), 요약 자동 생성, 사이트맵·RSS 캐시 무효화.
- 미리보기 버튼(비공개 상태에서 토큰 URL로 확인).
- 임시저장 자동(30초 localStorage).

### 7-3. Claude API 초안 생성 (선택, Phase 8)
- 어드민에서 "초안 생성": 주제 + 카테고리 입력 → Claude API로 제목 3안·본문 초안·meta description 생성 → 에디터에 삽입 → 사람이 수정 후 발행. 광고규정 금지 표현(보장/100%/최저가/전문) 필터를 후처리로 체크.

---

## 8. SEO 파일 (sitemap · robots · RSS)

### 8-1. sitemap
- `/sitemap.xml` = sitemap index → `/sitemap-pages.xml`(고정 페이지), `/sitemap-area.xml`(허브·구·동), `/sitemap-job.xml`, `/sitemap-blog.xml`, `/sitemap-cases.xml`.
- DB에서 실시간 생성 + 10분 캐시. 글 발행/수정 시 캐시 삭제.
- 각 URL: `<loc>` 절대경로(https, non-www, 트레일링 슬래시), `<lastmod>`(post.updated_at / 고정 페이지는 배포일), `<changefreq>`, `<priority>`(메인 1.0, 허브 0.9, 구·직업 0.8, 동·글 0.7, 기타 0.5).
- 블로그 사이트맵에 `<image:image>` 확장으로 썸네일 포함.
- 비공개·예약 미발행 글 제외. 404·리다이렉트 URL 포함 금지.
- 네이버 서치어드바이저·구글 서치콘솔에 sitemap.xml 제출 (Phase 9).

### 8-2. robots.txt
```
User-agent: *
Allow: /
Disallow: /admin/
Disallow: /static/uploads/tmp/
Disallow: /preview/
Disallow: /*?utm_
Disallow: /*?page=

User-agent: Yeti
Allow: /

Sitemap: https://{도메인}/sitemap.xml
Sitemap: https://{도메인}/rss.xml
```
- Yeti(네이버) 명시 허용. 어드민·미리보기·파라미터 URL 차단. 페이지네이션은 `/blog/page/2/` 경로형이므로 색인 허용, `?page=`만 차단.

### 8-3. RSS
- `/rss.xml`: 블로그 최신 30건, RSS 2.0. `<title>`, `<link>`, `<guid isPermaLink="true">`, `<pubDate>`(RFC 822, KST), `<description>`(요약, CDATA), `<content:encoded>`(본문 전체 HTML, 이미지 절대경로), `<enclosure>`(썸네일), `<category>`.
- `/feed/cases.xml`: 진행 사례 피드 (동일 포맷).
- `<head>`에 `<link rel="alternate" type="application/rss+xml">` 삽입.
- 네이버 서치어드바이저 "RSS 제출"에 등록. 네이버는 RSS 기반 수집이 강하므로 블로그 발행 즉시 반영되도록 캐시 무효화.

### 8-4. 페이지 공통 SEO 체크리스트
- `<title>` 60자 내, `<meta description>` 80자 내, `<link rel="canonical">`, OG(title/description/image 1200×630/url/type), `<meta name="robots" content="index,follow">`.
- JSON-LD: 전 페이지 `LegalService` + `BreadcrumbList`, 상세 `FAQPage`, 블로그 `Article`(headline, image, datePublished, dateModified, author, publisher).
- H1 페이지당 1개. 이미지 alt 필수(어드민 저장 시 빈 alt 경고).
- 네이버 서치어드바이저·구글 서치콘솔·네이버 애널리틱스·GA4 코드는 site_config에서 관리해 base.html에 주입.
- 응답 시간 목표 200ms 내(SSR + 템플릿 캐시), 이미지 webp, gzip.

---

## 9. 개발 Phase (클로드코드 1단계씩)

| Phase | 내용 | 산출물 |
|---|---|---|
| 0 | 프로젝트 골격, config, DB 연결, base.html, site.css 토큰, 폰트 | 빈 페이지 렌더 |
| 1 | 메인 + 고정 페이지 10개 (하드코딩 콘텐츠) | 정적 사이트 완성 |
| 2 | 상담폼 POST + inquiry 저장 + 어드민 접수 목록 | 전환 동작 |
| 3 | DB 모델 + seed 커맨드 (gu/dong/job/faq/content_block) | 데이터 적재 |
| 4 | /area/ 허브·구·동 페이지 템플릿 + variant 로직 | 지역 페이지 대량 생성 |
| 5 | /job/ 허브·상세 (+ /case-type/) | 직업 페이지 |
| 6 | 블로그·사례 게시판: 리스트(썸네일)·상세·카테고리·페이지네이션 + 어드민 글쓰기(Toast UI, 이미지 업로드·webp·썸네일 자동) | 블로그 |
| 7 | sitemap index·robots.txt·RSS·canonical·JSON-LD·OG, 캐시 무효화, 성능 | SEO 마감 |
| 8 | 동별 특성 문단 + 블로그 초안 Claude API 생성 (선택) | 콘텐츠 차별화 |
| 9 | Cafe24 배포, nginx, SSL, 서치어드바이저·서치콘솔 등록 | 오픈 |

### 9-1. 다음 단계 (이 문서 확정 후)
1. 업체명·전화·주소·광고책임자 확정 → site_config
2. 법률상담.net 원문 텍스트 전달 → 메인/고정 페이지 문구 1:1 치환
3. 동 리스트 최종 확정(법정동 통합 여부)
4. ~~프로토타입 3장~~ 완료 (suwon-proto/) → 블로그 리스트·상세 프로토타입 2장 추가 후 CLAUDE.md 작성
5. Phase 0 착수
