import os
import re

from flask import (
    Blueprint,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from app import db, sms
from app.config import SITE_DEFAULTS
from app.models import Inquiry

bp = Blueprint("contact", __name__)

PHONE_RE = re.compile(r"^[0-9\-\s]{9,20}$")


@bp.route("/contact/")
def contact():
    return render_template("contact.html")


def _notify(name, phone, debt_range, area_text):
    """접수 확인 문자(신청자) + 새 접수 알림(사무소).

    두 발송 모두 실패해도 접수에는 영향이 없다(app/sms.py 참고).
    """
    site = SITE_DEFAULTS
    try:
        sms.send_async(
            phone,
            sms.applicant_message(name, site["firm_name"], site["phone"]),
            title="상담 신청 접수",
        )
        admin_to = os.environ.get("ALIGO_ADMIN_PHONE", "").strip()
        if admin_to:
            sms.send_async(
                admin_to,
                sms.admin_message(name, phone, debt_range, area_text),
                title="상담 접수 알림",
            )
    except Exception:            # 문자 때문에 접수 응답이 깨지는 일은 없어야 한다
        current_app.logger.exception("문자 발송 준비 중 오류")


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

    # 문자는 접수가 **저장된 뒤에** 백그라운드로 보낸다.
    # 문자 발송이 실패해도 접수는 이미 남아 있어야 하고, 응답도 지연되면 안 된다.
    _notify(name, phone, debt_range, area_text)

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
