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

from itertools import combinations

from app.config import REGION
from app.content import josa, pick, render_tpl, stable_hash
from app.keyword_rules import SCHEMES, correction_terms
from app.keyword_sections import SECTIONS
from app.scheme_facts import COURT_NAME, SCHEME_FACTS, correction_html
from app.summary_points import LEADS, OTHER_HEADS, POINTS, RELATED_HEADS
from app.variant_codes import VECTORS

# 분류가 아직 정의되지 않았을 때 쓰는 기본 섹션 세트
FALLBACK_CATEGORY = "상황형"

# 제도·지역별 벡터 오프셋. 96개 벡터와 서로소인 간격(19·7)을 써서
# 제도가 다르면 반드시 다른 벡터가 배정되게 한다.
SCHEME_OFFSET = {code: i * 19 for i, code in enumerate(SCHEMES)}
REGION_OFFSET = 7

# 사이트 오프셋 — multi-site-plan.md §3.
# 지역 사이트들은 같은 문장 풀을 공유한다. 오프셋이 다르면 다른 벡터가 뽑히고,
# VECTORS는 서로 최소 3자리가 다른 코드라 **6개 섹션 중 최소 3개가 달라진다.**
# 수원은 0이라 기존 출력이 그대로 나온다.
SITE_OFFSET = REGION.get("site_offset", 0)
SITE_SALT = REGION.get("site_salt", "")


def _region_offset(region):
    """지역 축이 몇 갈래냐에 따라 오프셋을 다르게 준다.

    수원형(gu_dong)은 지역 접두사가 붙었다/아니다 둘뿐이라 상수 하나면 됐다.
    **도산레이는 지역 축이 17개 시도라 상수를 쓰면 17개가 전부 같은 오프셋을
    받는다** — "서울특별시 개인회생 자격"과 "경기도 개인회생 자격"이 같은 섹션
    조합을 쓰게 된다. 게다가 그 사이트는 제도가 하나라 SCHEME_OFFSET이 전부 0이라
    분산을 지역 축이 혼자 떠맡는다. 그래서 시도마다 다른 값을 준다.
    """
    if not region:
        return 0
    if REGION.get("area_mode") == "sido":
        return REGION_OFFSET * (1 + stable_hash("sido::%s" % region) % 13)
    return REGION_OFFSET

