import os
import re
import uuid
from datetime import date, datetime, timedelta, timezone
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
from app.models import Inquiry, Keyword, Post

bp = Blueprint("admin", __name__, url_prefix="/admin")

STATUSES = ("new", "contacted", "done", "spam")
STATUS_LABEL = {"new": "신규", "contacted": "연락함", "done": "완료", "spam": "스팸"}
STATUS_ITEMS = [(k, STATUS_LABEL[k]) for k in STATUSES]
PER_PAGE = 50


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
    return redirect(url_for("admin.dashboard"))


@bp.route("/dashboard")
@requires_auth
def dashboard():
    today_start = datetime.combine(date.today(), datetime.min.time())
    stats = {
        "total": Inquiry.query.count(),
        "today": Inquiry.query.filter(Inquiry.created_at >= today_start).count(),
        "new": Inquiry.query.filter_by(status="new").count(),
        "posts": Post.query.filter_by(is_public=True).count(),
        "keywords": Keyword.query.filter_by(is_public=True).count(),
        "keywords_hidden": Keyword.query.filter_by(is_public=False).count(),
    }
    recent = Inquiry.query.order_by(Inquiry.created_at.desc()).limit(8).all()
    posts = Post.query.order_by(Post.published_at.desc()).limit(5).all()
    return render_template(
        "admin/dashboard.html",
        nav="dash",
        s=stats,
        recent=recent,
        posts=posts,
        status_label=STATUS_LABEL,
        today=date.today().strftime("%Y년 %m월 %d일"),
    )


def _inquiry_query(status, q):
    query = Inquiry.query
    if status in STATUSES:
        query = query.filter_by(status=status)
    if q:
        like = f"%{q}%"
        query = query.filter(db.or_(Inquiry.name.like(like), Inquiry.phone.like(like)))
    return query.order_by(Inquiry.created_at.desc())


@bp.route("/inquiries")
@requires_auth
def inquiries():
    status = request.args.get("status")
    q = (request.args.get("q") or "").strip()
    page = max(request.args.get("page", 1, type=int), 1)

    query = _inquiry_query(status, q)
    total = query.count()
    pages = max((total + PER_PAGE - 1) // PER_PAGE, 1)
    rows = query.offset((page - 1) * PER_PAGE).limit(PER_PAGE).all()

    counts = {"all": Inquiry.query.count()}
    for key in STATUSES:
        counts[key] = Inquiry.query.filter_by(status=key).count()

    return render_template(
        "admin/inquiries.html",
        nav="inq",
        rows=rows,
        total=total,
        page=page,
        pages=pages,
        status=status if status in STATUSES else None,
        q=q,
        counts=counts,
        status_items=STATUS_ITEMS,
        status_label=STATUS_LABEL,
    )


@bp.route("/inquiries.csv")
@requires_auth
def inquiries_csv():
    status = request.args.get("status")
    q = (request.args.get("q") or "").strip()
    rows = _inquiry_query(status, q).all()

    def cell(v):
        v = str(v if v is not None else "")
        return '"' + v.replace('"', '""') + '"'

    lines = ["접수일시,이름,연락처,채무액,지역,유입페이지,상태,메모"]
    for r in rows:
        lines.append(",".join([
            cell(r.created_at.strftime("%Y-%m-%d %H:%M")),
            cell(r.name), cell(r.phone), cell(r.debt_range), cell(r.area_text),
            cell(r.source_path), cell(STATUS_LABEL.get(r.status, r.status)), cell(r.memo),
        ]))
    body = "\ufeff" + "\n".join(lines)  # 엑셀 한글 대응 BOM
    fname = "inquiries_%s.csv" % date.today().strftime("%Y%m%d")
    return Response(
        body,
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=%s" % fname},
    )


@bp.route("/inquiries/<int:inquiry_id>/update", methods=["POST"])
@requires_auth
def inquiry_update(inquiry_id):
    row = db.session.get(Inquiry, inquiry_id)
    if row:
        status = request.form.get("status")
        if status in STATUSES:
            row.status = status
        row.memo = (request.form.get("memo") or "").strip()[:2000]
        db.session.commit()
    return redirect(request.referrer or url_for("admin.inquiries"))


@bp.route("/inquiries/<int:inquiry_id>/delete", methods=["POST"])
@requires_auth
def inquiry_delete(inquiry_id):
    row = db.session.get(Inquiry, inquiry_id)
    if row:
        db.session.delete(row)
        db.session.commit()
    return redirect(request.referrer or url_for("admin.inquiries"))


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
    public_count = sum(1 for p in posts if p.is_public)
    return render_template(
        "admin/cases.html", nav="case", posts=posts, public_count=public_count
    )


@bp.route("/cases/new", methods=["GET", "POST"])
@requires_auth
def case_new():
    if request.method == "POST":
        post = Post()
        fill_post(post)
        if not post.title or not post.body_html.strip():
            return render_template("admin/case_form.html", nav="case", post=post, error="제목과 본문을 입력하세요.")
        db.session.add(post)
        db.session.commit()
        return redirect(url_for("admin.cases"))
    return render_template("admin/case_form.html", nav="case", post=None, error=None)


@bp.route("/cases/<int:post_id>/edit", methods=["GET", "POST"])
@requires_auth
def case_edit(post_id):
    post = db.session.get(Post, post_id)
    if not post:
        return redirect(url_for("admin.cases"))
    if request.method == "POST":
        fill_post(post)
        if not post.title or not post.body_html.strip():
            return render_template("admin/case_form.html", nav="case", post=post, error="제목과 본문을 입력하세요.")
        db.session.commit()
        return redirect(url_for("admin.cases"))
    return render_template("admin/case_form.html", nav="case", post=post, error=None)


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


# ── 서브키워드 세트 관리 ────────────────────────────────────────────
# 12,000페이지를 한 번에 발행하기로 했으므로, 문제가 생겼을 때 세트 단위로
# 즉시 내릴 수 있어야 한다. is_public=False면 페이지는 404, 사이트맵에서도 빠진다.

@bp.route("/keywords")
@requires_auth
def keywords():
    from app.keyword_rules import SCHEMES
    from app.models import Keyword

    rows = []
    for code, name in SCHEMES.items():
        for region in ("", "수원"):
            q = Keyword.query.filter_by(scheme=code, region=region)
            total = q.count()
            if not total:
                continue
            rows.append({
                "scheme": code,
                "name": name,
                "region": region,
                "total": total,
                "public": q.filter_by(is_public=True).count(),
                "fix": q.filter_by(needs_correction=True).count(),
            })
    return render_template(
        "admin/keywords.html", nav="kw", rows=rows,
        total=sum(r["total"] for r in rows),
        public=sum(r["public"] for r in rows),
    )


@bp.route("/keywords/toggle", methods=["POST"])
@requires_auth
def keywords_toggle():
    from app.models import Keyword

    scheme = request.form.get("scheme")
    region = request.form.get("region", "")
    publish = request.form.get("publish") == "1"
    q = Keyword.query.filter_by(scheme=scheme, region=region)
    n = q.update({Keyword.is_public: publish}, synchronize_session=False)
    db.session.commit()
    current_app.logger.info("keyword set %s/%s → public=%s (%d행)",
                            scheme, region or "-", publish, n)
    return redirect(url_for("admin.keywords"))
