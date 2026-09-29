"""서브키워드 랜딩 페이지 — /{키워드 슬러그}/

예: /개인회생-신청자격/, /수원-개인회생-신청자격/, /개인파산-신청자격/
전체 설계는 keyword-pages-plan.md 참고.

**라우트 우선순위 주의**: 이 블루프린트의 `/<slug>/`는 가장 넓은 패턴이다.
고정 페이지(/about/)와 기존 한글 URL(/<name>-개인회생/)이 먼저 잡혀야 하므로
`create_app`에서 **가장 마지막에 등록**한다. scripts/check_routes.py로 확인할 수 있다.
"""

from flask import Blueprint, abort, render_template

from app import db
from app.keyword_render import build
from app.keyword_rules import SCHEMES
from app.models import Keyword
from app.scheme_facts import SCHEME_FACTS

bp = Blueprint("keyword", __name__)

RELATED_SCHEMES = 4   # 같은 키워드의 다른 제도 링크 수
RELATED_SAME_CAT = 6  # 같은 분류의 다른 키워드 링크 수


# ── 모아보기 허브 ──────────────────────────────────────────────────
# 12,000페이지가 서로만 링크하면 크롤러가 진입할 입구가 없다.
# /모아보기/ → 제도 → 분류 → 개별 페이지로 내려가는 경로를 만든다.
# URL에 '모아보기' 접두를 둔 이유: 키워드 슬러그와 충돌할 여지를 없애기 위함.

@bp.route("/모아보기/")
def hub():
    counts = dict(
        db.session.query(Keyword.scheme, db.func.count(Keyword.id))
        .filter(Keyword.is_public.is_(True))
        .group_by(Keyword.scheme)
        .all()
    )
    schemes = [
        {"code": code, "name": SCHEMES[code],
         "intro": SCHEME_FACTS[code]["intro"], "count": counts.get(code, 0)}
        for code in SCHEMES if counts.get(code)
    ]
    return render_template("keyword/hub.html", schemes=schemes)


@bp.route("/모아보기/<scheme>/")
def scheme_hub(scheme):
    if scheme not in SCHEMES:
        abort(404)
    rows = (
        db.session.query(Keyword.category, db.func.count(Keyword.id))
        .filter(Keyword.scheme == scheme, Keyword.is_public.is_(True))
        .group_by(Keyword.category)
        .order_by(Keyword.category)
        .all()
    )
    if not rows:
        abort(404)
    return render_template(
        "keyword/scheme_hub.html",
        scheme=scheme,
        scheme_name=SCHEMES[scheme],
        facts=SCHEME_FACTS[scheme],
        categories=[{"name": c, "count": n} for c, n in rows],
    )


@bp.route("/모아보기/<scheme>/<category>/")
def category_hub(scheme, category):
    if scheme not in SCHEMES:
        abort(404)
    rows = (
        Keyword.query.filter_by(scheme=scheme, category=category, is_public=True)
        .order_by(Keyword.region, Keyword.id)
        .all()
    )
    if not rows:
        abort(404)
    return render_template(
        "keyword/category_hub.html",
        scheme=scheme,
        scheme_name=SCHEMES[scheme],
        category=category,
        rows=rows,
    )


@bp.route("/<slug>/")
def page(slug):
    kw = Keyword.query.filter_by(slug_ko=slug, is_public=True).first()
    if not kw:
        abort(404)

    # 같은 키워드의 다른 제도 — 제도 간 회유를 만들어 색인에 유리하다
    others = (
        Keyword.query.filter(
            Keyword.source_no == kw.source_no,
            Keyword.id != kw.id,
            Keyword.region == kw.region,
            Keyword.is_public.is_(True),
        )
        .limit(RELATED_SCHEMES)
        .all()
    )
    # 같은 분류의 다른 키워드 — 12,000페이지가 고아가 되지 않게
    same_cat = (
        Keyword.query.filter(
            Keyword.category == kw.category,
            Keyword.scheme == kw.scheme,
            Keyword.region == kw.region,
            Keyword.id != kw.id,
            Keyword.is_public.is_(True),
        )
        .order_by(Keyword.id)
        .offset(kw.id % 17)
        .limit(RELATED_SAME_CAT)
        .all()
    )

    return render_template(
        "keyword/detail.html",
        page=build(kw),
        others=others,
        same_cat=same_cat,
    )
