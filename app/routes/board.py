"""진행 사례 게시판 (블로그형, 단일 보드). 한글 URL: /사례/, /사례/<slug>/"""

from flask import Blueprint, abort, render_template

from app import db
from app.models import Post

bp = Blueprint("board", __name__)

PER_PAGE = 8


def _public():
    return Post.query.filter_by(is_public=True)


@bp.route("/사례/")
@bp.route("/사례/page/<int:page>/")
def case_list(page=1):
    q = _public().order_by(Post.published_at.desc())
    total = q.count()
    pages = max((total + PER_PAGE - 1) // PER_PAGE, 1)
    if page < 1 or page > pages:
        abort(404)
    posts = q.offset((page - 1) * PER_PAGE).limit(PER_PAGE).all()
    return render_template(
        "board/list.html", posts=posts, page=page, pages=pages, total=total
    )


@bp.route("/사례/<slug>/")
def case_view(slug):
    post = _public().filter_by(slug=slug).first_or_404()
    post.view_count = (post.view_count or 0) + 1
    db.session.commit()

    prev_post = (
        _public()
        .filter(Post.published_at < post.published_at, Post.id != post.id)
        .order_by(Post.published_at.desc())
        .first()
    )
    next_post = (
        _public()
        .filter(Post.published_at > post.published_at, Post.id != post.id)
        .order_by(Post.published_at.asc())
        .first()
    )
    recent = (
        _public()
        .filter(Post.id != post.id)
        .order_by(Post.published_at.desc())
        .limit(5)
        .all()
    )
    return render_template(
        "board/view.html",
        post=post,
        prev_post=prev_post,
        next_post=next_post,
        recent=recent,
    )
