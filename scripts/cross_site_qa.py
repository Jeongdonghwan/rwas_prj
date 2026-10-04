# -*- coding: utf-8 -*-
"""사이트 간 중복 검사 — 지역 사이트들이 서로 복제본인지 잰다.

    python scripts/cross_site_qa.py                      # 수원 vs 안산 설정
    python scripts/cross_site_qa.py --sample 800
    python scripts/cross_site_qa.py --offset 53 --salt yongin

## 왜 필요한가
`keyword_qa.py`는 **한 사이트 안**의 중복만 본다. 지역 사이트 5개는 같은 문장 풀
34만 자를 공유하므로, 사이트 안쪽이 아무리 깨끗해도 **사이트끼리 지역명만 다른
복제본**일 수 있다. 같은 사업자의 사이트가 그러면 도어웨이로 묶여
**이미 색인된 수원 사이트까지 같이 평가가 내려간다.**

## 어떻게 재는가
REGION은 import 시점에 한 번 읽히므로 한 프로세스 안에서 두 설정을 돌릴 수 없다.
그래서 **자식 프로세스를 두 번 띄워** 각각 SITE_SALT/SITE_OFFSET을 다르게 주고
같은 키워드의 본문을 뽑아 비교한다.

비교 전에 지역명과 키워드를 지운다 — 지우지 않으면 지역명이 다르다는 이유만으로
유사도가 내려가 **실제보다 좋아 보인다.**

## 기준
multi-site-plan.md §5 — 평균 0.60 미만 / 최대 0.75 미만.
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

MEAN_FAIL = 0.60
MAX_FAIL = 0.75


def dump_bodies(out_path, sample):
    """자식 프로세스에서 실행 — 현재 설정으로 키워드 본문을 뽑아 저장한다."""
    from app import create_app
    from app.models import Keyword
    from scripts.seo_qa import text_of

    app = create_app()
    client = app.test_client()
    rows = {}
    with app.app_context():
        all_rows = Keyword.query.order_by(Keyword.id).all()
        step = max(1, len(all_rows) // sample)
        picked = all_rows[::step][:sample]
        meta = [(r.slug_ko, r.keyword) for r in picked]

    for slug, keyword in meta:
        r = client.get("/%s/" % slug)
        if r.status_code != 200:
            continue
        rows[slug] = [keyword, text_of(r.get_data(as_text=True))]

    Path(out_path).write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")


def run_child(out_path, sample, salt, offset):
    env = dict(os.environ, SITE_SALT=salt, SITE_OFFSET=str(offset),
               PYTHONIOENCODING="utf-8")
    cmd = [sys.executable, __file__, "--dump", out_path, "--sample", str(sample)]
    subprocess.run(cmd, cwd=str(ROOT), env=env, check=True)
    return json.loads(Path(out_path).read_text(encoding="utf-8"))


def compare(a, b, region_a, region_b):
    from scripts.seo_qa import grams, jaccard

    def clean(text, keyword, region):
        out = text.replace(keyword, "")
        for token in keyword.split():
            out = out.replace(token, "")
        # 지역명을 지우지 않으면 "지역명이 다르다"는 이유만으로 점수가 내려가
        # 실제보다 좋아 보인다
        for r in (region_a, region_b, region):
            if r:
                out = out.replace(r, "")
        return out

    scores = []
    for slug in sorted(set(a) & set(b)):
        ka, ta = a[slug]
        kb, tb = b[slug]
        ga = grams(clean(ta, ka, region_a))
        gb = grams(clean(tb, kb, region_b))
        if ga and gb:
            scores.append((jaccard(ga, gb), slug))
    return scores


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump")          # 내부용 — 자식 프로세스 진입점
    ap.add_argument("--sample", type=int, default=400)
    ap.add_argument("--salt", default="ansan")
    ap.add_argument("--offset", type=int, default=31)
    args = ap.parse_args()

    if args.dump:
        dump_bodies(args.dump, args.sample)
        return 0

    from app.config import REGION
    tmp = ROOT / ".qa_tmp"
    tmp.mkdir(exist_ok=True)

    print("기준 사이트  : salt=%r offset=%d  (현재 설정)"
          % (REGION["site_salt"], REGION["site_offset"]))
    print("비교 사이트  : salt=%r offset=%d" % (args.salt, args.offset))
    print("표본         : %d페이지\n" % args.sample)

    base = run_child(str(tmp / "a.json"), args.sample,
                     REGION["site_salt"], REGION["site_offset"])
    other = run_child(str(tmp / "b.json"), args.sample, args.salt, args.offset)

    scores = compare(base, other, REGION["name"], REGION["name"])
    if not scores:
        print("비교할 페이지가 없습니다 — keyword 테이블이 비었는지 확인하세요.")
        return 1

    vals = sorted(s for s, _ in scores)
    mean = sum(vals) / len(vals)
    worst = sorted(scores, reverse=True)[:8]

    print("비교 쌍 %d개" % len(scores))
    print("  평균 %.3f / 중앙 %.3f / 최대 %.3f"
          % (mean, vals[len(vals) // 2], vals[-1]))
    print("\n가장 비슷한 쌍:")
    for s, slug in worst:
        print("  %.3f  %s" % (s, slug))

    ok = mean < MEAN_FAIL and vals[-1] < MAX_FAIL
    print("\n기준: 평균 < %.2f, 최대 < %.2f" % (MEAN_FAIL, MAX_FAIL))
    print("%s" % ("PASS — 사이트끼리 충분히 다르다" if ok else
                  "FAIL — 이대로 4개를 만들면 도어웨이로 묶일 수 있다"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
