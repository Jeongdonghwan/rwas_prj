"""flask seed — seed/*.csv 와 seed/content_blocks/*.html 을 DB에 적재 (전체 삭제 후 재적재)."""

import csv
from pathlib import Path

import click
from flask.cli import with_appcontext

from app import db
from app.models import CaseType, ContentBlock, Dong, Faq, Gu, Job, Post

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
