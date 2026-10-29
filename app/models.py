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


class AdminUser(db.Model):
    """어드민 계정.

    예전에는 HTTP Basic + 환경변수 한 쌍이었다. 로그아웃이 안 되고,
    비밀번호를 바꾸려면 서버 .env를 고치고 재시작해야 했으며, 계정이 하나뿐이었다.

    비밀번호는 **평문으로 저장하지 않는다** — werkzeug scrypt 해시만 둔다.
    첫 기동 시 계정이 하나도 없으면 ADMIN_USER/ADMIN_PASSWORD(기본 admin/admin)로
    하나를 만든다. 그 상태는 어드민 화면에 경고로 표시된다.
    """

    __tablename__ = "admin_user"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(50))
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    must_change = db.Column(db.Boolean, default=False, nullable=False)
    last_login_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=now_utc)

    def set_password(self, raw):
        from werkzeug.security import generate_password_hash

        self.password_hash = generate_password_hash(raw)

    def check_password(self, raw):
        from werkzeug.security import check_password_hash

        return check_password_hash(self.password_hash, raw or "")


class Keyword(db.Model):
    """서브키워드 랜딩 페이지 (12,000행). seed/keyword.csv에서 적재.

    전체 설계는 keyword-pages-plan.md 참고.
    - scheme: rehab / bankruptcy / credit / workout / adjust (app/keyword_rules.SCHEMES)
    - needs_correction: 제도 치환으로 사실과 어긋나는 키워드 → 본문 최상단에 교정 문단
    - is_public: 세트 단위 롤백용. 대량 발행 후 색인 문제가 나면 여기부터 내린다.
    """

    __tablename__ = "keyword"

    id = db.Column(db.Integer, primary_key=True)
    # slug_ko 실측 최대 28자(71바이트). VARCHAR(200)이면 utf8mb4 유니크 인덱스가
    # 800바이트가 되어 구형 InnoDB의 767바이트 한계에 걸릴 수 있다 → 120으로 제한.
    slug_ko = db.Column(db.String(120), unique=True, nullable=False, index=True)
    keyword = db.Column(db.String(160), nullable=False)
    scheme = db.Column(db.String(20), nullable=False, index=True)
    region = db.Column(db.String(20), default="")       # "" 또는 "수원"
    category = db.Column(db.String(40), index=True)      # 분류 25종
    intent = db.Column(db.String(60))                    # 검색의도 30종
    needs_correction = db.Column(db.Boolean, default=False)
    correction_terms = db.Column(db.String(200))         # ";" 구분
    is_public = db.Column(db.Boolean, default=True, index=True)
    source_no = db.Column(db.Integer)
    # 같은 (분류, 제도, 지역) 그룹 안에서의 순번. app/variant_codes.VECTORS를
    # 이 값으로 골라 섹션 조합을 배정한다 → 같은 그룹 두 페이지가 공유하는
    # 섹션이 최대 3/6개로 제한된다. 해시로 독립 선택하면 우연히 5~6개가 겹친다.
    variant_idx = db.Column(db.Integer, default=0)


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
    """글. kind 로 성격이 갈린다.

    **case(진행 사례)와 column(법률칼럼)을 절대 섞지 말 것.**
    사례는 실제 사건 기록이라 "의뢰인 동의를 받아 사실 위주로 작성" 고지가 붙고
    **사람이 직접 쓴다** — 없는 사건을 생성하면 변호사 광고규정상 허위광고다.
    칼럼은 제도·절차 일반 안내라 자동 생성이 가능하고, "개별 사건의 법률 자문이
    아니다"라는 다른 고지가 붙는다.
    """

    __tablename__ = "post"

    KIND_CASE = "case"
    KIND_COLUMN = "column"

    id = db.Column(db.Integer, primary_key=True)
    # 기존 행은 전부 진행 사례다 → default/서버 기본값 모두 case
    kind = db.Column(db.String(16), default=KIND_CASE, nullable=False,
                     server_default=KIND_CASE, index=True)
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


class ColumnKeyword(db.Model):
    """법률칼럼 키워드 큐. seed/column_keywords.csv 에서 적재.

    status: pending → done(발행됨) / failed(재시도 한도 초과, 어드민에서 되살릴 수 있음)
    큐를 다시 적재해도 status 는 보존한다 — 같은 키워드를 두 번 쓰지 않기 위해서다.
    """

    __tablename__ = "column_keyword"

    id = db.Column(db.Integer, primary_key=True)
    keyword = db.Column(db.String(160), unique=True, nullable=False, index=True)
    category = db.Column(db.String(20), index=True)
    scheme = db.Column(db.String(20))
    area = db.Column(db.String(30), default="")
    intent = db.Column(db.String(40))
    status = db.Column(db.String(10), default="pending", nullable=False, index=True)
    attempts = db.Column(db.Integer, default=0, nullable=False)
    last_error = db.Column(db.String(300))
    post_id = db.Column(db.Integer)
    published_at = db.Column(db.DateTime)


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


class Setting(db.Model):
    """어드민에서 바꾸는 운영 설정(키-값). 지금은 칼럼 자동 발행 일정만 쓴다(app/column_settings.py)."""

    __tablename__ = "setting"

    key = db.Column(db.String(40), primary_key=True)
    value = db.Column(db.String(300))
