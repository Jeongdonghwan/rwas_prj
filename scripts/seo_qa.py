# -*- coding: utf-8 -*-
"""SEO QA 게이트 — 규칙 위반 시 exit 1.

    python scripts/seo_qa.py            # 전체 검사
    python scripts/seo_qa.py --quiet    # 요약만

검사 항목
  · 타이틀 60자 이내 / 설명 40~160자 / 사이트 전체 중복 금지
  · H1 정확히 1개, 본문 최소 분량, img alt 누락 0, canonical 존재
  · 핵심 키워드(수원개인회생) 타이틀·설명 포함
  · 같은 유형 페이지 간 3-gram Jaccard 유사도
    (지역·직업명을 제거한 뒤 비교 — 이름만 치환한 복제를 잡기 위함)
"""
import re
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import quote

# 콘솔이 cp949여도 한글·기호가 깨지지 않게
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app
from app.config import REGION

# 핵심 키워드는 지역마다 다르다 — 하드코딩하면 다른 지역 사이트에서 전부 FAIL
CORE_KW = REGION["name"] + "개인회생"  # noqa: E402
from app.models import CaseType, Dong, Gu, Job, Post  # noqa: E402

TITLE_MAX = 60
DESC_MIN, DESC_MAX = 40, 160
BODY_MIN = 800          # 본문 공백 제외 최소 글자수
SIM_WARN, SIM_FAIL = 0.55, 0.70   # 이름 제거 후 3-gram Jaccard

QUIET = "--quiet" in sys.argv


