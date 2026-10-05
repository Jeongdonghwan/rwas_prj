from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote

from flask import Flask, has_request_context, request
from flask_compress import Compress
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# ── 시각 ────────────────────────────────────────────────────────────
# DB에는 전부 UTC로 쌓는다(models.now_utc). 서버 로컬 시각을 섞으면 정렬과
# 비교가 9시간씩 어긋나므로, **저장은 UTC·표시는 KST**로 분리한다.
# 운영 서버의 타임존 설정에 기대지 않으려고 오프셋을 직접 둔다.
KST = timezone(timedelta(hours=9))


def to_kst(dt):
    """naive는 UTC로 간주하고 KST로 바꾼다. 과거 데이터가 naive라서 필요하다."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(KST)


def kst_day_start_utc(days_ago=0):
    """한국 날짜 기준 그날 0시를 UTC naive로 돌려준다.

    DB의 created_at과 직접 비교하려면 tz를 떼야 한다 — SQLite는 naive로 저장한다.
    """
    day = (datetime.now(KST) - timedelta(days=days_ago)).date()
    start = datetime.combine(day, datetime.min.time(), tzinfo=KST)
    return start.astimezone(timezone.utc).replace(tzinfo=None)


def create_app():
    app = Flask(__name__)
    app.config.from_object("app.config.Config")

    Path(app.root_path).parent.joinpath("instance").mkdir(exist_ok=True)

    # 응답 압축 — HTML 51KB→12KB, CSS 52KB→12KB. 앞단(nginx)이 이미 gzip을 하면
    # 그쪽이 먼저 처리하므로 중복 압축은 일어나지 않는다. 폰트(woff2)는 이미
    # 압축된 포맷이라 대상에서 뺀다.
    app.config.setdefault("COMPRESS_MIMETYPES", [
        "text/html", "text/css", "text/xml", "text/plain",
        "text/javascript", "application/javascript", "application/json",
        "application/xml", "application/rss+xml",
    ])
    app.config.setdefault("COMPRESS_LEVEL", 6)
    app.config.setdefault("COMPRESS_MIN_SIZE", 1024)
    Compress(app)

    db.init_app(app)

    from app.config import LAWYER, SITE_DEFAULTS

    import os
    _static = Path(app.static_folder)
    try:
        asset_ver = str(int(max(
            os.path.getmtime(_static / "css" / "site.css"),
            os.path.getmtime(_static / "js" / "site.js"),
        )))
    except OSError:
        asset_ver = "1"

    _areas = []

    def _area_options():
        """구(또는 시도) 이름 목록. 한 번 읽어 캐시한다 — 전 페이지에서 쓰이므로
        매 요청 조회하면 낭비고, 지역 목록은 배포 중에 바뀌지 않는다."""
        if not _areas:
            try:
                from app.models import Gu
                _areas.extend(g.name for g in Gu.query.order_by(Gu.sort).all())
            except Exception:       # DB가 아직 없을 때(최초 기동 등)
                return []
        return _areas

    @app.context_processor
    def inject_site():
        # canonical/og:url은 사이트맵과 같은 표기여야 한다. request.path는 디코딩된
        # 한글이라 그대로 쓰면 사이트맵(퍼센트 인코딩)과 달라져 크롤러가 같은 URL로
        # 묶지 못할 수 있다 → 여기서 인코딩해 한 가지 표기로 통일한다.
        canonical = SITE_DEFAULTS["base_url"].rstrip("/")
        if has_request_context():
            canonical += quote(request.path)
        return {
            "site": SITE_DEFAULTS,
            "lawyer": LAWYER,
            "asset_ver": asset_ver,
            "canonical_url": canonical,
            # 상담폼 거주 지역 선택지. **하드코딩하면 안 된다** — 수원 구 이름을
            # 박아두는 바람에 안산 사이트 상담폼에 장안구·권선구가 떴다.
            "area_options": _area_options(),
        }

    # Flask는 정적 파일을 파일 핸들 그대로(스트리밍) 내보낸다. 그러면
    # Flask-Compress가 스트리밍 전용 알고리즘만 써서 br은 되지만 gzip은 빠진다.
    # get_data()로 본문을 한 번 읽어 일반 응답으로 만들면 gzip까지 적용된다.
    # after_request는 등록 역순 실행이라 Compress(app)보다 늦게 등록해야
    # 이 훅이 먼저 돌아 압축 단계에 반영된다. (woff2·이미지는 이미 압축 포맷이라 제외)
    @app.after_request
    def _compressible_static(resp):
        if resp.direct_passthrough and resp.mimetype in (
            "text/css", "text/javascript", "application/javascript",
        ):
            resp.direct_passthrough = False
            resp.get_data()
        return resp

    from app.content import josa, vtext
    from app.variants import SECTION_KEYS

    app.jinja_env.globals["vtext"] = vtext
    app.jinja_env.globals["lf_sections"] = SECTION_KEYS
    app.jinja_env.filters["josa"] = josa

    # 문장 풀(variants·keyword_sections·DB 템플릿)에서 쓰는 지역 변수.
    # render_tpl이 이 jinja_env를 쓰므로 풀 문장 안에서 {{ region }} 같은 식으로
    # 참조할 수 있다. 지역마다 달라지는 값을 문장에 박지 않기 위한 장치다.
    from app.config import REGION as _R
    app.jinja_env.globals.update(
        region=_R["name"], region_full=_R["name_full"],
        court=_R["court"], court_long=_R["court_long"],
        court_district=_R["court_district"],
        area_long=_R["area_long"],
    )

    # DB에는 UTC로 쌓이니 화면에 찍을 땐 전부 이 필터를 거친다.
    # 템플릿에서 .strftime()을 직접 부르면 9시간 이른 시각이 나온다.
    def _kst(dt, fmt="%Y-%m-%d %H:%M", empty="-"):
        dt = to_kst(dt)
        return dt.strftime(fmt) if dt else empty

    app.jinja_env.filters["kst"] = _kst

    from app.routes.main import bp as main_bp
    from app.routes.contact import bp as contact_bp
    from app.routes.admin import bp as admin_bp
    from app.routes.area import bp as area_bp
    from app.routes.job import bp as job_bp
    from app.routes.ko import bp as ko_bp
    from app.routes.board import bp as board_bp
    from app.routes.seo import bp as seo_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(contact_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(area_bp)
    app.register_blueprint(job_bp)
    app.register_blueprint(ko_bp)
    app.register_blueprint(board_bp)
    app.register_blueprint(seo_bp)

    # 서브키워드 블루프린트는 /<slug>/ 라는 가장 넓은 패턴을 쓴다.
    # 고정 페이지·기존 한글 URL이 먼저 잡혀야 하므로 반드시 마지막에 등록한다.
    from app.routes.keyword import bp as keyword_bp

    app.register_blueprint(keyword_bp)

    from app.seed import (admin_reset_command, seed_command,
                          seed_keywords_command, sms_check_command)

    app.cli.add_command(seed_command)
    app.cli.add_command(seed_keywords_command)
    app.cli.add_command(sms_check_command)
    app.cli.add_command(admin_reset_command)

    with app.app_context():
        from app import models  # noqa: F401

        db.create_all()

    return app
