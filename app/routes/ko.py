"""한글 URL 라우트 — /{이름}-개인회생/ 형식이 정식 URL.

예: /매탄동-개인회생/, /장안구-개인회생/, /직장인-개인회생/, /도박빚-개인회생/
허브: /지역별-개인회생/, /직업별-개인회생/, /상황별-개인회생/
기존 영문 URL(/area/... /job/... /case-type/...)은 area.py/job.py에서 여기로 301.
"""

from flask import Blueprint, abort, render_template

from app import db

from app.content import get_block, pick_faqs
from app.variants import POOLS

# 가장 작은 문장 풀의 크기. 구 개수가 이보다 많으면 rank 배분이 무의미해진다.
VARIANT_COUNT = min(len(v) for v in POOLS.values())
from app.models import CaseType, Dong, Gu, Job

bp = Blueprint("ko", __name__)

BLOCK_KEYS = ("rehab_core", "after_apply", "why_us")


def _blocks(seed):
    """seed(엔티티 이름)로 블록을 해시 선택 — 키당 6종이면 216가지 본문 조합."""
    return {k: get_block(k, seed) for k in BLOCK_KEYS}


@bp.route("/지역별-개인회생/")
def area_hub():
    gus = Gu.query.order_by(Gu.sort).all()
    return render_template("area/hub.html", gus=gus)


@bp.route("/직업별-개인회생/")
def job_hub():
    jobs = Job.query.order_by(Job.sort).all()
    categories = []
    for j in jobs:
        if not categories or categories[-1][0] != j.category:
            categories.append((j.category, []))
        categories[-1][1].append(j)
    return render_template("job/hub.html", categories=categories)


@bp.route("/상황별-개인회생/")
def case_hub():
    cases = CaseType.query.order_by(CaseType.sort).all()
    return render_template("casetype/hub.html", cases=cases)


@bp.route("/<name>-개인회생/")
def page(name):
    gu = Gu.query.filter_by(name=name).first()
    if gu:
        return _render_gu(gu)
    dong = Dong.query.filter_by(name=name).first()
    if dong:
        return _render_dong(dong)
    job = Job.query.filter_by(slug_ko=name).first()
    if job:
        return _render_job(job)
    case = CaseType.query.filter_by(slug_ko=name).first()
    if case:
        return _render_case(case)
    abort(404)


def _related_columns(terms, limit=20):
    """키워드에 terms 중 하나가 들어간 공개 칼럼. 앞 term 일수록 우선(동 > 구), 그 안에선 최신순."""
    from app.models import ColumnKeyword, Post
    rows = (db.session.query(Post, ColumnKeyword.keyword)
            .join(ColumnKeyword, ColumnKeyword.post_id == Post.id)
            .filter(Post.is_public.is_(True), Post.kind == Post.KIND_COLUMN)
            .order_by(Post.published_at.desc()).all())
    out, seen = [], set()
    for t in terms:
        for post, kw in rows:
            if post.id not in seen and t and t in kw:
                out.append(post)
                seen.add(post.id)
    return out[:limit]


def _media(name, terms, siblings):
    """페이지 전용 OG 카드 + 관련 칼럼 + ItemList 항목.

    ItemList 는 **화면에 실제로 보이는 것만** 넣는다(관련 칼럼 섹션 + 하단 링크 목록).
    이미지는 칼럼 썸네일, 형제 페이지는 그 페이지의 OG 카드 — 로고·공통 og.jpg 는 절대 쓰지 않는다
    (네이버 캐러셀 심사 탈락 사유). siblings = [(표시명, url 이름)].
    """
    from flask import url_for
    from app.config import SITE_DEFAULTS
    from app.thumbs import page_og
    base = SITE_DEFAULTS["base_url"]
    try:
        og = page_og("%s 개인회생" % name)
    except Exception:          # 이미지 실패로 페이지가 죽으면 안 된다
        og = None
    cols = _related_columns(terms)
    items = [{"name": c.title, "url": base + url_for("board.column_view", slug=c.slug),
              "image": (base + c.thumb_path) if c.thumb_path else None, "desc": c.excerpt}
             for c in cols]
    for label, key in siblings:
        try:
            img = base + page_og("%s 개인회생" % key[0])
        except Exception:
            img = None
        items.append({"name": label, "url": base + url_for("ko.page", name=key[1]), "image": img})
    return {"og_image": (base + og) if og else None, "related_cols": cols,
            "ld_items": items[:20], "ld_name": "%s 개인회생 관련 안내" % name}


