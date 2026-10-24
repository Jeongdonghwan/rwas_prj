from flask import request, Blueprint, render_template

from app.models import CaseType, Gu, Job, Post

bp = Blueprint("main", __name__)


def _v0(name):
    """시안 0번 미리보기(?theme=0)면 팔레트 교체 이전 원본 템플릿. 확정 후 삭제."""
    t = request.args.get("theme") or request.cookies.get("lei_theme")
    return "_v0/" + name if t == "0" else name


@bp.route("/")
def index():
    gus = Gu.query.order_by(Gu.sort).all()
    jobs = Job.query.order_by(Job.sort).all()
    cases = CaseType.query.order_by(CaseType.sort).all()
    job_groups = []
    for j in jobs:
        if not job_groups or job_groups[-1][0] != j.category:
            job_groups.append((j.category, []))
        job_groups[-1][1].append(j)
    # kind 를 안 가리면 자동 칼럼이 사례 캐러셀에 섞여 /사례/<slug>/ 로 404 링크가 난다
    posts = (
        Post.query.filter_by(is_public=True, kind=Post.KIND_CASE)
        .order_by(Post.published_at.desc())
        .limit(4)
        .all()
    )
    columns = (
        Post.query.filter_by(is_public=True, kind=Post.KIND_COLUMN)
        .order_by(Post.published_at.desc())
        .limit(8)
        .all()
    )
    return render_template(
        _v0("index.html"),
        gus=gus,
        jobs=jobs,
        job_groups=job_groups,
        cases=cases,
        posts=posts,
        columns=columns,
    )


@bp.route("/about/")
def about():
    return render_template(_v0("about.html"))


@bp.route("/service/rehab/")
def service_rehab():
    return render_template("service/rehab.html")


@bp.route("/service/bankruptcy/")
def service_bankruptcy():
    return render_template("service/bankruptcy.html")


@bp.route("/service/docs/")
def service_docs():
    return render_template("service/docs.html")


@bp.route("/service/cost/")
def service_cost():
    return render_template("service/cost.html")


@bp.route("/process/")
def process():
    return render_template(_v0("process.html"))


@bp.route("/faq/")
def faq():
    return render_template("faq.html")


@bp.route("/privacy/")
def privacy():
    return render_template("privacy.html")


@bp.route("/email-policy/")
def email_policy():
    return render_template("email_policy.html")
