# -*- coding: utf-8 -*-
"""법률칼럼 키워드 큐 — 적재와 선택.

선택 규칙: **분류 라운드로빈.** 같은 분류("생활영향")가 연달아 나오면
며칠째 비슷한 글만 올라가 사이트가 단조로워 보인다. 최근 발행에서 가장 오래
안 쓴 분류부터 하나씩 고른다.
"""
import csv
from datetime import datetime, timezone
from pathlib import Path

from app import db
from app.config import REGION
from app.models import ColumnKeyword

ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = ROOT / "seed" / "column_keywords.csv"

MAX_ATTEMPTS = 3   # 검증에서 이만큼 떨어지면 failed — 어드민에서 되살린다


def load_csv(path=CSV_PATH):
    """CSV → 테이블. (추가 수, 정리 수)를 돌려준다.

    **기존 행의 status 는 건드리지 않는다.**

    키워드 목록을 다시 만들어 넣어도 이미 쓴 키워드가 pending 으로
    돌아가면 같은 글을 두 번 쓰게 된다.
    """
    with open(path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    wanted = {r["keyword"] for r in rows}

    # CSV 에서 빠진 키워드 중 **아직 안 쓴 것(pending)만** 지운다.
    # 키워드 규칙을 고친 뒤(예: "이동 …" → "안산 이동 …") 다시 적재하면 옛 표기가
    # 대기열에 남아 그대로 발행된다 — 운영 첫 실행에서 실제로 그랬다.
    # done/failed 는 절대 건드리지 않는다(발행 이력·실패 기록).
    removed = (ColumnKeyword.query
               .filter(ColumnKeyword.status == "pending",
                       ColumnKeyword.keyword.notin_(wanted))
               .delete(synchronize_session=False))

    existing = {k.keyword for k in ColumnKeyword.query.with_entities(
        ColumnKeyword.keyword)}
    added = 0
    for r in rows:
        if r["keyword"] in existing:
            continue
        db.session.add(ColumnKeyword(
            keyword=r["keyword"], category=r["category"],
            scheme=r["scheme"], area=r.get("area") or "",
            intent=r.get("intent") or "",
        ))
        existing.add(r["keyword"])
        added += 1
    db.session.commit()
    return added, removed


def _order(s):
    """사이트마다 다른 순서. **5개 사이트가 같은 날 같은 주제를 쓰지 않게 한다.**

    큐 CSV 는 다섯 사이트가 같은 주제 목록에서 만들어져 순서가 똑같다.
    id 순으로 꺼내면 첫날 수원·안산·용인·성남이 전부 "배우자 재산도 보나요"를
    쓴다 — 같은 사업자 도메인 네 개가 같은 날 같은 글을 올리는 건 도어웨이 신호다.
    사이트 소금을 섞은 해시로 순서를 정해 사이트마다 다른 길로 큐를 돈다.
    """
    from app.content import stable_hash
    return stable_hash("%s::col::%s" % (REGION.get("site_salt") or REGION["name"], s))


def pick(n):
    """오늘 쓸 키워드 n개. 최근에 덜 쓴 분류부터 하나씩."""
    # 분류별 마지막 발행 시각 — 한 번도 안 쓴 분류가 가장 앞
    last_used = {}
    for cat, ts in (db.session.query(ColumnKeyword.category,
                                     db.func.max(ColumnKeyword.published_at))
                    .filter(ColumnKeyword.status == "done")
                    .group_by(ColumnKeyword.category)):
        last_used[cat] = ts

    cats = [c for (c,) in db.session.query(ColumnKeyword.category)
            .filter(ColumnKeyword.status == "pending").distinct()]
    epoch = datetime(1970, 1, 1)
    cats.sort(key=lambda c: (last_used.get(c) or epoch, _order(c)))

    picked = []
    for cat in cats:
        if len(picked) >= n:
            break
        cands = ColumnKeyword.query.filter_by(status="pending", category=cat).all()
        if cands:
            # 재시도 횟수가 적은 것 우선, 그 안에서는 사이트별 순서
            picked.append(min(cands, key=lambda k: (k.attempts or 0,
                                                    _order(k.keyword))))
    return picked


def mark_done(kw, post_id):
    kw.status = "done"
    kw.post_id = post_id
    kw.published_at = datetime.now(timezone.utc)
    kw.last_error = None
    db.session.commit()


def mark_failed(kw, reason):
    """검증 실패. 한도 전까지는 pending 으로 남겨 다음 날 다시 시도한다."""
    kw.attempts = (kw.attempts or 0) + 1
    kw.last_error = (reason or "")[:300]
    if kw.attempts >= MAX_ATTEMPTS:
        kw.status = "failed"
    db.session.commit()


def stats():
    q = db.session.query(ColumnKeyword.status, db.func.count()).group_by(
        ColumnKeyword.status)
    return dict(q.all())
