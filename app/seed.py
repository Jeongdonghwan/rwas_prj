"""flask seed — seed/*.csv 와 seed/content_blocks/*.html 을 DB에 적재 (전체 삭제 후 재적재)."""

import csv
from pathlib import Path

import click
from flask.cli import with_appcontext

from app import db
from app.models import CaseType, ContentBlock, Dong, Faq, Gu, Job

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

    db.session.commit()
    click.echo(
        f"seeded: gu={Gu.query.count()} dong={Dong.query.count()} "
        f"job={Job.query.count()} case_type={CaseType.query.count()} "
        f"faq={Faq.query.count()} content_block={ContentBlock.query.count()}"
    )
