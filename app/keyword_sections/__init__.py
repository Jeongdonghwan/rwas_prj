# -*- coding: utf-8 -*-
"""분류 25종별 섹션 풀. 서브키워드 12,000페이지의 본문을 만든다.

## 왜 분류별로 나누는가
이전 롱폼은 개인회생 절차 10단계가 고정이라, '압류' 키워드 페이지와 '서류' 키워드
페이지가 같은 소제목을 썼다. 그러면 제목만 다른 같은 문서가 된다.
분류마다 그 주제에 맞는 섹션을 따로 두어야 실제로 다른 문서가 된다.

## 구조
    SECTIONS = {
      "<분류명>": {
        "sections": [           # 6개
          {"key": "...",
           "heads":  [4개],     # 소제목 후보 — {{kw}} 포함 권장
           "bodies": [4개]},    # 본문 후보 — <p>…</p> 형태
          ...
        ],
        "faqs": [ {"q": ..., "a": ...} ],   # 4~6개
      },
    }

섹션 6개 × 후보 4개 = 4^6 = 4,096 조합. 같은 분류에 480페이지
(키워드 80 × 제도 6)가 들어가므로 조합이 충분히 남는다.

## 중요 — 본문은 제도 중립으로 쓴다
같은 분류 섹션이 개인회생·개인파산·신용회복·워크아웃·채무조정 5개 제도 페이지에
모두 쓰인다. 그래서 본문에는 **특정 제도에만 있는 사실을 단정해 넣으면 안 된다**
(변제금 3년, 무담보 10억, 금지명령 등). 제도별 사실은 `app/scheme_facts.py`의
요약 박스와 교정 문단이 담당한다.

본문에서 쓸 수 있는 변수:
    {{kw}}      키워드 전체 (예: "수원 개인회생 신청자격")
    {{scheme}}  제도명 (예: "개인회생", "개인파산", "신용회복", "워크아웃", "채무조정")
    {{organ}}   진행 기관 (예: "법원(수원회생법원)", "신용회복위원회")

## 광고규정
보장·단정("반드시 인가됩니다") 금지, 타 사무소 비교 금지, "전문" 표기 금지.
단정이 어려운 것은 "상담에서 확인합니다"로 남긴다.
"""

import importlib  # noqa: E402
import pkgutil  # noqa: E402
from pathlib import Path  # noqa: E402

SECTIONS = {}
MISSING = []


def _load():
    """group*.py를 모두 찾아 병합한다.

    파일 목록을 하드코딩하지 않는 이유: 분류 그룹을 나눠 작성하는 동안에도
    앱이 뜨어야 하고, 그룹을 추가·분할할 때 여기를 고치지 않아도 되게 하기 위함.
    """
    here = Path(__file__).parent
    for mod in sorted(m.name for m in pkgutil.iter_modules([str(here)])
                      if m.name.startswith("group")):
        try:
            m = importlib.import_module("app.keyword_sections.%s" % mod)
        except Exception as exc:          # 작성 중인 파일이 깨져 있어도 앱은 떠야 한다
            MISSING.append("%s (%s)" % (mod, exc))
            continue
        for k, v in getattr(m, "SECTIONS", {}).items():
            if k in SECTIONS:
                raise RuntimeError("분류 중복 정의: %s (%s)" % (k, mod))
            SECTIONS[k] = v


_load()

__all__ = ["SECTIONS"]
