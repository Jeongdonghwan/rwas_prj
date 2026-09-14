"""구 영문 URL(/job/..., /case-type/...) — 한글 URL로 301 리다이렉트만 담당."""

from flask import Blueprint, redirect, url_for

from app.models import CaseType, Job

bp = Blueprint("job", __name__)


@bp.route("/job/")
def hub():
    return redirect(url_for("ko.job_hub"), 301)


@bp.route("/job/<slug>/")
def detail(slug):
    job = Job.query.filter_by(slug=slug).first_or_404()
    return redirect(url_for("ko.page", name=job.slug_ko), 301)


@bp.route("/case-type/")
def case_hub():
    return redirect(url_for("ko.case_hub"), 301)


@bp.route("/case-type/<slug>/")
def case_detail(slug):
    case = CaseType.query.filter_by(slug=slug).first_or_404()
    return redirect(url_for("ko.page", name=case.slug_ko), 301)
