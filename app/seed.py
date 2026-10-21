"""flask seed — seed/*.csv 와 seed/content_blocks/*.html 을 DB에 적재 (전체 삭제 후 재적재)."""

import csv
from pathlib import Path

import click
from flask.cli import with_appcontext

from app import db
from app.models import CaseType, ContentBlock, Dong, Faq, Gu, Job, Keyword, Post

SEED_DIR = Path(__file__).resolve().parent.parent / "seed"


def read_csv(name):
    with open(SEED_DIR / name, encoding="utf-8") as f:
        return list(csv.DictReader(f))


@click.command("seed")
@with_appcontext
def seed_command():
    for model in (Faq, ContentBlock, CaseType, Job, Dong, Gu):
        db.session.query(model).delete()

    gu_by_slug = {}
    for row in read_csv("gu.csv"):
        gu = Gu(
            slug=row["slug"],
            name=row["name"],
            intro_html=row["intro_html"],
            court_note=row["court_note"],
            sort=int(row["sort"]),
        )
        db.session.add(gu)
        gu_by_slug[gu.slug] = gu
    db.session.flush()

    for row in read_csv("dong.csv"):
        db.session.add(
            Dong(
                gu_id=gu_by_slug[row["gu_slug"]].id,
                slug=row["slug"],
                name=row["name"],
                name_legal=row["name_legal"],
                transit_note=row["transit_note"],
                feature_note=row["feature_note"],
                adjacent_slugs=row["adjacent_slugs"].split(";"),
                variant_set=row["variant_set"],
                sort=int(row["sort"]),
            )
        )

    for row in read_csv("job.csv"):
        db.session.add(
            Job(
                slug=row["slug"],
                slug_ko=row["slug_ko"],
                name=row["name"],
                category=row["category"],
                income_proof_note=row["income_proof_note"],
                job_keep_note=row["job_keep_note"],
                repay_note=row["repay_note"],
                variant_set=row["variant_set"],
                sort=int(row["sort"]),
            )
        )

    for row in read_csv("case_type.csv"):
        db.session.add(
            CaseType(
                slug=row["slug"],
                slug_ko=row["slug_ko"],
                name=row["name"],
                intro=row["intro"],
                variant_set=row["variant_set"],
                sort=int(row["sort"]),
            )
        )

    for row in read_csv("faq.csv"):
        db.session.add(
            Faq(
                scope=row["scope"],
                kind=row["kind"],
                sort=int(row["sort"]),
                question_tpl=row["question_tpl"],
                answer_tpl=row["answer_tpl"] or None,
            )
        )

    for path in sorted((SEED_DIR / "content_blocks").glob("*.html")):
        block_key, variant = path.stem.rsplit("_", 1)
        db.session.add(
            ContentBlock(
                block_key=block_key,
                variant=variant,
                body_html=path.read_text(encoding="utf-8"),
            )
        )

    # **목업 사례를 넣지 않는다.** 예전에는 글이 하나도 없으면 예시 사례를 넣었는데,
    # 새로 만든 운영 DB가 정확히 그 상태라 지어낸 사례("영통구 40대 직장인, 1억 2천만 원
    # 인가")가 다섯 사이트에 "의뢰인 동의를 받아 사실 위주로 작성" 고지를 달고 공개됐다.
    # 없는 사건을 실제 사례로 게시하면 변호사 광고규정상 허위광고다.
    # 진행 사례는 어드민에서 사람이 직접 쓴다.

    db.session.commit()
    click.echo(
        f"seeded: gu={Gu.query.count()} dong={Dong.query.count()} "
        f"job={Job.query.count()} case_type={CaseType.query.count()} "
        f"faq={Faq.query.count()} content_block={ContentBlock.query.count()}"
    )


@click.command("seed-keywords")
@click.option("--public/--draft", default=True,
              help="적재 시 공개 여부. --draft로 넣고 나중에 세트별로 공개할 수 있다.")