def text_of(html, main_only=False):
    """main_only=True면 <main> 안쪽(고유 본문)만 — 헤더·푸터·CTA 같은 공통 보일러플레이트
    는 어느 사이트나 동일하므로 중복 판정 대상이 아니다. 유사도는 이 값으로 잰다."""
    if main_only:
        m = re.search(r"<main[^>]*>(.*?)</main>", html, re.S)
        t = m.group(1) if m else html
        # 사이드바(aside)는 페이지마다 같은 연락처 카드 → 본문에서 제외
        t = re.sub(r"<aside.*?</aside>", " ", t, flags=re.S)
    else:
        body = re.search(r"<body.*?</body>", html, re.S)
        t = body.group(0) if body else html
    t = re.sub(r"<script.*?</script>", " ", t, flags=re.S)
    t = re.sub(r"<style.*?</style>", " ", t, flags=re.S)
    t = re.sub(r"<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def grams(s, n=3):
    s = re.sub(r"\s+", "", s)
    return {s[i:i + n] for i in range(max(len(s) - n + 1, 0))}


def jaccard(a, b):
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def main():
    app = create_app()
    c = app.test_client()

    with app.app_context():
        pages = [
            ("고정", "메인", "/"),
            ("고정", "소개", "/about/"),
            ("고정", "개인회생", "/service/rehab/"),
            ("고정", "개인파산", "/service/bankruptcy/"),
            ("고정", "준비서류", "/service/docs/"),
            ("고정", "비용", "/service/cost/"),
            ("고정", "절차", "/process/"),
            ("고정", "FAQ", "/faq/"),
            ("고정", "상담신청", "/contact/"),
            ("허브", "사례목록", quote("/사례/")),
            ("허브", "지역허브", quote("/지역별-개인회생/")),
            ("허브", "직업허브", quote("/직업별-개인회생/")),
            ("허브", "상황허브", quote("/상황별-개인회생/")),
        ]
        pages += [("동", d.name, quote("/%s-개인회생/" % d.name)) for d in Dong.query.all()]
        pages += [("구", g.name, quote("/%s-개인회생/" % g.name)) for g in Gu.query.all()]
        pages += [("직업", j.name, quote("/%s-개인회생/" % j.slug_ko)) for j in Job.query.all()]
        pages += [("상황", x.name, quote("/%s-개인회생/" % x.slug_ko)) for x in CaseType.query.all()]
        pages += [("사례", p.title[:14], quote("/사례/%s/" % p.slug)) for p in Post.query.all()]

    errors, warns = [], []
    titles, descs = Counter(), Counter()
    bodies = {}   # (kind, name) -> 본문 텍스트

    for kind, name, url in pages:
        r = c.get(url)
        if r.status_code != 200:
            errors.append("%s/%s: HTTP %d" % (kind, name, r.status_code))
            continue
        h = r.get_data(as_text=True)

        t = re.search(r"<title>(.*?)</title>", h, re.S)
        d = re.search(r'<meta name="description" content="(.*?)">', h, re.S)
        title = t.group(1).strip() if t else ""
        desc = d.group(1).strip() if d else ""
        h1s = re.findall(r"<h1[^>]*>(.*?)</h1>", h, re.S)
        imgs = re.findall(r"<img [^>]*>", h)
        body = text_of(h)
        label = "%s/%s" % (kind, name)

        titles[title] += 1
        descs[desc] += 1
        bodies[(kind, name)] = text_of(h, main_only=True)

        if len(title) > TITLE_MAX:
            errors.append("%s: 타이틀 %d자(최대 %d)" % (label, len(title), TITLE_MAX))
        if not (DESC_MIN <= len(desc) <= DESC_MAX):
            errors.append("%s: 설명 %d자(%d~%d)" % (label, len(desc), DESC_MIN, DESC_MAX))
        if len(h1s) != 1:
            errors.append("%s: H1 %d개" % (label, len(h1s)))
        if not re.search(r'<link rel="canonical"', h):
            errors.append("%s: canonical 없음" % label)
        no_alt = [i for i in imgs if "alt=" not in i]
        if no_alt:
            errors.append("%s: alt 없는 img %d개" % (label, len(no_alt)))
        if CORE_KW not in title and CORE_KW not in desc:
            errors.append("%s: 핵심 키워드 없음" % label)
        if len(body.replace(" ", "")) < BODY_MIN:
            warns.append("%s: 본문 %d자(권장 %d 이상)"
                         % (label, len(body.replace(" ", "")), BODY_MIN))

    for t, n in titles.items():
        if n > 1:
            errors.append("타이틀 중복 %d회: %s" % (n, t[:50]))
    for d, n in descs.items():
        if n > 1:
            errors.append("설명 중복 %d회: %s" % (n, d[:50]))

    # ── 유사도: 같은 유형끼리, 고유명사를 지운 뒤 비교 ──
    sims = []
    for kind in ("동", "구", "직업", "상황"):
        items = [(nm, bd) for (k, nm), bd in bodies.items() if k == kind]
        prepped = []
        for nm, bd in items:
            stripped = bd.replace(nm, "")
            prepped.append((nm, grams(stripped)))
        for i in range(len(prepped)):
            for j in range(i + 1, len(prepped)):
                s = jaccard(prepped[i][1], prepped[j][1])
                sims.append((kind, prepped[i][0], prepped[j][0], s))

    sims.sort(key=lambda x: -x[3])
    for kind, a, b, s in sims:
        if s >= SIM_FAIL:
            errors.append("유사도 %.0f%% (%s: %s ↔ %s)" % (s * 100, kind, a, b))
        elif s >= SIM_WARN:
            warns.append("유사도 %.0f%% (%s: %s ↔ %s)" % (s * 100, kind, a, b))

    # ── 리포트 ──
    print("검사 페이지: %d개" % len(pages))
    if sims:
        by_kind = {}
        for kind, a, b, s in sims:
            by_kind.setdefault(kind, []).append(s)
        print("유형별 평균/최대 유사도(<main> 본문, 이름 제거 후):")
        for kind, vals in by_kind.items():
            print("  %-4s 평균 %.0f%% / 최대 %.0f%% (%d쌍)"
                  % (kind, sum(vals) / len(vals) * 100, max(vals) * 100, len(vals)))
        if not QUIET:
            print("가장 유사한 5쌍:")
            for kind, a, b, s in sims[:5]:
                print("  %.0f%%  %s: %s ↔ %s" % (s * 100, kind, a, b))

    if warns:
        print("\n경고 %d건:" % len(warns))
        for w in warns[:20]:
            print("  ·", w)
    if errors:
        print("\n오류 %d건:" % len(errors))
        for e in errors[:30]:
            print("  ✗", e)
        print("\nFAIL")
        return 1
    print("\n오류 0건 — PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
