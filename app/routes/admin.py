import os
import re
import uuid
import time
from datetime import date, datetime, timedelta, timezone
from functools import wraps
from pathlib import Path

from flask import (
    Blueprint,
    Response,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from PIL import Image, ImageOps

from app import db
from app.models import AdminUser, Inquiry, Keyword, Post

bp = Blueprint("admin", __name__, url_prefix="/admin")

STATUSES = ("new", "contacted", "done", "spam")
STATUS_LABEL = {"new": "신규", "contacted": "연락함", "done": "완료", "spam": "스팸"}
STATUS_ITEMS = [(k, STATUS_LABEL[k]) for k in STATUSES]
PER_PAGE = 50


# ── 로그인 ──────────────────────────────────────────────────────────
# 예전에는 HTTP Basic + 환경변수였다. 로그아웃이 안 되고 비밀번호를 바꾸려면
# 서버 .env를 고쳐야 했다. 지금은 세션 로그인 + DB 계정(AdminUser)이다.

LOGIN_WINDOW = 600      # 초
LOGIN_MAX_TRY = 10      # 이 횟수를 넘기면 창이 지날 때까지 막는다
_attempts = {}          # {ip: [실패 시각, ...]} — 단일 프로세스 기준 간이 차단


def _client_ip():
    fwd = request.headers.get("X-Forwarded-For", "")
    return (fwd.split(",")[0].strip() if fwd else request.remote_addr) or "?"


def _too_many(ip):
    now = time.time()
    tries = [t for t in _attempts.get(ip, []) if now - t < LOGIN_WINDOW]
    _attempts[ip] = tries
    return len(tries) >= LOGIN_MAX_TRY


def _note_fail(ip):
    _attempts.setdefault(ip, []).append(time.time())


def current_admin():
    uid = session.get("admin_id")
    if not uid:
        return None
    user = db.session.get(AdminUser, uid)
    return user if (user and user.is_active) else None


def requires_auth(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        user = current_admin()
        if not user:
            session.pop("admin_id", None)
            # full_path는 쿼리가 없어도 끝에 "?"를 붙인다 → 그대로 두면
            # 로그인 후 "/admin/keywords?"로 돌아가 쿼리 파싱이 어색해진다.
            nxt = request.full_path.rstrip("?") if request.method == "GET" else None
            return redirect(url_for("admin.login", next=nxt))
        # 초기 비밀번호를 쓰는 동안에는 변경 화면 밖으로 못 나간다
        if user.must_change and request.endpoint not in (
            "admin.account", "admin.logout", "admin.password",
        ):
            return redirect(url_for("admin.account"))
        return f(*args, **kwargs)

    return wrapper


def ensure_bootstrap_admin():
    """계정이 하나도 없으면 환경변수(기본 admin/admin)로 하나 만든다.

    기본값을 그대로 쓰면 `must_change`가 서서 로그인 직후 비밀번호 변경을 강제한다.
    """
    if AdminUser.query.count():
        return
    uid = os.environ.get("ADMIN_USER") or "admin"
    pw = os.environ.get("ADMIN_PASSWORD") or "admin"
    u = AdminUser(username=uid, name="관리자", must_change=(pw in ("admin", "1234", "change-me")))
    u.set_password(pw)
    db.session.add(u)
    db.session.commit()


@bp.app_context_processor
def _inject_admin():
    """어드민 템플릿에서 로그인 사용자를 쓸 수 있게 한다(헤더 표시용)."""
    try:
        return {"me": current_admin()} if request.blueprint == "admin" else {}
    except Exception:
        return {}


@bp.route("/login", methods=["GET", "POST"])
def login():
    ensure_bootstrap_admin()
    if current_admin():
        return redirect(url_for("admin.dashboard"))

    error = None
    if request.method == "POST":
        ip = _client_ip()
        if _too_many(ip):
            error = "로그인 시도가 너무 많습니다. 잠시 후 다시 시도해 주세요."
        else:
            uid = (request.form.get("username") or "").strip()
            pw = request.form.get("password") or ""
            user = AdminUser.query.filter_by(username=uid, is_active=True).first()
            if user and user.check_password(pw):
                session.clear()
                session["admin_id"] = user.id
                session.permanent = bool(request.form.get("remember"))
                # 다른 테이블(created_at)과 같은 UTC 기준으로 둔다 — 섞으면
                # 목록 정렬·비교가 9시간씩 어긋난다. 표시할 때 KST로 돌린다.
                user.last_login_at = datetime.now(timezone.utc)
                db.session.commit()
                nxt = request.args.get("next") or ""
                # 열린 리다이렉트 방지 — 내부 경로만 허용
                if not nxt.startswith("/") or nxt.startswith("//"):
                    nxt = url_for("admin.dashboard")
                return redirect(nxt)
            _note_fail(ip)
            current_app.logger.warning("어드민 로그인 실패 ip=%s id=%s", ip, uid[:20])
            error = "아이디 또는 비밀번호가 올바르지 않습니다."
    return render_template("admin/login.html", error=error), (401 if error else 200)


@bp.route("/logout", methods=["GET", "POST"])
def logout():
    session.pop("admin_id", None)
    return redirect(url_for("admin.login"))


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


# ── 계정 관리 ───────────────────────────────────────────────────────

@bp.route("/account")
@requires_auth
def account():
    me = current_admin()
    users = AdminUser.query.order_by(AdminUser.id).all()
    return render_template("admin/account.html", nav="acct", me=me, users=users)


@bp.route("/account/password", methods=["POST"])
@requires_auth
def password():
    me = current_admin()
    cur = request.form.get("current") or ""
    new = request.form.get("new") or ""
    again = request.form.get("again") or ""

    err = None
    # 초기 비밀번호 강제 변경 중에는 현재 비밀번호를 다시 묻지 않는다
    if not me.must_change and not me.check_password(cur):
        err = "현재 비밀번호가 올바르지 않습니다."
    elif len(new) < 8:
        err = "새 비밀번호는 8자 이상이어야 합니다."
    elif new != again:
        err = "새 비밀번호가 서로 다릅니다."
    elif me.check_password(new):
        err = "이전과 다른 비밀번호를 입력해 주세요."

    if err:
        flash(err, "error")
    else:
        me.set_password(new)
        me.must_change = False
        db.session.commit()
        current_app.logger.info("어드민 비밀번호 변경 id=%s", me.username)
        flash("비밀번호를 변경했습니다.", "ok")
    return redirect(url_for("admin.account"))


@bp.route("/account/add", methods=["POST"])
@requires_auth
def account_add():
    uid = (request.form.get("username") or "").strip()
    name = (request.form.get("name") or "").strip()[:50]
    pw = request.form.get("password") or ""

    err = None
    if not re.fullmatch(r"[A-Za-z0-9_.-]{3,50}", uid):
        err = "아이디는 영문·숫자·_.- 조합 3~50자로 입력해 주세요."
    elif AdminUser.query.filter_by(username=uid).first():
        err = "이미 있는 아이디입니다."
    elif len(pw) < 8:
        err = "비밀번호는 8자 이상이어야 합니다."

    if err:
        flash(err, "error")
    else:
        u = AdminUser(username=uid, name=name or uid, must_change=True)
        u.set_password(pw)
        db.session.add(u)
        db.session.commit()
        current_app.logger.info("어드민 계정 추가 id=%s", uid)
        flash("%s 계정을 추가했습니다. 첫 로그인 때 비밀번호를 바꾸게 됩니다." % uid, "ok")
    return redirect(url_for("admin.account"))


@bp.route("/account/<int:user_id>/toggle", methods=["POST"])
@requires_auth
def account_toggle(user_id):
    me = current_admin()
    u = db.session.get(AdminUser, user_id)
    if not u:
        flash("계정을 찾을 수 없습니다.", "error")
    elif u.id == me.id:
        flash("본인 계정은 끌 수 없습니다.", "error")
    elif u.is_active and AdminUser.query.filter_by(is_active=True).count() <= 1:
        # 마지막 활성 계정까지 끄면 아무도 못 들어온다
        flash("마지막 남은 계정은 끌 수 없습니다.", "error")
    else:
        u.is_active = not u.is_active
        db.session.commit()
        flash("%s 계정을 %s했습니다." % (u.username, "사용" if u.is_active else "중지"), "ok")
    return redirect(url_for("admin.account"))


@bp.route("/account/<int:user_id>/delete", methods=["POST"])
@requires_auth
def account_delete(user_id):
    me = current_admin()
    u = db.session.get(AdminUser, user_id)
    if not u:
        flash("계정을 찾을 수 없습니다.", "error")
    elif u.id == me.id:
        flash("본인 계정은 삭제할 수 없습니다.", "error")
    elif AdminUser.query.count() <= 1:
        flash("마지막 남은 계정은 삭제할 수 없습니다.", "error")
    else:
        db.session.delete(u)
        db.session.commit()
        current_app.logger.info("어드민 계정 삭제 id=%s", u.username)
        flash("%s 계정을 삭제했습니다." % u.username, "ok")
    return redirect(url_for("admin.account"))
