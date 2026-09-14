"""한글 URL 라우트 — /{이름}-개인회생/ 형식이 정식 URL.

예: /매탄동-개인회생/, /장안구-개인회생/, /직장인-개인회생/, /도박빚-개인회생/
허브: /지역별-개인회생/, /직업별-개인회생/, /상황별-개인회생/
기존 영문 URL(/area/... /job/... /case-type/...)은 area.py/job.py에서 여기로 301.
"""

from flask import Blueprint, abort, render_template

from app.content import get_block, pick_faqs
from app.models import CaseType, Dong, Gu, Job

bp = Blueprint("ko", __name__)

BLOCK_KEYS = ("rehab_core", "after_apply", "why_us")


def _blocks(variant):
    return {k: get_block(k, variant) for k in BLOCK_KEYS}


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


def _render_gu(gu):
    faqs = pick_faqs("gu", "A", 3, gu=gu.name)
    return render_template("area/gu.html", gu=gu, faqs=faqs)


def _render_dong(dong):
    gu = dong.gu
    v = dong.variant_set
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
    )


def _render_job(job):
    v = job.variant_set
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
    )


def _render_case(case):
    v = case.variant_set
    faqs = pick_faqs("case", v, 4, name=case.name)
    related = (
        CaseType.query.filter(CaseType.id != case.id)
        .order_by(CaseType.sort)
        .limit(4)
        .all()
    )
    return render_template(
        "casetype/detail.html", case=case, blocks=_blocks(v), faqs=faqs, related=related
    )
