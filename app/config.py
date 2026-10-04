import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-secret")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL") or (
        "sqlite:///" + str(BASE_DIR / "instance" / "dev.db")
    )
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}
    JSON_AS_ASCII = False

    # 어드민 세션 쿠키. Secure는 https에서만 켠다 — 로컬 http 개발에서 켜면
    # 브라우저가 쿠키를 저장하지 않아 로그인이 무한 반복된다.
    SESSION_COOKIE_NAME = "lei_adm"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "") not in (
        "",
        "0",
        "false",
        "False",
    )
    # "로그인 상태 유지"를 켠 세션의 수명
    PERMANENT_SESSION_LIFETIME = timedelta(days=14)


# ── 지역 설정 ───────────────────────────────────────────────────────
# **다른 지역 사이트를 만들 때 바꾸는 곳은 여기와 seed/gu.csv·dong.csv뿐이다.**
# 안산·용인·성남·도산 프로젝트는 이 저장소를 복사한 뒤 이 블록만 교체한다.
# 전체 계획은 multi-site-plan.md.
REGION = {
    # 지역명 — 브랜드·타이틀·키워드·본문 전반에 들어간다
    "name": "수원",
    # 행정 단위를 붙인 형태 (schema.org areaServed, "OO시 거주자" 문장)
    "name_full": "수원시",
    # 인근 지역 안내 문구 — "OO 인근(…)도 같은 법원 관할" 식으로 쓴다
    "nearby": "화성·용인·오산·의왕 등 경기 남부",
    # schema.org areaServed 목록
    "area_served": ["수원시 장안구", "수원시 권선구", "수원시 팔달구", "수원시 영통구"],
    # "OO 등 경기 남부에 주소지가 있으면" 식의 본문 문구
    "area_served_text": "수원·용인·화성 등 경기 남부",

    "brand": "수원개인회생파산 법률사무소 레이",
    # 서브페이지 타이틀 접미사. 60자 상한이 있어 brand보다 짧게 유지할 것
    "brand_seo": "수원개인회생 법률사무소 레이",
    "keywords": (
        "수원개인회생, 수원개인회생파산, 수원 개인회생, 수원 개인파산, "
        "수원개인회생 변호사, 수원회생법원, 개인회생 신청자격, 개인회생 비용, "
        "채무조정, 법률사무소 레이"
    ),
    "base_url": "https://suwonlei.com",

    # 관할 법원 표기 방식
    #   "named"   — 법원 이름을 그대로 쓴다. 사무소가 법원 인근이라는 문장도 쓴다.
    #               수원·안산·용인·성남은 전부 수원회생법원 관할이고 광교 사무소가
    #               실제로 그 법원 근처라 네 사이트 모두 이 모드다.
    #   "generic" — 법원명 없이 "주소지 관할 법원"으로 쓰고, **법원 인근이라는
    #               문장은 아예 뺀다.** 전국 단위(도산레이)용 — 광교 사무소는
    #               서울·부산 법원 근처가 아니라서 그 문장이 허위가 된다.
    "court_mode": "named",
    "court": "수원회생법원",

    # 지역 축 — "gu_dong"은 구→동 2단, "sido"는 전국 17개 시도 1단(도산레이)
    "area_mode": "gu_dong",

    # 키워드 지역 접두사. 문자열 하나면 단일 지역, 리스트면 시도별로 다 만든다.
    "kw_prefix": "수원",

    # 사이트 구분자 — multi-site-plan.md §3.
    # 같은 키워드라도 사이트마다 다른 섹션 조합·FAQ·문장이 나오게 하는 값이다.
    # **수원은 0/"" 고정** — 이미 색인된 사이트라 출력이 바뀌면 안 된다.
    "site_salt": "",
    "site_offset": 0,
}

# 사이트 기본값 (사업자등록증 기준). 이메일·도메인은 확정 시 교체.
# 주소·전화·사업자번호는 **모든 지역 사이트가 공유한다**(사무소는 광교 한 곳).
SITE_DEFAULTS = {
    "firm_name": "법률사무소 레이",
    "brand": REGION["brand"],
    "brand_en": "LEI LAW OFFICE",
    "phone": "1644-6755",
    "phone_link": "16446755",
    "address": "경기도 수원시 영통구 광교중앙로248번길 7-2, D동 10층 1002호(하동, 원희캐슬광교)",
    "address_short": "수원시 영통구 광교중앙로248번길 7-2, 원희캐슬광교 D동 10층 1002호",
    "ceo": "이재열",
    "ad_lawyer": "이재열",
    "biz_no": "333-41-00086",
    "since": "2016",  # 개업 2016년 3월 15일
    "email": "pasubyeong@naver.com",
    "hours": "24시간 상담, 주말 예약제",
    "map_embed": "",
    # 도메인 (non-www, https). .env의 SITE_URL로 덮어쓸 수 있음
    "base_url": os.environ.get("SITE_URL", REGION["base_url"]).rstrip("/"),
    # 검색엔진 소유확인 메타값 (공개값이라 기본값으로 둠)
    "naver_site_verification": os.environ.get(
        "NAVER_SITE_VERIFICATION", "fc590fc0d8e14f3f16b0104f7193ebdf22d7554a"
    ),
    "google_site_verification": os.environ.get(
        "GOOGLE_SITE_VERIFICATION", "WFdQhnriDQxtjgd2f72pkYIKvwzARsIzBX05OQKucgM"
    ),
    # 검색 노출용 짧은 브랜드 (서브페이지 타이틀 접미사)
    "brand_seo": REGION["brand_seo"],
    # 전 페이지 공통 키워드 (페이지별 키워드는 meta_keywords 블록으로 추가)
    "keywords": REGION["keywords"],
    # 템플릿에서 지역명을 쓸 때 — 하드코딩 대신 {{ site.region }}
    "region": REGION["name"],
    "region_full": REGION["name_full"],
    "nearby": REGION["nearby"],
    "area_served": REGION["area_served"],
    "area_served_text": REGION["area_served_text"],
    # 관할 법원 — 지역에 따라 달라진다
    "court": REGION["court"],
    "court_mode": REGION["court_mode"],
    # ── 사무소 위치 — 지역 사이트가 몇 개든 사무소는 광교 한 곳이다 ──
    # site.court(관할 법원)와 섞지 말 것. 안산·용인·성남은 둘이 같은 값이지만,
    # 전국 사이트(도산레이)는 관할이 "주소지 관할 법원"이어도 사무소는 여전히
    # 수원회생법원 앞이다. "OO 앞"은 사무소 설명이므로 아래 값을 쓴다.
    "office_city": "수원",
    "office_court": "수원회생법원",
}

# 대표변호사 약력 (about·메인 소개 섹션에서 사용)
LAWYER = {
    "name": "이재열",
    "name_en": "Lee Jae Yeol",
    "photo": "img/lawyer-900.webp",
    "photo_card": "img/lawyer-card.webp",
    "edu": [
        "서울대학교 정치학과 졸업",
        "서울대학교 행정대학원 수료",
        "부산대학교 법학전문대학원 졸업",
        "제1회 변호사시험 합격",
    ],
    "career": [
        "前 법률사무소 나루 변호사",
        "前 법률사무소 태우 변호사",
        "現 법률사무소 레이 대표변호사",
    ],
    "activity": [
        "(주)마트투 자문변호사",
        "(주)하나텍 자문변호사",
        "(주)지전건설 자문변호사",
        "(주)쏘하우징 자문변호사",
        "(주)인유어즈 자문변호사",
    ],
}
