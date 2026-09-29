import re

from flask import (
    Blueprint,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from app import db
from app.models import Inquiry

bp = Blueprint("contact", __name__)

PHONE_RE = re.compile(r"^[0-9\-\s]{9,20}$")


@bp.route("/contact/")
def contact():
    return render_template("contact.html")


def _wants_json():
    """site.js가 fetch로 보낼 때만 JSON을 준다. JS가 없으면 기존 방식으로 동작."""
    return request.headers.get("X-Requested-With") == "fetch"


@bp.route("/inquiry", methods=["POST"])
def submit():
    name = (request.form.get("name") or "").strip()[:50]
    phone = (request.form.get("phone") or "").strip()[:30]
    debt_range = (request.form.get("debt") or "").strip()[:50]
    area_text = (request.form.get("area") or "").strip()[:100]
    memo = (request.form.get("memo") or "").strip()[:2000]
    source_path = (request.form.get("source_path") or "").strip()[:255]
    agree = request.form.get("agree")

    back = source_path if source_path.startswith("/") else url_for("main.index")

    error = None
    if not name or not PHONE_RE.match(phone):
        error = "이름과 연락처를 확인해주세요."
    elif not agree:
        error = "개인정보 수집·이용 동의가 필요합니다."
    if error:
        if _wants_json():
            return jsonify({"ok": False, "error": error}), 400
        flash(error, "error")
        return redirect(back + "#form")

    utm = {
        k: request.args.get(k)
        for k in ("utm_source", "utm_medium", "utm_campaign")
        if request.args.get(k)
    } or None

    db.session.add(
        Inquiry(
            name=name,
            phone=phone,
            debt_range=debt_range,
            area_text=area_text,
            memo=memo,
            source_path=source_path,
            utm=utm,
        )
    )
    db.session.commit()

    if _wants_json():
        return jsonify({"ok": True, "name": name})

    # JS가 없을 때는 POST-Redirect-GET. POST 응답을 그대로 렌더하면
    # 새로고침 시 브라우저가 재제출을 묻고 URL도 /inquiry로 남는다.
    session["inquiry_name"] = name
    return redirect(url_for("contact.done"))


@bp.route("/inquiry/done/")
def done():
    name = session.pop("inquiry_name", None)
    if not name:
        return redirect(url_for("main.index"))
    return render_template("inquiry_done.html", name=name)
