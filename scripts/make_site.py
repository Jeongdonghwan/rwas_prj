# -*- coding: utf-8 -*-
"""지역 사이트 프로젝트를 만든다.

    python scripts/make_site.py ansan            # ../ansan_prj 생성
    python scripts/make_site.py ansan --force    # 이미 있으면 덮어쓴다

`scripts/site_data/<이름>.py`의 REGION·GU·DONG을 읽어서

    ../<이름>_prj/
        app/region.py      ← 통째로 새로 쓴다
        seed/gu.csv        ← 새로 쓴다
        seed/dong.csv      ← 새로 쓴다
        seed/keyword.csv   ← 비운다(생성 대상이라 복사하지 않는다)

를 만든다. 나머지 코드는 전부 원본 그대로다 — multi-site-plan.md §4-C.

**복사하지 않는 것**: .git(새 저장소여야 한다), instance/(로컬 DB),
seed/keyword.csv(지역마다 다시 만든다), app/static/uploads/(사례 이미지),
.env(키가 들어 있다), __pycache__, .qa_tmp.
"""
import argparse
import csv
import importlib
import shutil
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

SKIP_DIRS = {".git", "__pycache__", "instance", ".qa_tmp", "uploads", ".pytest_cache"}
SKIP_FILES = {".env", "keyword.csv", "snapshot.json"}


def _ignore(dirpath, names):
    out = []
    for n in names:
        if n in SKIP_DIRS or n in SKIP_FILES:
            out.append(n)
        elif n.endswith((".pyc", ".db")):
            out.append(n)
    return out


def write_region(dst, region):
    """app/region.py를 통째로 다시 쓴다. 설정이 한 파일에 모여 있어 가능한 방식이다."""
    lines = [
        "# -*- coding: utf-8 -*-",
        '"""지역 설정 — scripts/make_site.py가 생성했다.',
        "",
        "원본은 raws_prj(수원)이고 지역 데이터는 scripts/site_data/에 있다.",
        "이 파일과 seed/gu.csv·dong.csv만 지역마다 다르고 나머지 코드는 동일하다.",
        "전체 계획은 multi-site-plan.md.",
        '"""',
        "import os",
        "",
        "REGION = {",
    ]
    # 키를 손으로 나열하면 REGION에 필드를 더할 때마다 여기가 빠져 KeyError가 난다.
    # 데이터에 있는 것을 그대로 내보낸다(env로 덮는 두 개만 따로).
    for key, val in region.items():
        if key in ("site_salt", "site_offset"):
            continue
        lines.append("    %r: %r," % (key, val))
    lines += [
        "",
        "    # 사이트 구분자 — 같은 문장 풀을 쓰는 다른 지역 사이트와 겹치지 않게 한다.",
        "    # 값을 바꾸면 모든 키워드 페이지의 섹션 조합이 바뀐다(multi-site-plan.md §3).",
        '    "site_salt": os.environ.get("SITE_SALT", %r),' % region["site_salt"],
        '    "site_offset": int(os.environ.get("SITE_OFFSET") or %d),'
        % region["site_offset"],
        "}",
        "",
    ]
    (dst / "app" / "region.py").write_text("\n".join(lines), encoding="utf-8")


def write_seeds(dst, gu_rows, dong_rows):
    seed = dst / "seed"
    with open(seed / "gu.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["slug", "name", "intro_html",
                                          "court_note", "sort"])
        w.writeheader()
        w.writerows(gu_rows)

    rows = []
    for i, (gu, slug, name, legal, transit, feature, adj) in enumerate(dong_rows, 1):
        rows.append({
            "gu_slug": gu, "slug": slug, "name": name, "name_legal": legal,
            "transit_note": transit, "feature_note": feature,
            "adjacent_slugs": adj,
            # variant_set은 더 이상 선택에 쓰이지 않는다(해시 회전으로 대체).
            # 컬럼이 남아 있어 값만 채운다 — CLAUDE.md "Phase 3~5 구현 메모" 참고.
            "variant_set": "ABC"[i % 3],
            "sort": i,
        })
    # 도산레이는 지역 축이 시도 1단이라 동이 없다 — 헤더만 있는 CSV를 쓴다
    fields = ["gu_slug", "slug", "name", "name_legal", "transit_note",
              "feature_note", "adjacent_slugs", "variant_set", "sort"]
    with open(seed / "dong.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    return len(gu_rows), len(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("site", help="scripts/site_data/<이름>.py 의 이름")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--out", help="생성 경로 (기본: ../<이름>_prj)")
    args = ap.parse_args()

    mod = importlib.import_module("scripts.site_data.%s" % args.site)

    # 원본(수원)이 가진 키가 빠지면 복사본이 KeyError로 죽는다 — 여기서 먼저 잡는다
    from app.region import REGION as BASE
    missing = sorted(set(BASE) - set(mod.REGION))
    if missing:
        sys.exit("site_data/%s.py에 빠진 키: %s" % (args.site, ", ".join(missing)))
    dst = Path(args.out) if args.out else ROOT.parent / ("%s_prj" % args.site)

    if dst.exists():
        if not args.force:
            sys.exit("이미 있습니다: %s  (--force로 덮어쓰기)" % dst)
        shutil.rmtree(dst)

    shutil.copytree(ROOT, dst, ignore=_ignore)
    write_region(dst, mod.REGION)
    n_gu, n_dong = write_seeds(dst, mod.GU, mod.DONG)

    # 키워드는 지역마다 새로 만든다 — 빈 파일만 남겨 둔다
    (dst / "seed" / "keyword.csv").write_text("", encoding="utf-8")

    print("생성: %s" % dst)
    print("  지역   %s (%s)" % (mod.REGION["name"], mod.REGION["brand"]))
    print("  구 %d개 / 동 %d개" % (n_gu, n_dong))
    print("  salt=%r offset=%d" % (mod.REGION["site_salt"],
                                   mod.REGION["site_offset"]))
    print()
    print("다음 단계:")
    print("  cd %s" % dst)
    print("  python scripts/import_keywords.py")
    print("  FLASK_APP=run.py flask seed && FLASK_APP=run.py flask seed-keywords")


if __name__ == "__main__":
    main()
