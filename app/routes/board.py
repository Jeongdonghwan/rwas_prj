"""글 게시판 — 진행 사례와 법률칼럼 두 종류.

한글 URL: `/사례/`, `/사례/<slug>/` · `/법률칼럼/`, `/법률칼럼/<slug>/`

**두 보드를 섞지 않는 이유**는 내용이 아니라 광고규정이다. 사례는 실제 사건
기록이라 "의뢰인 동의를 받아 사실 위주" 고지가 붙고 사람이 직접 쓴다.
칼럼은 제도 일반 안내라 자동 생성이 가능하고 "개별 사건의 법률 자문이 아니다"가
붙는다. 한 보드에 섞이면 자동 생성 글이 사례 고지를 달게 된다.

칼럼 경로는 `REGION["column_path"]`다. 발행 전이면 그 값만 바꾸면 되지만,
**색인이 시작된 뒤에는** 옛 경로를 받아 새 경로로 301을 돌려주는 라우트를
따로 추가해야 한다(옛 값을 상수로 남겨 `redirect(..., code=301)`).
"""

from flask import Blueprint, abort, redirect, render_template, url_for

from app import db
from app.config import REGION
from app.models import Post

bp = Blueprint("board", __name__)

PER_PAGE = 8
COLUMN_PATH = REGION["column_path"]


def _public(kind):
    return Post.query.filter_by(is_public=True, kind=kind)


def _paged(kind, page, template, **extra):
    q = _public(kind).order_by(Post.published_at.desc())
    total = q.count()
    pages = max((total + PER_PAGE - 1) // PER_PAGE, 1)
    if page < 1 or page > pages:
        abort(404)
    posts = q.offset((page - 1) * PER_PAGE).limit(PER_PAGE).all()
    return render_template(template, posts=posts, page=page, pages=pages,
                           total=total, **extra)


def _detail(kind, slug, template, list_endpoint):
    post = _public(kind).filter_by(slug=slug).first_or_404()
    post.view_count = (post.view_count or 0) + 1
    db.session.commit()

    prev_post = (
        _public(kind)
        .filter(Post.published_at < post.published_at, Post.id != post.id)
        .order_by(Post.published_at.desc())
        .first()
    )
    next_post = (
        _public(kind)
        .filter(Post.published_at > post.published_at, Post.id != post.id)
        .order_by(Post.published_at.asc())
        .first()
    )
    recent = (
        _public(kind)
        .filter(Post.id != post.id)
        .order_by(Post.published_at.desc())
        .limit(5)
        .all()
    )
    return render_template(template, post=post, prev_post=prev_post,
                           next_post=next_post, recent=recent,
                           list_endpoint=list_endpoint)


# ── 진행 사례 (사람이 직접 작성) ──────────────────────────────────

@bp.route("/사례/")
@bp.route("/사례/page/<int:page>/")
def case_list(page=1):
    return _paged(Post.KIND_CASE, page, "board/list.html")


@bp.route("/사례/<slug>/")
def case_view(slug):
    return _detail(Post.KIND_CASE, slug, "board/view.html", "board.case_list")


# ── 법률칼럼 (자동 생성 + 어드민 수정) ──────────────────────────────

@bp.route("/%s/" % COLUMN_PATH)
@bp.route("/%s/page/<int:page>/" % COLUMN_PATH)
def column_list(page=1):
    return _paged(Post.KIND_COLUMN, page, "board/column_list.html")


@bp.route("/%s/<slug>/" % COLUMN_PATH)
def column_view(slug):
    return _detail(Post.KIND_COLUMN, slug, "board/column_view.html",
                   "board.column_list")
