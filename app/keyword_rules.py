# -*- coding: utf-8 -*-
"""제도별 용어 규칙 — 키워드를 다른 제도로 바꿨을 때 사실과 어긋나는지 판정한다.

배경: 서브키워드 2,000개는 전부 '개인회생' 기준으로 만들어졌다. 제도명만 바꾸면
개인회생에만 있는 절차 용어가 그대로 남아 틀린 문서가 된다.
예) "개인회생 변제금" → "개인파산 변제금" (파산에는 변제금 개념이 없다)

대응(확정): 키워드를 버리지 않고 **본문 최상단에 교정 문단**을 넣어 바로잡는다.
실제로 헷갈려서 검색하는 사람이 많아 검색의도에도 맞다.
`needs_correction()`이 True면 그 페이지는 교정 문단을 먼저 출력한다.

**사실 확인이 끝난 용어만 단정한다.** 목록에 없는 용어는 교정하지 않고 일반 설명으로 둔다
(광고규정상 틀린 단정이 더 위험하다).
"""

# 제도 코드 → 표시명. URL·타이틀·본문에 쓰인다.
SCHEMES = {
    "rehab": "개인회생",
    "bankruptcy": "개인파산",
    "credit": "신용회복",
    "workout": "워크아웃",
    "adjust": "채무조정",
    # 도산(倒産) = 회생 + 파산 통칭. 전국 단위 사이트(도산레이)에서만 쓴다.
    # **반드시 맨 뒤에 둘 것** — keyword_render.SCHEME_OFFSET이
    # `enumerate(SCHEMES)` 순번이라, 중간에 끼우면 기존 제도의 오프셋이 밀려
    # 이미 색인된 수원 페이지의 섹션 조합이 전부 바뀐다.
    "dosan": "도산",
}

# 제도별 서술 각도 — 4세트가 서로 비슷해지지 않게 하는 축
SCHEME_ANGLE = {
    "rehab": "법원 절차로 가용소득만 변제하고 잔여 채무를 면책받는 제도",
    "bankruptcy": "소득으로 변제가 어려운 경우 재산을 청산하고 면책받는 법원 절차",
    "credit": "신용회복위원회 채무조정과 신용정보 회복 경로",
    "workout": "연체 90일 이상 채무자의 개인워크아웃(원금·이자 감면)",
    "adjust": "내 상황에 맞는 채무조정 제도를 고르고 비교하는 관점",
    "dosan": "회생과 파산을 아우르는 도산절차 전반 — 소득과 재산 상황에 따라 경로가 갈린다",
}

# 개인회생에만 존재하는 절차 용어 → 다른 제도로 치환하면 교정이 필요하다.
# 각 항목: (용어, 그 용어가 존재하지 않는 제도들, 교정 문구 키)
REHAB_ONLY_TERMS = {
    "변제금": ("bankruptcy",),
    "변제계획": ("bankruptcy", "credit", "workout", "adjust"),
    "변제기간": ("bankruptcy",),
    "개시결정": ("bankruptcy", "credit", "workout", "adjust"),
    "인가": ("bankruptcy", "credit", "workout", "adjust"),
    "금지명령": ("credit", "workout", "adjust"),
    "중지명령": ("credit", "workout", "adjust"),
    "회생위원": ("bankruptcy", "credit", "workout", "adjust"),
    "가용소득": ("bankruptcy", "credit", "workout", "adjust"),
    "청산가치": ("credit", "workout", "adjust"),
    "채권자집회": ("credit", "workout", "adjust"),
    "보정": ("credit", "workout", "adjust"),
    "폐지": ("credit", "workout", "adjust"),
    "재신청": ("credit", "workout", "adjust"),
}

# 법원 절차가 아닌 제도 — '법원·판사·관할' 류 표현이 성립하지 않는다
NON_COURT_SCHEMES = ("credit", "workout")
COURT_TERMS = ("법원", "판사", "관할", "기각", "파산선고")


def _terms_in(keyword):
    return [t for t in REHAB_ONLY_TERMS if t in keyword]


def needs_correction(keyword, scheme):
    """이 키워드를 이 제도 페이지로 만들 때 교정 문단이 필요한가."""
    if scheme == "rehab":
        return False
    for term in _terms_in(keyword):
        if scheme in REHAB_ONLY_TERMS[term]:
            return True
    if scheme in NON_COURT_SCHEMES and any(t in keyword for t in COURT_TERMS):
        return True
    return False


def correction_terms(keyword, scheme):
    """교정해야 할 용어 목록 (본문 교정 문단 생성용)."""
    if scheme == "rehab":
        return []
    out = [t for t in _terms_in(keyword) if scheme in REHAB_ONLY_TERMS[t]]
    if scheme in NON_COURT_SCHEMES:
        out += [t for t in COURT_TERMS if t in keyword]
    return out


def to_scheme(keyword, scheme):
    """'개인회생 ...' 키워드를 대상 제도 표기로 바꾼다."""
    name = SCHEMES[scheme]
    return keyword.replace("개인회생", name) if scheme != "rehab" else keyword
