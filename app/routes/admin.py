import os
import re
import uuid
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path

from flask import (
    Blueprint,
    Response,
    current_app,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from PIL import Image, ImageOps

from app import db
from app.models import Inquiry, Post

bp = Blueprint("admin", __name__, url_prefix="/admin")

STATUSES = ("new", "contacted", "done", "spam")


def check_auth(auth):
    user = os.environ.get("ADMIN_USER", "admin")
    pw = os.environ.get("ADMIN_PASSWORD", "admin")
    return auth and auth.username == user and auth.password == pw


def requires_auth(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not check_auth(request.authorization):
            return Response(
                "로그인이 필요합니다.",
                401,
                {"WWW-Authenticate": 'Basic realm="admin"'},
            )
        return f(*args, **kwargs)

    return wrapper


@bp.route("/")
@requires_auth
def home():
    return redirect(url_for("admin.inquiries"))


@bp.route("/inquiries")
@requires_auth
def inquiries():
    status = request.args.get("status")
    q = Inquiry.query.order_by(Inquiry.created_at.desc())
    if status in STATUSES:
        q = q.filter_by(status=status)
    rows = q.limit(200).all()

    def esc(s):
        return (
            str(s or "")
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )

    tabs = " | ".join(
        f'<a href="?status={s}">{s}</a>' for s in STATUSES
    )
    trs = "".join(
        f"<tr><td>{r.id}</td><td>{r.created_at:%Y-%m-%d %H:%M}</td>"
        f"<td>{esc(r.name)}</td><td>{esc(r.phone)}</td><td>{esc(r.debt_range)}</td>"
        f"<td>{esc(r.area_text)}</td><td>{esc(r.source_path)}</td><td>{esc(r.status)}</td>"
        f'<td><form method="post" action="{url_for("admin.set_status", inquiry_id=r.id)}">'
        + "".join(
            f'<button name="status" value="{s}">{s}</button>' for s in STATUSES
        )
        + "</form></td></tr>"
        for r in rows
    )
    return (
        "<!doctype html><meta charset=utf-8><title>상담 접수</title>"
        "<style>body{font-family:sans-serif;padding:20px}table{border-collapse:collapse;width:100%}"
        "th,td{border:1px solid #ccc;padding:6px 8px;font-size:14px}button{margin-right:4px}</style>"
        f'<h1>상담 접수 목록</h1><p><a href="{url_for("admin.cases")}">→ 진행 사례 관리</a></p>'
        f'<p><a href="?">전체</a> | {tabs}</p>'
        "<table><tr><th>ID</th><th>접수일시</th><th>이름</th><th>연락처</th><th>채무액</th>"
        f"<th>지역</th><th>유입 페이지</th><th>상태</th><th>변경</th></tr>{trs}</table>"
    )


@bp.route("/inquiries/<int:inquiry_id>/status", methods=["POST"])
@requires_auth
def set_status(inquiry_id):
    status = request.form.get("status")
    if status in STATUSES:
        row = db.session.get(Inquiry, inquiry_id) or None
        if row:
            row.status = status
            db.session.commit()
    return redirect(url_for("admin.inquiries"))


# ---------- 진행 사례 게시판 ----------

def slugify(title):
    s = re.sub(r"[^\w가-힣\- ]", "", title).strip().lower()
    s = re.sub(r"[\s_]+", "-", s)
    return s[:180] or uuid.uuid4().hex[:8]


def unique_slug(title, post_id=None):
    base = slugify(title)
    slug, n = base, 2
    while True:
        q = Post.query.filter_by(slug=slug)
        if post_id:
            q = q.filter(Post.id != post_id)
        if not q.first():
            return slug
        slug = f"{base}-{n}"
        n += 1


def upload_dir():
    now = datetime.now()
    rel = Path("uploads") / f"{now:%Y}" / f"{now:%m}"
    absdir = Path(current_app.static_folder) / rel
    absdir.mkdir(parents=True, exist_ok=True)
    return rel, absdir


def save_image(file_storage, max_w):
    img = ImageOps.exif_transpose(Image.open(file_storage)).convert("RGB")
    if img.width > max_w:
        img.thumbnail((max_w, max_w * 3), Image.LANCZOS)
    rel, absdir = upload_dir()
    name = uuid.uuid4().hex[:12] + ".webp"
    img.save(absdir / name, "WEBP", quality=82)
    return "/static/" + (rel / name).as_posix()


def strip_tags(html):
    return re.sub(r"<[^>]+>", " ", html or "")


def fill_post(post):
    post.title = (request.form.get("title") or "").strip()[:200]
    post.body_html = request.form.get("body_html") or ""
    excerpt = (request.form.get("excerpt") or "").strip()
    if not excerpt:
        excerpt = re.sub(r"\s+", " ", strip_tags(post.body_html)).strip()[:120]
    post.excerpt = excerpt[:300]
    post.thumb_alt = (request.form.get("thumb_alt") or post.title)[:200]
    post.is_public = bool(request.form.get("is_public"))
    pub = request.form.get("published_at")
    if pub:
        try:
            post.published_at = datetime.strptime(pub, "%Y-%m-%d")
        except ValueError:
            pass
    thumb = request.files.get("thumb")
    if thumb and thumb.filename:
        post.thumb_path = save_image(thumb, 960)
    post.slug = unique_slug(post.title, post.id)


@bp.route("/cases")
@requires_auth
def cases():
    posts = Post.query.order_by(Post.published_at.desc()).all()
    return render_template("admin/cases.html", posts=posts)


@bp.route("/cases/new", methods=["GET", "POST"])
@requires_auth
def case_new():
    if request.method == "POST":
        post = Post()
        fill_post(post)
        if not post.title or not post.body_html.strip():
            return render_template("admin/case_form.html", post=post, error="제목과 본문을 입력하세요.")
        db.session.add(post)
        db.session.commit()
        return redirect(url_for("admin.cases"))
    return render_template("admin/case_form.html", post=None, error=None)


@bp.route("/cases/<int:post_id>/edit", methods=["GET", "POST"])
@requires_auth
def case_edit(post_id):
    post = db.session.get(Post, post_id)
    if not post:
        return redirect(url_for("admin.cases"))
    if request.method == "POST":
        fill_post(post)
        if not post.title or not post.body_html.strip():
            return render_template("admin/case_form.html", post=post, error="제목과 본문을 입력하세요.")
        db.session.commit()
        return redirect(url_for("admin.cases"))
    return render_template("admin/case_form.html", post=post, error=None)


@bp.route("/cases/<int:post_id>/delete", methods=["POST"])
@requires_auth
def case_delete(post_id):
    post = db.session.get(Post, post_id)
    if post:
        db.session.delete(post)
        db.session.commit()
    return redirect(url_for("admin.cases"))


@bp.route("/cases/<int:post_id>/toggle", methods=["POST"])
@requires_auth
def case_toggle(post_id):
    post = db.session.get(Post, post_id)
    if post:
        post.is_public = not post.is_public
        db.session.commit()
    return redirect(url_for("admin.cases"))


@bp.route("/upload", methods=["POST"])
@requires_auth
def upload():
    f = request.files.get("image")
    if not f or not f.filename:
        return jsonify({"error": "no file"}), 400
    try:
        url = save_image(f, 1400)
    except Exception:
        return jsonify({"error": "invalid image"}), 400
    return jsonify({"url": url})
