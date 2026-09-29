# -*- coding: utf-8 -*-
"""서브키워드 12,000페이지 중복 검사.

    python scripts/keyword_qa.py               # 전체
    python scripts/keyword_qa.py --sample 2000 # 표본만 (빠른 확인용)

## 왜 별도 스크립트인가
기존 `seo_qa.py`는 전 페이지를 서로 비교한다(O(n²)). 실측으로 10,000페이지에서
5.2시간·1.6GB가 들어 12,000페이지에는 쓸 수 없다.

두 가지로 해결한다.

1. **MinHash 서명** — 본문 3-gram 집합을 128개 정수로 압축해서 들고 있는다.
   12,000페이지 × 128개 = 메모리 몇 MB. 자카드 유사도를 ±0.04 수준으로 추정한다.
2. **비교 대상을 좁힌다** — 서로 비슷해질 수 있는 조합만 본다.
   · 같은 (분류, 제도, 지역) 안에서 — 같은 섹션 세트를 쓰므로 여기가 가장 위험하다
   · 같은 키워드의 제도별 페이지끼리 — 4제도로 나눈 것이 의미가 있는지 확인

전수 비교 474,000쌍 대신 실제로 위험한 쌍만 보므로 수 분 안에 끝난다.
"""
import argparse
import hashlib
import random
import re
import sys
from collections import defaultdict
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import create_app                      # noqa: E402
from app.models import Keyword                  # noqa: E402
from scripts.seo_qa import grams, jaccard, text_of  # noqa: E402

PERMS = 128
MASK = (1 << 61) - 1
SIM_WARN, SIM_FAIL = 0.60, 0.75   # 같은 분류 안은 원래 비슷하므로 seo_qa보다 완화
CROSS_WARN = 0.70                 # 제도 간(같은 키워드)은 더 크게 달라야 의미가 있다


def _perm_params(seed=7):
    rnd = random.Random(seed)
    return [(rnd.randrange(1, MASK), rnd.randrange(0, MASK)) for _ in range(PERMS)]


PARAMS = _perm_params()


def signature(gram_set):
    """MinHash 서명. 집합 전체 대신 이 128개만 들고 있으면 된다."""
    sig = [MASK] * PERMS
    for g in gram_set:
        h = int.from_bytes(hashlib.blake2b(g.encode("utf-8"), digest_size=8).digest(),
                           "big") & MASK
        for i, (a, b) in enumerate(PARAMS):
            v = (a * h + b) & MASK
            if v < sig[i]:
                sig[i] = v
    return sig


def est_jaccard(s1, s2):
    return sum(1 for a, b in zip(s1, s2) if a == b) / PERMS


