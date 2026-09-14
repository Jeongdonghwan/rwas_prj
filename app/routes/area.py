"""구 영문 URL(/area/...) — 한글 URL로 301 리다이렉트만 담당."""

from flask import Blueprint, redirect, url_for

from app.models import Dong, Gu

bp = Blueprint("area", __name__, url_prefix="/area")


@bp.route("/")
def hub():
    return redirect(url_for("ko.area_hub"), 301)


@bp.route("/<gu_slug>/")
def gu_page(gu_slug):
    gu = Gu.query.filter_by(slug=gu_slug).first_or_404()
    return redirect(url_for("ko.page", name=gu.name), 301)


@bp.route("/<gu_slug>/<dong_slug>/")
def dong_page(gu_slug, dong_slug):
    gu = Gu.query.filter_by(slug=gu_slug).first_or_404()
    dong = Dong.query.filter_by(gu_id=gu.id, slug=dong_slug).first_or_404()
    return redirect(url_for("ko.page", name=dong.name), 301)
