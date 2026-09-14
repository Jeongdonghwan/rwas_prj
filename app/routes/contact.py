import re

from flask import Blueprint, flash, redirect, render_template, request, url_for

from app import db
from app.models import Inquiry

bp = Blueprint("contact", __name__)

PHONE_RE = re.compile(r"^[0-9\-\s]{9,20}$")


@bp.route("/contact/")
def contact():
    return render_template("contact.html")


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

    if not name or not PHONE_RE.match(phone):
        flash("이름과 연락처를 확인해주세요.", "error")
        return redirect(back + "#form")
    if not agree:
        flash("개인정보 수집·이용 동의가 필요합니다.", "error")
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

    return render_template("inquiry_done.html", name=name)
