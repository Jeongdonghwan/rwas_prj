# -*- coding: utf-8 -*-
"""다른 지역 사이트의 구·동 이름이 섞여 들어왔는지 검사한다.

    python scripts/foreign_region_check.py

`region_leak.py`는 지역명("수원")만 본다. 그래서 **구·동 이름이 박힌 건 못 잡는다** —
실제로 안산 사이트가 이런 것들을 내보내고 있었다.

  · 지역허브 설명: "장안구·권선구·팔달구·영통구 31개 동별로"
  · 상담폼 거주지역 선택: 장안구 / 권선구 / 팔달구 / 영통구
  · schema.org 주소: "안산시 영통구" (존재하지 않는 주소)

이 검사는 **다른 사이트에만 있는 이름**을 금지어로 삼는다. 같은 이름이 여러 지역에
있는 경우(중앙동·정자동·고등동 등)는 자기 것이기도 하므로 제외한다.

사무소 주소(수원시 영통구·광교)는 어느 사이트에서나 사실이므로 허용한다.
"""
import csv
import importlib
import re
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# 사무소를 가리키는 표현 — 지역이 바뀌어도 참이다
OFFICE_OK = ["경기도 수원시 영통구", "수원시 영통구", "수원 광교",
             "수원회생법원", "수원지방법원",
             # 사무소가 경기도에 있어 푸터·schema.org에 늘 나온다
             "경기도"]

SITES = ["ansan", "yongin", "seongnam", "dosan"]

# 일상어와 겹치는 지명은 검사에서 뺀다. 그대로 두면 "이동 부담이 적습니다"가
# 용인 이동읍으로 잡혀 매번 거짓 경보가 뜬다 — 게이트가 울기만 하면 아무도 안 본다.
# 지명으로 쓸 때는 앞에 지역명이 붙으므로(용인 이동읍) 실제 누락은 다른 이름이 잡아준다.
AMBIGUOUS = {"이동", "일동", "와동", "사동", "중앙동", "신촌동", "시흥동", "고등동"}


def names_of_site_data(mod):
    out = {g["name"] for g in mod.GU}
    out |= {d[2] for d in mod.DONG}          # (gu, slug, 이름, ...)
    return out


def suwon_names():
    """수원은 site_data가 없어 원본 저장소의 시드에서 읽는다."""
    out = set()
    for f, col in (("seed/gu.csv", "name"), ("seed/dong.csv", "name")):
        p = ROOT / f
        if p.exists():
            with open(p, encoding="utf-8") as fh:
                out |= {r[col] for r in csv.DictReader(fh) if r.get(col)}
    return out


def main():
    from app import create_app
    from app.config import REGION
    from app.models import CaseType, Dong, Gu, Job, Keyword

    all_names = {"suwon": suwon_names()}
    for s in SITES:
        try:
            all_names[s] = names_of_site_data(
                importlib.import_module("scripts.site_data.%s" % s))
        except Exception as e:
            print("  (site_data/%s 를 읽지 못했습니다: %s)" % (s, e))

    app = create_app()
    client = app.test_client()
    with app.app_context():
        mine = {g.name for g in Gu.query.all()} | {d.name for d in Dong.query.all()}
        # 지금 사이트가 어느 쪽인지 — 구 이름이 가장 많이 겹치는 세트
        me = max(all_names, key=lambda k: len(all_names[k] & mine)) if mine else None
        forbidden = set()
        for k, v in all_names.items():
            if k != me:
                forbidden |= v
        forbidden -= mine
        forbidden -= AMBIGUOUS
        # 내 시드 문장이 이웃 도시를 언급하는 건 의도된 것
        for g in Gu.query.all():
            for t in (g.intro_html, g.court_note):
                forbidden -= {n for n in forbidden if t and n in t}
        for d in Dong.query.all():
            for t in (d.transit_note, d.feature_note):
                forbidden -= {n for n in forbidden if t and n in t}

        paths = ["/", "/about/", "/contact/", "/process/", "/faq/", "/사례/",
                 "/service/rehab/", "/service/bankruptcy/", "/service/cost/",
                 "/service/docs/", "/지역별-개인회생/", "/직업별-개인회생/",
                 "/상황별-개인회생/", "/모아보기/", "/privacy/"]
        for g in Gu.query.all():
            paths.append("/%s-개인회생/" % g.name)
        for d in Dong.query.all():
            paths.append("/%s-개인회생/" % d.name)
        for j in Job.query.all():
            paths.append("/%s-개인회생/" % (j.slug_ko or j.slug))
        for c in CaseType.query.all():
            paths.append("/%s-개인회생/" % (c.slug_ko or c.slug))
        rows = Keyword.query.order_by(Keyword.id).all()
        step = max(1, len(rows) // 200)
        paths += ["/%s/" % r.slug_ko for r in rows[::step][:200]]

    print("지역 %s / 내 지역명 %d개 / 금지 이름 %d개 / 검사 %d페이지"
          % (REGION["name"], len(mine), len(forbidden), len(paths)))

    hits = {}
    for p in paths:
        r = client.get(p)
        if r.status_code != 200:
            hits.setdefault("HTTP %s" % r.status_code, []).append(p)
            continue
        body = r.get_data(as_text=True)
        for ok in OFFICE_OK:
            body = body.replace(ok, "")
        for n in forbidden:
            if n in body:
                hits.setdefault(n, []).append(p)

    if not hits:
        print("PASS — 다른 지역 이름이 섞이지 않았습니다")
        return 0
    print("FAIL — %d종" % len(hits))
    for n, ps in sorted(hits.items(), key=lambda kv: -len(kv[1]))[:12]:
        print("  %-14s %d페이지  예: %s" % (n, len(ps), ps[0]))
    return 1


if __name__ == "__main__":
    sys.exit(main())
