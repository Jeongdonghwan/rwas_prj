from flask import Blueprint, render_template

from app.models import CaseType, Gu, Job, Post

bp = Blueprint("main", __name__)


@bp.route("/")
def index():
    gus = Gu.query.order_by(Gu.sort).all()
    jobs = Job.query.order_by(Job.sort).all()
    cases = CaseType.query.order_by(CaseType.sort).all()
    posts = (
        Post.query.filter_by(is_public=True)
        .order_by(Post.published_at.desc())
        .limit(4)
        .all()
    )
    return render_template("index.html", gus=gus, jobs=jobs, cases=cases, posts=posts)


@bp.route("/about/")
def about():
    return render_template("about.html")


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
    return render_template("process.html")


@bp.route("/faq/")
def faq():
    return render_template("faq.html")


@bp.route("/privacy/")
def privacy():
    return render_template("privacy.html")


@bp.route("/email-policy/")
def email_policy():
    return render_template("email_policy.html")
