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
from app.variant_codes import VECTORS

# 분류가 아직 정의되지 않았을 때 쓰는 기본 섹션 세트
FALLBACK_CATEGORY = "상황형"

# 제도·지역별 벡터 오프셋. 96개 벡터와 서로소인 간격(19·7)을 써서
# 제도가 다르면 반드시 다른 벡터가 배정되게 한다.
SCHEME_OFFSET = {code: i * 19 for i, code in enumerate(SCHEMES)}
REGION_OFFSET = 7


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

    # 섹션 조합은 해시가 아니라 배정 코드로 고른다. 해시로 독립 선택하면
    # 같은 그룹에서 5~6개 섹션이 우연히 겹치는 쌍이 생긴다(app/variant_codes.py).
    #
    # variant_idx는 (분류, 제도, 지역) 그룹 안의 순번이라, 같은 키워드의 제도별
    # 페이지는 순번이 같다. 그대로 쓰면 제도만 다른 5페이지가 같은 섹션을 쓴다
    # (실측: 제도 간 유사도 73%까지 올라갔다). 그래서 제도·지역만큼 벡터를 어긋낸다.
    # 오프셋은 그룹 전체에 똑같이 적용되므로 그룹 내 거리는 그대로 유지된다.
    offset = SCHEME_OFFSET.get(kw.scheme, 0) + (REGION_OFFSET if kw.region else 0)
    vec = VECTORS[((kw.variant_idx or 0) + offset) % len(VECTORS)]
    sections = []
    for i, sec in enumerate(cat["sections"]):
        bodies = sec["bodies"]
        heads = sec["heads"]
        b = bodies[vec[i] % len(bodies)] if i < len(vec) else \
            pick(seed, "b::%d" % i, bodies)
        # 소제목은 본문과 다른 축으로 돌려 같은 조합이라도 제목이 겹치지 않게
        h = heads[(vec[i] + (kw.variant_idx or 0)) % len(heads)] if i < len(vec) else \
            pick(seed, "h::%d" % i, heads)
        sections.append({"head": render_tpl(h, **v), "body": render_tpl(b, **v)})

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