def strip_name(text, keyword):
    """키워드 문자열을 지운 뒤 비교한다 — 이름만 바꾼 복제를 잡기 위함."""
    out = text.replace(keyword, "")
    for token in keyword.split():
        out = out.replace(token, "")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int, default=0, help="표본 페이지 수(0이면 전체)")
    ap.add_argument("--verify", type=int, default=200,
                    help="MinHash 추정치를 정확값과 대조할 쌍 수")
    args = ap.parse_args()

    app = create_app()
    client = app.test_client()

    with app.app_context():
        rows = Keyword.query.order_by(Keyword.id).all()
    if args.sample and args.sample < len(rows):
        rnd = random.Random(1)
        rows = rnd.sample(rows, args.sample)
    print("검사 대상: %d 페이지" % len(rows))

    sigs, lengths, errors = {}, {}, []
    exact_pairs = []          # 정확도 대조용으로 일부만 원본 집합을 남긴다
    keep_sets = {}

    for i, k in enumerate(rows, 1):
        if i % 1000 == 0:
            print("  렌더 %d/%d" % (i, len(rows)))
        r = client.get("/%s/" % k.slug_ko)
        if r.status_code != 200:
            errors.append("%s: HTTP %d" % (k.slug_ko, r.status_code))
            continue
        body = text_of(r.get_data(as_text=True), main_only=True)
        lengths[k.id] = len(body.replace(" ", ""))
        gs = grams(strip_name(body, k.keyword))
        sigs[k.id] = signature(gs)
        if len(keep_sets) < args.verify:
            keep_sets[k.id] = gs

    print("렌더 완료: %d 성공 / %d 실패" % (len(sigs), len(errors)))

    # ── MinHash 정확도 확인 ────────────────────────────────────────
    ids = list(keep_sets)
    if len(ids) >= 2:
        diffs = []
        rnd = random.Random(3)
        for _ in range(min(args.verify, 300)):
            a, b = rnd.sample(ids, 2)
            diffs.append(abs(est_jaccard(sigs[a], sigs[b]) - jaccard(keep_sets[a], keep_sets[b])))
        print("MinHash 추정 오차: 평균 %.3f / 최대 %.3f (%d쌍 대조)"
              % (sum(diffs) / len(diffs), max(diffs), len(diffs)))

    by_id = {k.id: k for k in rows}

    # ── 1) 같은 (분류, 제도, 지역) 안 ──────────────────────────────
    groups = defaultdict(list)
    for k in rows:
        if k.id in sigs:
            groups[(k.category, k.scheme, k.region)].append(k.id)

    stats, worst = [], []
    for key, members in groups.items():
        if len(members) < 2:
            continue
        vals = []
        for i in range(len(members)):
            for j in range(i + 1, len(members)):
                s = est_jaccard(sigs[members[i]], sigs[members[j]])
                vals.append(s)
                if s >= SIM_WARN:
                    worst.append((s, key, members[i], members[j]))
        stats.append((key, sum(vals) / len(vals), max(vals), len(vals)))

    stats.sort(key=lambda x: -x[2])
    print("\n=== 같은 분류·제도 안의 유사도 (상위 10 그룹) ===")
    print("%-14s %-11s %-5s %6s %6s %8s" % ("분류", "제도", "지역", "평균", "최대", "쌍"))
    for (cat, sch, rg), avg, mx, n in stats[:10]:
        print("%-14s %-11s %-5s %5.0f%% %5.0f%% %8d" % (cat, sch, rg or "-", avg * 100, mx * 100, n))
    if stats:
        alla = [s[1] for s in stats]
        allm = [s[2] for s in stats]
        print("전체 그룹 %d개 — 평균의 평균 %.0f%% / 최대의 최대 %.0f%%"
              % (len(stats), sum(alla) / len(alla) * 100, max(allm) * 100))

    # ── 2) 같은 키워드의 제도별 페이지끼리 ─────────────────────────
    by_src = defaultdict(list)
    for k in rows:
        if k.id in sigs and not k.region:
            by_src[k.source_no].append(k.id)
    cross = []
    for src, members in by_src.items():
        for i in range(len(members)):
            for j in range(i + 1, len(members)):
                cross.append((est_jaccard(sigs[members[i]], sigs[members[j]]),
                              members[i], members[j]))
    if cross:
        cross.sort(key=lambda x: -x[0])
        avg = sum(c[0] for c in cross) / len(cross)
        print("\n=== 같은 키워드의 제도별 페이지끼리 (%d쌍) ===" % len(cross))
        print("평균 %.0f%% / 최대 %.0f%%" % (avg * 100, cross[0][0] * 100))
        print("가장 비슷한 5쌍:")
        for s, a, b in cross[:5]:
            print("  %.0f%%  %s  ↔  %s" % (s * 100, by_id[a].keyword, by_id[b].keyword))
        over = [c for c in cross if c[0] >= CROSS_WARN]
        if over:
            print("  ⚠ %d쌍이 %d%% 이상 — 제도별 서술 각도를 더 벌려야 한다"
                  % (len(over), CROSS_WARN * 100))

    # ── 3) 분량 ────────────────────────────────────────────────────
    if lengths:
        vals = sorted(lengths.values())
        thin = [i for i, v in lengths.items() if v < 1500]
        print("\n=== 본문 분량 ===")
        print("최소 %d자 / 중앙 %d자 / 최대 %d자" % (vals[0], vals[len(vals) // 2], vals[-1]))
        if thin:
            print("  ⚠ 1,500자 미만 %d개" % len(thin))

    # ── 판정 ───────────────────────────────────────────────────────
    fails = [w for w in worst if w[0] >= SIM_FAIL]
    print("\n" + "=" * 58)
    if errors:
        print("렌더 실패 %d건:" % len(errors))
        for e in errors[:10]:
            print("   ", e)
    if fails:
        fails.sort(key=lambda x: -x[0])
        print("유사도 %d%% 초과 %d쌍:" % (SIM_FAIL * 100, len(fails)))
        for s, key, a, b in fails[:15]:
            print("  %.0f%%  [%s] %s ↔ %s" % (s * 100, key[0], by_id[a].keyword, by_id[b].keyword))
        print("\nFAIL")
        return 1
    if errors:
        print("FAIL (렌더 실패)")
        return 1
    print("오류 0건 — PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
