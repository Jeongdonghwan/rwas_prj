# -*- coding: utf-8 -*-
"""원본 지역명(수원) 잔재 검사.

    python scripts/region_leak.py

지역 사이트에서 "수원"이 나오는 게 전부 정당한지 본다. 사무소는 광교 한 곳이라
주소·사무소 옆 법원은 수원이 **맞다.** 그 외의 수원은 치환이 빠진 것이다.

템플릿만 고치고 문장 풀(variants·faq·content_blocks)을 빠뜨렸을 때 실제로
안산 페이지에 "수원개인회생 실무"가 그대로 찍혔다 — 눈으로는 못 잡는다.
"""
import re
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

ORIGIN = "수원"

# 사무소를 설명하는 표현 — 지역이 바뀌어도 수원이 맞다
ALLOWED = [
    "경기도 수원시 영통구", "수원시 영통구", "수원 광교",
    "수원회생법원", "수원지방법원",
]


def allowed_strings():
    """허용 목록 = 사무소 표현 + 그 사이트 설정값.

    설정값을 넣는 이유: 안산의 area_long이 "안산·시흥·수원·화성·군포"처럼
    이웃으로 수원을 열거한다. 이건 치환 누락이 아니라 의도한 내용이다.
    """
    from app.config import REGION
    out = list(ALLOWED)
    out += [v for v in REGION.values() if isinstance(v, str) and ORIGIN in v]
    for v in REGION.values():
        if isinstance(v, list):
            out += [x for x in v if isinstance(x, str) and ORIGIN in x]

    # 시드에 손으로 쓴 지역 설명도 허용한다 — "안산 동쪽 끝이라 수원 방면 통근이
    # 많다"처럼 이웃 도시를 언급하는 건 치환 누락이 아니다.
    from app.models import Dong, Gu
    for g in Gu.query.all():
        out += [t for t in (g.intro_html, g.court_note) if t and ORIGIN in t]
    for d in Dong.query.all():
        out += [t for t in (d.transit_note, d.feature_note) if t and ORIGIN in t]

    return sorted(set(out), key=len, reverse=True)   # 긴 것부터 지워야 조각이 안 남는다


def leaks(text, allowed, keyword=""):
    if keyword:
        text = text.replace(keyword, "")
    for a in allowed:
        text = text.replace(a, "")
    return text.count(ORIGIN)


def main():
    from app import create_app
    from app.config import REGION
    from app.models import CaseType, Dong, Gu, Job, Keyword

    if REGION["name"] == ORIGIN:
        print("원본(수원) 프로젝트입니다 — 검사할 것이 없습니다.")
        return 0

    app = create_app()
    client = app.test_client()
    paths = ["/", "/about/", "/contact/", "/process/", "/faq/",
             "/service/rehab/", "/service/bankruptcy/", "/service/cost/",
             "/service/docs/", "/지역별-개인회생/", "/직업별-개인회생/",
             "/상황별-개인회생/", "/모아보기/", "/사례/"]
    with app.app_context():
        allowed = allowed_strings()
        for g in Gu.query.all():
            paths.append("/%s-개인회생/" % g.name)
        for d in Dong.query.all():
            paths.append("/%s-개인회생/" % d.name)
        for j in Job.query.all():
            paths.append("/%s-개인회생/" % (j.slug_ko or j.slug))
        for c in CaseType.query.all():
            paths.append("/%s-개인회생/" % (c.slug_ko or c.slug))
        rows = Keyword.query.order_by(Keyword.id).all()
        step = max(1, len(rows) // 300)
        # 키워드 자체에 "수원회생법원" 같은 말이 든 것이 있어 본문에서 빼고 센다
        kw_of = {}
        for r in rows[::step][:300]:
            paths.append("/%s/" % r.slug_ko)
            kw_of["/%s/" % r.slug_ko] = r.keyword

    bad = []
    for p in paths:
        r = client.get(p)
        if r.status_code != 200:
            bad.append((p, "HTTP %s" % r.status_code))
            continue
        n = leaks(r.get_data(as_text=True), allowed, kw_of.get(p, ""))
        if n:
            bad.append((p, "%d곳" % n))

    print("검사 %d페이지 / 지역 %s" % (len(paths), REGION["name"]))
    if not bad:
        print("PASS — 설명되지 않는 '%s' 없음" % ORIGIN)
        return 0

    print("FAIL — %d페이지" % len(bad))
    for p, why in bad[:15]:
        print("  %-30s %s" % (p, why))
    # 첫 사례의 문맥을 보여준다 — 어느 문장인지 찾는 게 일의 대부분이다
    t = re.sub(r"<[^>]+>", " ", client.get(bad[0][0]).get_data(as_text=True))
    for a in allowed:
        t = t.replace(a, "")
    for m in list(re.finditer(ORIGIN, t))[:5]:
        seg = re.sub(r"\s+", " ", t[max(0, m.start() - 60):m.start() + 50])
        print("    … %s" % seg)
    return 1


if __name__ == "__main__":
    sys.exit(main())
