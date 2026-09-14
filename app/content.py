"""variant 블록 선택·FAQ 회전·템플릿 변수 치환 헬퍼."""

from jinja2 import Template

from app.models import ContentBlock, Faq

VARIANT_OFFSET = {"A": 0, "B": 1, "C": 2}


def get_block(block_key, variant):
    row = (
        ContentBlock.query.filter_by(block_key=block_key, variant=variant).first()
        or ContentBlock.query.filter_by(block_key=block_key, variant="A").first()
    )
    return row.body_html if row else ""


def render_tpl(text, **vars):
    if not text:
        return ""
    return Template(text).render(**vars)


def pick_faqs(scope, variant, count, kind="qa", **vars):
    """scope 풀에서 variant 오프셋으로 회전해 count개 선택, 변수 치환."""
    pool = (
        Faq.query.filter_by(scope=scope, kind=kind).order_by(Faq.sort).all()
    )
    if not pool:
        return []
    offset = VARIANT_OFFSET.get(variant, 0) % len(pool)
    rotated = pool[offset:] + pool[:offset]
    return [
        {
            "q": render_tpl(f.question_tpl, **vars),
            "a": render_tpl(f.answer_tpl, **vars),
        }
        for f in rotated[:count]
    ]
