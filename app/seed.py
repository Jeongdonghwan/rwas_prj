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

    # 목업 사례 1건 — 게시글이 하나도 없을 때만 (재시드 시 중복·삭제 없음)
    if Post.query.count() == 0:
        db.session.add(
            Post(
                slug="영통구-40대-직장인-채무-1억-2천만-원-변제계획-인가",
                title="영통구 40대 직장인, 채무 1억 2천만 원 변제계획 인가",
                excerpt="이자만 갚던 카드론·신용대출 1억 2천만 원을 월 58만 원, 36개월 변제계획으로 정리한 사례입니다.",
                body_html=(
                    "<h2>상담 당시 상황</h2><p>카드론과 신용대출을 합쳐 채무가 1억 2천만 원까지 늘어난 상태였습니다. "
                    "매달 이자만 190만 원 수준이라 급여로는 원금이 줄지 않았고, 한 곳에서 압류 예고 통지를 받고 상담을 오셨습니다.</p>"
                    "<h2>진행 과정</h2><p>급여명세서와 부채증명서를 3주간 정리해 수원회생법원에 신청했고, "
                    "접수 12일차에 금지명령이 나와 추심이 중단됐습니다. 보정명령 1회를 같은 주에 대응했습니다.</p>"
                    "<h2>결과</h2><p>신청 5개월차에 월 58만 원, 36개월 변제계획이 인가됐습니다. "
                    "인가 이후에는 확정된 변제금만 납입하면 됩니다.</p>"
                    "<p>※ 채무·소득·재산에 따라 결과는 달라질 수 있습니다.</p>"
                ),
                thumb_path="/static/img/consult.webp",
                thumb_alt="상담 서류를 검토하는 모습",
                is_public=True,
            )
        )
        click.echo("sample case post added (목업 1건)")

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
