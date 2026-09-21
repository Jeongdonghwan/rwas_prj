import os
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


# 사이트 기본값 (사업자등록증 기준). 이메일·도메인은 확정 시 교체.
SITE_DEFAULTS = {
    "firm_name": "법률사무소 레이",
    "brand": "수원개인회생파산 법률사무소 레이",
    "brand_en": "LEI LAW OFFICE",
    "phone": "1644-6755",
    "phone_link": "16446755",
    "address": "경기도 수원시 영통구 광교중앙로248번길 7-2, D동 10층 1002호(하동, 원희캐슬광교)",
    "address_short": "수원시 영통구 광교중앙로248번길 7-2, 원희캐슬광교 D동 10층 1002호",
    "ceo": "이재열",
    "ad_lawyer": "이재열",
    "biz_no": "333-41-00086",
    "since": "2016",  # 개업 2016년 3월 15일
    "email": "info@example.com",  # TODO: 실제 이메일
    "hours": "24시간 상담, 주말 예약제",
    "map_embed": "",
    "base_url": "https://example.com",  # 도메인 확정 후 교체 (non-www, https)
    "naver_site_verification": "",
    "google_site_verification": "",
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