# FAQ 풀에서 실제로 보여줄 개수. 풀(5개)을 다 쓰면 같은 분류가 전부 같은 FAQ를
# 갖게 되므로 부분집합을 쓴다. C(5,3)=10가지 조합이 순번으로 배정된다.
FAQ_TAKE = 3


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
    # 시드에 사이트 소금을 섞는다 — stable_hash 기반 선택(문장 풀·FAQ 순서)이
    # 사이트마다 달라진다. 수원은 소금이 ""이라 기존 시드 그대로다.
    seed = (SITE_SALT + "::" + kw.slug_ko) if SITE_SALT else kw.slug_ko
    cat = _cat(kw.category)

    # 섹션 조합은 해시가 아니라 배정 코드로 고른다. 해시로 독립 선택하면
    # 같은 그룹에서 5~6개 섹션이 우연히 겹치는 쌍이 생긴다(app/variant_codes.py).
    #
    # variant_idx는 (분류, 제도, 지역) 그룹 안의 순번이라, 같은 키워드의 제도별
    # 페이지는 순번이 같다. 그대로 쓰면 제도만 다른 5페이지가 같은 섹션을 쓴다
    # (실측: 제도 간 유사도 73%까지 올라갔다). 그래서 제도·지역만큼 벡터를 어긋낸다.
    # 오프셋은 그룹 전체에 똑같이 적용되므로 그룹 내 거리는 그대로 유지된다.
    offset = (SCHEME_OFFSET.get(kw.scheme, 0)
              + _region_offset(kw.region)
              + SITE_OFFSET)
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

    # FAQ는 **부분집합**을 골라야 한다. 풀 5개에서 5개를 다 쓰면 같은 분류의 모든
    # 페이지가 같은 FAQ를 갖고, 순서를 섞어도 3-gram 집합은 그대로라 유사도가 안 내려간다.
    # (실측: FAQ가 공통 그램의 37%를 차지했다.) 조합을 순번으로 배정해 겹침을 줄인다.
    pool = cat.get("faqs") or []
    faqs = []
    if pool:
        take = min(FAQ_TAKE, len(pool))
        combos = list(combinations(range(len(pool)), take))
        idx = combos[((kw.variant_idx or 0) + offset) % len(combos)]
        chosen = [pool[i] for i in idx]
        # 고른 뒤 순서만 해시로 섞는다(보이는 순서를 페이지마다 다르게)
        chosen.sort(key=lambda f: stable_hash("%s::faq::%s" % (seed, f["q"][:30])))
        faqs = [{"q": render_tpl(f["q"], **v), "a": render_tpl(f["a"], **v)}
                for f in chosen]

    terms = correction_terms(_base_keyword(kw), kw.scheme) if kw.needs_correction else []
    summary, kv_main, kv_side = _summary_block(kw, seed, v)

    return {
        "kw": kw,
        "scheme_name": facts["name"],
        "organ": facts["organ"],
        "intro": facts["intro"],
        "summary": summary,
        "desc": _meta_desc(kw.keyword, summary),
        "kv": kv_main,
        "kv_side": kv_side,
        "lead": pick(seed, "lead", LEADS).format(
            intro=facts["intro"], cat=kw.category, kw=kw.keyword,
            kw_eul=josa(kw.keyword, "을를")),
        "related_head": pick(seed, "rhead", RELATED_HEADS).format(cat=kw.category),
        "other_head": pick(seed, "ohead", OTHER_HEADS),
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


def _summary_block(kw, seed, v):
    """핵심 요약 문단 + 요약 표 — 페이지마다 다르게 조립한다.

    문단: 첫 문장(3가지 중 1) + 사실 항목 3개(전체 5~6개 중 해시로 골라 순서까지 섞음, 표현 3가지 중 1).
    표: kv 6줄 중 4줄만 본문에, 나머지는 사이드 박스에. 같은 분류 페이지끼리 표가 통째로 같던 것을 깬다.
    사실값은 scheme_facts.kv 그대로다 — 표현만 바뀐다.
    """
    facts = SCHEME_FACTS[kw.scheme]
    pts = POINTS.get(kw.scheme)
    if not pts:                                   # 재료가 없으면 예전 고정 문단
        summary = render_tpl(facts["summary"], **v)
    else:
        order = sorted(range(len(pts["points"])),
                       key=lambda i: stable_hash("%s::pt::%d" % (seed, i)))[:3]
        parts = [pick(seed, "open", pts["open"])]
        parts += [pick(seed, "ph::%d" % i, pts["points"][i]) for i in sorted(order)]
        summary = render_tpl(" ".join(parts), court=COURT_NAME, **v)
    rows = list(facts["kv"])
    take = 4 if len(rows) > 4 else 3
    idx = sorted(sorted(range(len(rows)),
                        key=lambda i: stable_hash("%s::kv::%d" % (seed, i)))[:take])
    kv_main = [rows[i] for i in idx]
    kv_side = [rows[i] for i in range(len(rows)) if i not in idx] or kv_main[:2]
    return summary, kv_main, kv_side


def _meta_desc(keyword, summary_html, lo=40, hi=79):
    """메타 설명 — 그 페이지 요약 문단에서 만든다(40~79자).

    예전엔 '{키워드} 안내. 수원개인회생 신청자격·비용·기간·준비서류 정리.'로 1만 2천 페이지가
    뒷부분이 전부 같았고, 짧은 키워드는 40자 미만이었다.
    """
    import re
    text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", summary_html)).strip()
    # 첫 문장은 정의라 키워드와 겹친다 → 둘째 문장부터 쓰고, 모자라면 첫 문장까지
    sents = [x.strip() for x in re.split(r"(?<=[.다요])\s+", text) if x.strip()]
    body = " ".join(sents[1:]) or text
    out = "%s — %s" % (keyword, body)
    if len(out) > hi:
        cut = out[:hi]
        end = max(cut.rfind("다."), cut.rfind("요."))
        if end + 2 >= lo:                       # 문장 끝에서 자를 수 있으면 거기서
            out = cut[:end + 2]
        else:
            sp = out[:hi - 1].rfind(" ")
            out = out[:sp if sp > lo else hi - 1].rstrip(" ,·—.") + "…"
    if len(out) < lo:
        out = (out.rstrip(".") + ". 신청자격·비용·준비서류까지 정리했습니다.")[:hi]
    return out
