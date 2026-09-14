from datetime import datetime, timezone

from app import db


def now_utc():
    return datetime.now(timezone.utc)


class Gu(db.Model):
    __tablename__ = "gu"

    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(50), nullable=False)
    intro_html = db.Column(db.Text)
    court_note = db.Column(db.Text)
    sort = db.Column(db.Integer, default=0)

    dongs = db.relationship("Dong", backref="gu", order_by="Dong.sort")


class Dong(db.Model):
    __tablename__ = "dong"

    id = db.Column(db.Integer, primary_key=True)
    gu_id = db.Column(db.Integer, db.ForeignKey("gu.id"), nullable=False)
    slug = db.Column(db.String(50), nullable=False)
    name = db.Column(db.String(50), nullable=False)
    name_legal = db.Column(db.String(100))  # 통합된 행정동 표기 (예: 정자1·2·3동)
    transit_note = db.Column(db.Text)
    feature_note = db.Column(db.Text)
    adjacent_slugs = db.Column(db.JSON)  # 같은 구 인접 동 slug 리스트
    variant_set = db.Column(db.String(1), default="A")
    sort = db.Column(db.Integer, default=0)

    __table_args__ = (db.UniqueConstraint("gu_id", "slug"),)


class Job(db.Model):
    __tablename__ = "job"

    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(50), unique=True, nullable=False)
    slug_ko = db.Column(db.String(50), unique=True)  # 한글 URL용 (예: 직장인 → /직장인-개인회생/)
    name = db.Column(db.String(50), nullable=False)
    category = db.Column(db.String(30))  # 급여소득 / 사업소득 / 특수형태 / 무소득·기타
    income_proof_note = db.Column(db.Text)
    job_keep_note = db.Column(db.Text)
    repay_note = db.Column(db.Text)
    variant_set = db.Column(db.String(1), default="A")
    sort = db.Column(db.Integer, default=0)


class CaseType(db.Model):
    __tablename__ = "case_type"

    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(50), unique=True, nullable=False)
    slug_ko = db.Column(db.String(50), unique=True)  # 한글 URL용
    name = db.Column(db.String(50), nullable=False)
    intro = db.Column(db.Text)
    variant_set = db.Column(db.String(1), default="A")
    sort = db.Column(db.Integer, default=0)


class ContentBlock(db.Model):
    __tablename__ = "content_block"

    id = db.Column(db.Integer, primary_key=True)
    block_key = db.Column(db.String(50), nullable=False)  # rehab_core / after_apply / why_us
    variant = db.Column(db.String(1), nullable=False)
    body_html = db.Column(db.Text, nullable=False)

    __table_args__ = (db.UniqueConstraint("block_key", "variant"),)


class Faq(db.Model):
    __tablename__ = "faq"

    id = db.Column(db.Integer, primary_key=True)
    scope = db.Column(db.String(10), nullable=False)  # common / dong / gu / job / case
    kind = db.Column(db.String(10), default="qa")  # qa / concern(고민 4줄용, question_tpl만 사용)
    question_tpl = db.Column(db.Text, nullable=False)  # {{dong}} {{gu}} {{job}} {{name}} 치환
    answer_tpl = db.Column(db.Text)
    sort = db.Column(db.Integer, default=0)


class Post(db.Model):
    """진행 사례 게시판 (단일 보드)."""

    __tablename__ = "post"

    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(200), unique=True, nullable=False)
    title = db.Column(db.String(200), nullable=False)
    excerpt = db.Column(db.String(300))
    body_html = db.Column(db.Text, nullable=False)
    thumb_path = db.Column(db.String(255))  # /static/uploads/... (960w webp)
    thumb_alt = db.Column(db.String(200))
    is_public = db.Column(db.Boolean, default=True)
    view_count = db.Column(db.Integer, default=0)
    published_at = db.Column(db.DateTime, default=now_utc)
    created_at = db.Column(db.DateTime, default=now_utc)
    updated_at = db.Column(db.DateTime, default=now_utc, onupdate=now_utc)


class Inquiry(db.Model):
    __tablename__ = "inquiry"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    phone = db.Column(db.String(30), nullable=False)
    debt_range = db.Column(db.String(50))
    area_text = db.Column(db.String(100))
    source_path = db.Column(db.String(255))
    utm = db.Column(db.JSON)
    memo = db.Column(db.Text)
    status = db.Column(db.String(20), default="new")  # new / contacted / done / spam
    created_at = db.Column(db.DateTime, default=now_utc)