@with_appcontext
def seed_keywords_command(public):
    """seed/keyword.csv(12,000행)를 keyword 테이블에 적재. 전체 삭제 후 재삽입.

    본 시드와 분리한 이유: 행이 많아 매번 돌리면 느리고,
    `flask seed`는 지역·직업 데이터만 다루기 때문이다.
    """
    path = SEED_DIR / "keyword.csv"
    if not path.exists():
        raise click.ClickException(
            "seed/keyword.csv가 없습니다. 먼저 python scripts/import_keywords.py 를 실행하세요."
        )

    db.session.query(Keyword).delete()
    db.session.commit()

    # (분류, 제도, 지역) 그룹별 순번 — 섹션 조합 배정에 쓴다
    from collections import defaultdict
    counter = defaultdict(int)

    rows = []
    with open(path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            key = (r["category"], r["scheme"], r["region"])
            idx = counter[key]
            counter[key] += 1
            rows.append({
                "variant_idx": idx,
                "slug_ko": r["slug_ko"],
                "keyword": r["keyword"],
                "scheme": r["scheme"],
                "region": r["region"],
                "category": r["category"],
                "intent": r["intent"],
                "needs_correction": r["needs_correction"] == "1",
                "correction_terms": r["correction_terms"] or None,
                "is_public": public,
                "source_no": int(r["source_no"]) if r["source_no"] else None,
            })

    # 12,000행이라 ORM 개별 add는 느리다 → 청크 단위 bulk insert
    CHUNK = 2000
    for i in range(0, len(rows), CHUNK):
        db.session.bulk_insert_mappings(Keyword, rows[i:i + CHUNK])
        db.session.commit()

    total = Keyword.query.count()
    click.echo("keyword 적재 완료: %d행 (공개=%s)" % (total, public))
    for scheme in ("rehab", "bankruptcy", "credit", "workout", "adjust"):
        n = Keyword.query.filter_by(scheme=scheme).count()
        click.echo("   %-11s %5d" % (scheme, n))
    click.echo("   교정 문단 필요: %d행"
               % Keyword.query.filter_by(needs_correction=True).count())


@click.command("sms-check")
@click.option("--to", default=None, help="이 번호로 테스트 문자를 보낸다(생략하면 잔여건수만 조회)")
@with_appcontext
def sms_check_command(to):
    """문자 설정 점검 — 잔여 건수 조회, 선택적으로 테스트 발송.

        flask sms-check                    잔여 건수만
        flask sms-check --to 01012345678   테스트 문자까지

    발신 서버 IP가 알리고에 등록되지 않았으면 여기서 거절 응답이 나온다.
    ALIGO_TEST_MODE=Y면 실제 발송 없이 응답만 받는다(과금 없음).
    """
    import os
    import sys

    from app import sms
    from app.config import SITE_DEFAULTS

    # 윈도우 콘솔이 cp949라 ✓ 같은 문자에서 터진다
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    click.echo("설정 상태")
    click.echo("  아이디    : %s" % (os.environ.get("ALIGO_USER_ID") or "(없음)"))
    key = os.environ.get("ALIGO_API_KEY") or ""
    click.echo("  API 키    : %s" % (key[:4] + "…" + key[-4:] if len(key) > 8 else "(없음)"))
    click.echo("  발신번호  : %s" % (os.environ.get("ALIGO_SENDER") or "(없음)"))
    click.echo("  테스트모드: %s" % (os.environ.get("ALIGO_TEST_MODE") or "(꺼짐)"))
    if not sms.is_configured():
        raise click.ClickException("ALIGO_* 환경변수가 비어 있습니다(.env 확인)")

    click.echo("\n잔여 건수 조회")
    r = sms.remain()
    click.echo("  %s" % r.get("response") if r.get("ok") else "  실패: %s" % r)

    if to:
        msg = sms.applicant_message("홍길동", SITE_DEFAULTS["firm_name"],
                                    SITE_DEFAULTS["phone"])
        click.echo("\n테스트 발송 → %s" % to)
        click.echo("  본문(%d바이트, %s):" % (sms._byte_len(msg), sms._msg_type(msg)))
        for line in msg.splitlines():
            click.echo("    %s" % line)
        out = sms.send(to, msg, title="상담 신청 접수")
        click.echo("  결과: %s" % out.get("response", out))
        if out.get("ok"):
            click.echo("  ✓ 발송 요청 성공"
                       + ("  (테스트모드라 실제로는 가지 않습니다)"
                          if os.environ.get("ALIGO_TEST_MODE", "").upper() == "Y" else ""))
        else:
            hint = sms.error_hint((out.get("response") or {}).get("result_code"))
            if hint:
                click.echo("  → %s" % hint)


@click.command("admin-reset")
@click.argument("username")
@click.option("--password", default=None, help="지정하지 않으면 임시 비밀번호를 만들어 출력한다")
@with_appcontext
def admin_reset_command(username, password):
    """어드민 비밀번호 재설정 — 비밀번호를 잊었을 때 서버에서 쓴다.

        flask admin-reset admin
        flask admin-reset admin --password 새비밀번호

    재설정하면 다음 로그인 때 본인이 다시 바꾸도록 must_change가 선다.
    """
    import secrets

    from app.models import AdminUser

    u = AdminUser.query.filter_by(username=username).first()
    if not u:
        names = [x.username for x in AdminUser.query.all()]
        raise click.ClickException(
            "'%s' 계정이 없습니다. 현재 계정: %s" % (username, ", ".join(names) or "(없음)")
        )
    pw = password or secrets.token_urlsafe(9)
    u.set_password(pw)
    u.must_change = True
    u.is_active = True
    db.session.commit()
    click.echo("'%s' 비밀번호를 재설정했습니다." % username)
    click.echo("  임시 비밀번호: %s" % pw)
    click.echo("  로그인 후 바로 변경하게 됩니다.")


@click.command("seed-column-keywords")
@with_appcontext
def seed_column_keywords_command():
    """법률칼럼 키워드 큐 적재. 이미 있는 키워드의 status 는 보존한다."""
    from app.column_queue import load_csv, stats

    db.create_all()
    added, removed = load_csv()
    s = stats()
    click.echo("추가 %d · 옛 대기 정리 %d / 대기 %d · 완료 %d · 실패 %d"
               % (added, removed, s.get("pending", 0), s.get("done", 0),
                  s.get("failed", 0)))


@click.command("write-columns")
@click.option("--n", type=int, default=None, help="편수 (기본 .env COLUMN_PER_DAY)")
@click.option("--dry-run", is_flag=True, help="저장·큐 갱신 없이 생성·검증만")
@click.option("--pool", type=click.Choice(["any", "general", "region"]), default="any",
              help="general=지역 없는 질문·사례(새벽) / region=지역 키워드(오후)")
@with_appcontext
def write_columns_command(n, dry_run, pool):
    """법률칼럼 자동 작성 — cron 이 매일 새벽 부른다."""
    import os

    from app.column_writer import run

    db.create_all()
    n = n or int(os.environ.get("COLUMN_PER_DAY") or 2)
    res = run(n, dry_run=dry_run, log=click.echo, pool=pool)
    ok = sum(1 for _, good, _ in res if good)
    click.echo("완료 %d / %d%s" % (ok, len(res), " (dry-run)" if dry_run else ""))


@click.command("post-thumbs")
@click.option("--redo", is_flag=True, help="자동 썸네일도 다시 그린다")
@with_appcontext
def post_thumbs_command(redo):
    """썸네일 없는 글에 기본 타이틀 카드를 붙인다(올린 사진은 건드리지 않는다)."""
    from app.models import Post
    from app.thumbs import is_auto, make

    n = 0
    for p in Post.query.all():
        if p.thumb_path and not (redo and is_auto(p.thumb_path)):
            continue
        make(p)
        n += 1
    db.session.commit()
    click.echo("기본 썸네일 %d개" % n)