def _render_gu(gu):
    faqs = pick_faqs("gu", gu.name, 3, gu=gu.name)
    # 구가 몇 개 안 되면 해시로는 섹션이 우연히 겹친다 → 순번으로 라틴 방진 배분.
    #
    # **개수가 변형 수를 넘으면 rank를 쓰면 안 된다.** rank가 같은 페이지끼리
    # 전부 같은 문장을 쓰게 된다. 도산레이는 시도가 17개인데 변형이 4종이라
    # 그대로 넘겼더니 시도 페이지가 서로 93% 같아졌다(실측). 그 경우 해시로 돌린다.
    order = [g.id for g in Gu.query.order_by(Gu.sort).all()]
    rank = order.index(gu.id) if gu.id in order else 0
    if len(order) > VARIANT_COUNT:
        rank = None
    return render_template(
        "area/gu.html",
        gu=gu,
        faqs=faqs,
        seed=gu.name,
        blocks=_blocks(gu.name),
        lf_rank=rank,
        **_media(gu.name, [gu.name] + [d.name for d in gu.dongs],
                 [("%s 개인회생" % d.name, (d.name, d.name)) for d in gu.dongs]),
    )


def _render_dong(dong):
    gu = dong.gu
    v = dong.name
    concerns = pick_faqs("dong", v, 4, kind="concern", dong=dong.name, gu=gu.name)
    faqs = pick_faqs("dong", v, 5, dong=dong.name, gu=gu.name)
    adjacent = (
        Dong.query.filter(
            Dong.gu_id == gu.id, Dong.slug.in_(dong.adjacent_slugs or [])
        ).all()
        if dong.adjacent_slugs
        else []
    )
    jobs = Job.query.order_by(Job.sort).all()
    cross_jobs = (
        [jobs[(dong.id + i * 5) % len(jobs)] for i in range(3)] if jobs else []
    )
    return render_template(
        "area/dong.html",
        gu=gu,
        dong=dong,
        blocks=_blocks(v),
        concerns=concerns,
        faqs=faqs,
        adjacent=adjacent,
        cross_jobs=cross_jobs,
        seed=v,
        **_media(dong.name, [dong.name, gu.name],
                 [("%s 개인회생" % a.name, (a.name, a.name)) for a in adjacent]
                 + [("%s 개인회생 안내" % gu.name, (gu.name, gu.name))]
                 + [("%s 개인회생" % j.name, (j.name, j.slug_ko)) for j in cross_jobs]),
    )


def _render_job(job):
    v = job.name
    concerns = pick_faqs("job", v, 4, kind="concern", job=job.name)
    faqs = pick_faqs("job", v, 5, job=job.name)
    related = (
        Job.query.filter(Job.category == job.category, Job.id != job.id)
        .order_by(Job.sort)
        .limit(3)
        .all()
    )
    if len(related) < 3:
        related += (
            Job.query.filter(Job.category != job.category, Job.id != job.id)
            .order_by(Job.sort)
            .limit(3 - len(related))
            .all()
        )
    return render_template(
        "job/detail.html",
        job=job,
        blocks=_blocks(v),
        concerns=concerns,
        faqs=faqs,
        related=related,
        seed=v,
        **_media(job.name, [job.name],
                 [("%s 개인회생" % r.name, (r.name, r.slug_ko)) for r in related]),
    )


def _render_case(case):
    v = case.name
    faqs = pick_faqs("case", v, 4, name=case.name)
    related = (
        CaseType.query.filter(CaseType.id != case.id)
        .order_by(CaseType.sort)
        .limit(4)
        .all()
    )
    return render_template(
        "casetype/detail.html",
        case=case,
        blocks=_blocks(v),
        faqs=faqs,
        related=related,
        seed=v,
        **_media(case.name, [case.name],
                 [("%s 개인회생" % r.name, (r.name, r.slug_ko)) for r in related]),
    )
