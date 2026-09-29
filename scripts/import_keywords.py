# -*- coding: utf-8 -*-
"""서브키워드 xlsx → seed/keyword.csv

    python scripts/import_keywords.py [xlsx경로]

원본 2,000개(전부 '개인회생' 포함)를 아래 조합으로 펼친다.

    개인회생          2,000   지역 없음
    수원 개인회생      2,000   지역 접두
    개인파산          2,000
    신용회복          2,000
    워크아웃          2,000
    채무조정          2,000
    ----------------------
    합계             12,000

각 행에 `needs_correction`을 세워, 제도 치환으로 말이 안 되는 키워드
(예: '개인파산 변제금')는 본문 최상단에 교정 문단을 넣도록 표시한다.
판정 규칙은 app/keyword_rules.py.
"""
import csv
import re
import sys
from collections import Counter
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.keyword_rules import (  # noqa: E402
    SCHEMES, correction_terms, needs_correction, to_scheme,
)

DEFAULT_XLSX = (Path.home() / "Documents" / "카카오톡 받은 파일"
                / "개인회생_서브키워드_2000개.xlsx")
OUT = ROOT / "seed" / "keyword.csv"

# (제도, 지역) 조합 — 지역은 개인회생에만 붙인다(사용자 결정)
COMBOS = [
    ("rehab", ""),
    ("rehab", "수원"),
    ("bankruptcy", ""),
    ("credit", ""),
    ("workout", ""),
    ("adjust", ""),
]


def slugify(text):
    """URL 슬러그: 공백 → '-', 그 외 기호 제거. 한글은 그대로 둔다."""
    s = re.sub(r"[·/()\[\],]", " ", text)
    s = re.sub(r"\s+", "-", s.strip())
    return s.strip("-")


def load(xlsx):
    import openpyxl
    ws = openpyxl.load_workbook(xlsx, data_only=True).active
    rows = []
    for r in ws.iter_rows(min_row=2, values_only=True):
        if not r[1]:
            continue
        rows.append({
            "no": r[0],
            "keyword": str(r[1]).strip(),
            "category": (str(r[2]).strip() if r[2] else ""),
            "intent": (str(r[3]).strip() if r[3] else ""),
        })
    return rows


def main():
    xlsx = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_XLSX
    if not xlsx.exists():
        sys.exit("원본 파일을 찾을 수 없습니다: %s" % xlsx)

    base = load(xlsx)
    print("원본 키워드 %d개 로드" % len(base))

    out, seen, dup, skipped = [], set(), 0, 0
    for scheme, region in COMBOS:
        for r in base:
            kw = to_scheme(r["keyword"], scheme)
            # 원본에 이미 대상 제도명이 들어 있으면 치환이 겹친다.
            # 예) "개인회생 개인파산 차이" → "개인파산 개인파산 차이"
            # 원본(개인회생) 페이지가 같은 주제를 이미 다루므로 건너뛴다.
            if any(kw.count(n) > 1 for n in SCHEMES.values()):
                skipped += 1
                continue
            if region:
                kw = "%s %s" % (region, kw)
            slug = slugify(kw)
            if slug in seen:
                dup += 1
                continue
            seen.add(slug)
            out.append({
                "slug_ko": slug,
                "keyword": kw,
                "scheme": scheme,
                "region": region,
                "category": r["category"],
                "intent": r["intent"],
                "needs_correction": int(needs_correction(r["keyword"], scheme)),
                "correction_terms": ";".join(correction_terms(r["keyword"], scheme)),
                "source_no": r["no"],
            })

    OUT.parent.mkdir(exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
        w.writeheader()
        w.writerows(out)

    print("생성: %s" % OUT)
    print("총 %d행 (슬러그 중복 %d건, 제도명 중복으로 제외 %d건)" % (len(out), dup, skipped))
    print()
    by = Counter((o["scheme"], o["region"]) for o in out)
    for (s, rg), n in by.items():
        print("  %-11s %-3s %5d" % (SCHEMES[s], rg or "-", n))
    need = sum(o["needs_correction"] for o in out)
    print("\n교정 문단이 필요한 페이지: %d개 (%.0f%%)" % (need, need / len(out) * 100))
    for s in SCHEMES:
        n = sum(o["needs_correction"] for o in out if o["scheme"] == s)
        if n:
            print("  %-11s %5d" % (SCHEMES[s], n))
    print("\n분류 %d종 · 검색의도 %d종"
          % (len({o["category"] for o in out}), len({o["intent"] for o in out})))


if __name__ == "__main__":
    main()
