# -*- coding: utf-8 -*-
"""칼럼 자동 발행 일정 — 어드민에서 켜고 끄고, 회차별 편수·시각을 바꾼다.

cron 은 **매시간** `flask write-columns --auto` 를 부르고, 여기 설정과 현재 시각(KST)을 보고
이번 시간에 돌 회차가 있으면 그만큼만 쓴다. 그래서 편수·시각을 바꿔도 서버 cron 은 손댈 필요가 없다.

회차 2개: general(지역 없는 질문·사례·비교) / region(지역 키워드). 같은 회차를 하루에 두 번 돌지
않도록 마지막 실행 날짜를 남긴다.
"""
from datetime import datetime, timedelta, timezone

from app import db
from app.models import Setting

KST = timezone(timedelta(hours=9))
MAX_PER_SLOT = 5        # 한 회차 최대 편수 — 하루에 갑자기 몰아 올리면 양산 글로 보이고 비용도 뛴다

SLOTS = {
    "general": {"label": "일반 키워드", "desc": "질문·사례·생활·제도비교"},
    "region": {"label": "지역 키워드", "desc": "지역×직업·상황·사례·질문"},
}
DEFAULTS = {
    "enabled": "1",
    "general_n": "2", "general_hour": "3",
    "region_n": "2", "region_hour": "14",
}


def get_all():
    vals = dict(DEFAULTS)
    for row in Setting.query.filter(Setting.key.like("col_%")).all():
        vals[row.key[4:]] = row.value
    return vals


def _set(key, value):
    row = db.session.get(Setting, "col_" + key)
    if row is None:
        row = Setting(key="col_" + key)
        db.session.add(row)
    row.value = str(value)


def save(form):
    """어드민 폼 저장. 값은 범위로 잘라 넣는다(편수 0~5, 시각 0~23)."""
    _set("enabled", "1" if form.get("enabled") else "0")
    for slot in SLOTS:
        n = _clamp(form.get(slot + "_n"), 0, MAX_PER_SLOT, int(DEFAULTS[slot + "_n"]))
        h = _clamp(form.get(slot + "_hour"), 0, 23, int(DEFAULTS[slot + "_hour"]))
        _set(slot + "_n", n)
        _set(slot + "_hour", h)
    db.session.commit()


def _clamp(v, lo, hi, default):
    try:
        return max(lo, min(hi, int(v)))
    except (TypeError, ValueError):
        return default


def now_kst():
    return datetime.now(KST)


def due_slots(now=None):
    """지금 돌아야 하는 회차 [(slot, n)]. 꺼져 있거나 이미 오늘 돈 회차는 빠진다."""
    now = now or now_kst()
    v = get_all()
    if v.get("enabled") != "1":
        return []
    today = now.strftime("%Y-%m-%d")
    out = []
    for slot in SLOTS:
        n = int(v.get(slot + "_n") or 0)
        if n > 0 and int(v.get(slot + "_hour") or -1) == now.hour \
                and v.get(slot + "_last") != today:
            out.append((slot, n))
    return out


def mark_ran(slot, ok, total, now=None):
    now = now or now_kst()
    _set(slot + "_last", now.strftime("%Y-%m-%d"))
    _set(slot + "_result", "%s · %d/%d편" % (now.strftime("%m-%d %H:%M"), ok, total))
    db.session.commit()


if __name__ == "__main__":
    # 자가 점검: 시각·중복·꺼짐 규칙. **메모리 DB 로 돈다** — config 를 앱 생성 뒤에 바꾸면
    # 이미 붙은 dev.db 에 테스트 값이 써진다(실제로 그랬다). 그래서 환경변수로 먼저 지정하고 다시 import.
    import os
    import subprocess
    import sys
    if os.environ.get("DATABASE_URL") != "sqlite://":
        env = dict(os.environ, DATABASE_URL="sqlite://")
        sys.exit(subprocess.call([sys.executable, "-m", "app.column_settings"], env=env))
    from app import create_app
    app = create_app()
    with app.app_context():
        db.create_all()
        t3 = datetime(2026, 10, 29, 3, 5, tzinfo=KST)
        assert due_slots(t3) == [("general", 2)], due_slots(t3)
        mark_ran("general", 2, 2, t3)
        assert due_slots(t3) == [], "같은 날 두 번 돌면 안 된다"
        assert due_slots(t3 + timedelta(days=1)) == [("general", 2)]
        save({"enabled": "", "general_n": "9", "general_hour": "30"})
        assert due_slots(t3 + timedelta(days=1)) == [], "꺼지면 안 돈다"
        save({"enabled": "1", "general_n": "9", "general_hour": "4", "region_n": "0"})
        v = get_all()
        assert v["general_n"] == "5" and v["general_hour"] == "4" and v["region_n"] == "0"
        print("OK")
