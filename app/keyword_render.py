# -*- coding: utf-8 -*-
"""서브키워드 페이지 본문 조립.

한 페이지는 아래 순서로 만들어진다.

    1. 교정 문단        needs_correction일 때만 (app/scheme_facts.py)
    2. 핵심 요약 박스    제도별 사실 (SCHEME_FACTS)
    3. 분류별 섹션 6개   app/keyword_sections/ — 제도 중립
    4. 제도 비교표       템플릿에서 partials/lf_table.html 재사용
    5. FAQ             분류별
    6. 관련 링크        같은 분류·같은 키워드의 다른 제도

선택은 전부 `content.stable_hash`(blake2b) 기반이라 같은 페이지는 항상 같은 결과다.
같은 분류에 480페이지(키워드 80 × 제도 6)가 들어가는데 섹션 6개 × 후보 4개 =
4,096조합이므로 조합이 충분히 남는다.
"""

from app.content import pick, render_tpl, stable_hash
from app.keyword_rules import SCHEMES, correction_terms
from app.keyword_sections import SECTIONS
from app.scheme_facts import SCHEME_FACTS, correction_html

# 분류가 아직 정의되지 않았을 때 쓰는 기본 섹션 세트
FALLBACK_CATEGORY = "상황형"


def _cat(category):
    """분류에 해당하는 섹션 세트. 없으면 기본값."""
    return SECTIONS.get(category) or SECTIONS.get(FALLBACK_CATEGORY) or {
        "sections": [], "faqs": []
    }


def tpl_vars(kw):
    """문장 풀에서 쓸 수 있는 변수."""
    facts = SCHEME_FACTS[kw.scheme]
    return {
        "kw": kw.keyword,
        "scheme": facts["name"],
        "organ": facts["organ"],
    }


def build(kw):
    """Keyword 행 하나를 렌더링에 필요한 dict로 만든다."""
    facts = SCHEME_FACTS[kw.scheme]
    v = tpl_vars(kw)
    seed = kw.slug_ko
    cat = _cat(kw.category)

    sections = []
    for i, sec in enumerate(cat["sections"]):
        key = "%s::%d" % (sec.get("key", i), i)
        sections.append({
            "head": render_tpl(pick(seed, "h::" + key, sec["heads"]), **v),
            "body": render_tpl(pick(seed, "b::" + key, sec["bodies"]), **v),
        })

    # FAQ는 순서를 섞어 페이지마다 구성이 달라지게 한다
    pool = cat.get("faqs") or []
    ordered = sorted(pool, key=lambda f: stable_hash("%s::faq::%s" % (seed, f["q"][:30])))
    faqs = [
        {"q": render_tpl(f["q"], **v), "a": render_tpl(f["a"], **v)}
        for f in ordered[:5]
    ]

    terms = correction_terms(_base_keyword(kw), kw.scheme) if kw.needs_correction else []

    return {
        "kw": kw,
        "scheme_name": facts["name"],
        "organ": facts["organ"],
        "intro": facts["intro"],
        "summary": render_tpl(facts["summary"], **v),
        "kv": facts["kv"],
        "correction": correction_html(terms, kw.scheme),
        "sections": sections,
        "faqs": faqs,
    }


def _base_keyword(kw):
    """교정 판정은 원본('개인회생 …') 기준이므로 되돌려서 판정한다."""
    text = kw.keyword
    if kw.region:
        text = text[len(kw.region):].strip()
    name = SCHEMES[kw.scheme]
    return text.replace(name, "개인회생") if kw.scheme != "rehab" else text
