"""SEO 파일: robots.txt, sitemap(index+분할), RSS.

한글 URL이 정식이므로 url_for가 반환하는 퍼센트 인코딩 경로를 그대로 사용한다.
(사이트맵·RSS는 XML 규격상 반드시 인코딩된 절대 URL이어야 한다.)
"""

from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path
from xml.sax.saxutils import escape

from flask import Blueprint, Response, abort, url_for

from app.config import SITE_DEFAULTS
from app.keyword_rules import SCHEMES
from app.models import CaseType, Dong, Gu, Job, Keyword, Post

# 서브키워드 사이트맵은 제도별로 나눈다. 색인 문제가 어느 세트에서 났는지
# 추적하려면 나눠야 하고, 문제가 생기면 세트 단위로 내릴 수 있다.
KW_PER_FILE = 5000

bp = Blueprint("seo", __name__)

CACHE = "public, max-age=600"  # 10분

ROOT = Path(__file__).resolve().parent.parent.parent

# 페이지 유형별로 "그 페이지를 실제로 만들어내는 파일들".
# lastmod를 여기서 뽑는다 — 전 URL에 오늘 날짜를 박으면 매일 전체가 바뀐다고
# 주장하는 꼴이라 검색엔진이 lastmod 신호 자체를 무시한다.
#
# **base.html·헤더·푸터는 일부러 뺐다.** 메타태그 한 줄 고쳤다고 전 페이지
# lastmod가 오늘로 리셋되면 "매일 전체가 바뀐다"는 원래 문제로 되돌아간다.
# 여기 넣는 것은 그 페이지의 **본문 내용**을 만드는 파일만.
LONGFORM_SRC = ("app/templates/partials/longform.html",
                "app/templates/partials/lf_summary.html",
                "app/templates/partials/lf_table.html",
                "app/variants.py", "app/variants_longform.py", "app/content.py",
                "seed/faq.csv", "seed/content_blocks")

CONTENT_SOURCES = {
    "area": ("app/templates/area", "seed/gu.csv", "seed/dong.csv") + LONGFORM_SRC,
    "job": ("app/templates/job", "seed/job.csv") + LONGFORM_SRC,
    "case": ("app/templates/casetype", "seed/case_type.csv") + LONGFORM_SRC,
}


def content_mtime(*rel_paths):
    """주어진 파일·디렉터리의 최종 수정 시각 중 가장 최근 값.

    git으로 배포하면 바뀐 파일만 mtime이 갱신되므로, 실제로 고친 유형의
    lastmod만 움직인다. 파일이 없으면(배포 누락 등) 오늘로 떨어진다.
    """
    ts = []
    for rel in rel_paths:
        p = ROOT / rel
        if p.is_dir():
            ts += [f.stat().st_mtime for f in p.rglob("*") if f.is_file()]
        elif p.exists():
            ts.append(p.stat().st_mtime)
    return datetime.fromtimestamp(max(ts)) if ts else datetime.now()


def template_mtime(*names):
    """해당 페이지 템플릿의 수정 시각만 본다(base.html·공통 파셜은 제외)."""
    return content_mtime(*("app/templates/%s" % n for n in names))


def base():
    return SITE_DEFAULTS["base_url"].rstrip("/")


def abs_url(endpoint, **kw):
    return base() + url_for(endpoint, **kw)


def xml_response(body, mimetype="application/xml; charset=utf-8"):
    return Response(body, mimetype=mimetype, headers={"Cache-Control": CACHE})


def url_entry(loc, lastmod=None, changefreq=None, priority=None):
    out = ["  <url>", "    <loc>%s</loc>" % escape(loc)]
    if lastmod:
        out.append("    <lastmod>%s</lastmod>" % lastmod.strftime("%Y-%m-%d"))
    if changefreq:
        out.append("    <changefreq>%s</changefreq>" % changefreq)
    if priority:
        out.append("    <priority>%s</priority>" % priority)
    out.append("  </url>")
    return "\n".join(out)


def urlset(entries):
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(entries)
        + "\n</urlset>\n"
    )


# ---------- robots.txt ----------

@bp.route("/robots.txt")
def robots():
    body = "\n".join([
        "User-agent: *",
        "Allow: /",
        "Disallow: /admin/",
        "Disallow: /inquiry",
        "Disallow: /static/uploads/tmp/",
        "Disallow: /*?utm_",
        "",
        "# 네이버 검색로봇",
        "User-agent: Yeti",
        "Allow: /",
        "Disallow: /admin/",
        "Disallow: /inquiry",
        "",
        "# 다음 검색로봇",
        "User-agent: Daum",
        "Allow: /",
        "Disallow: /admin/",
        "Disallow: /inquiry",
        "",
        "Sitemap: %s/sitemap.xml" % base(),
        "Sitemap: %s/rss.xml" % base(),
        "",
    ])
    return Response(body, mimetype="text/plain; charset=utf-8",
                    headers={"Cache-Control": CACHE})


# ---------- sitemap ----------

@bp.route("/sitemap.xml")
@bp.route("/sitemap")
def sitemap_index():
    latest_post = (
        Post.query.filter_by(is_public=True)
        .order_by(Post.published_at.desc())
        .first()
    )
    lastmods = {
        "pages": template_mtime("index.html", "about.html", "contact.html",
                                "process.html", "faq.html", "service"),
        "area": content_mtime(*CONTENT_SOURCES["area"]),
        "job": content_mtime(*CONTENT_SOURCES["job"]),
        "case": content_mtime(*CONTENT_SOURCES["case"]),
        "board": (latest_post.updated_at or latest_post.published_at)
                 if latest_post else template_mtime("board"),
    }
    names = ["pages", "area", "job", "case", "board"]
    parts = [
        "  <sitemap>\n    <loc>%s/sitemap-%s.xml</loc>\n    <lastmod>%s</lastmod>\n  </sitemap>"
        % (base(), n, lastmods[n].strftime("%Y-%m-%d"))
        for n in names
    ]

    # 서브키워드 — 제도별, 5,000개 넘으면 페이지 분할
    kw_mt = content_mtime("app/keyword_sections", "app/scheme_facts.py",
                          "app/keyword_render.py", "app/templates/keyword",
                          "seed/keyword.csv")
    for scheme in SCHEMES:
        n = Keyword.query.filter_by(scheme=scheme, is_public=True).count()
        if not n:
            continue
        for p in range(1, (n + KW_PER_FILE - 1) // KW_PER_FILE + 1):
            parts.append(
                "  <sitemap>\n    <loc>%s/sitemap-kw-%s-%d.xml</loc>\n"
                "    <lastmod>%s</lastmod>\n  </sitemap>"
                % (base(), scheme, p, kw_mt.strftime("%Y-%m-%d"))
            )
    items = "\n".join(parts)
    return xml_response(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + items
        + "\n</sitemapindex>\n"
    )


@bp.route("/sitemap-pages.xml")
def sitemap_pages():
    # 고정 페이지는 각자의 템플릿 수정 시각을 쓴다
    rows = [
        ("main.index", "index.html", "weekly", "1.0"),
        ("main.service_rehab", "service/rehab.html", "monthly", "0.9"),
        ("main.service_bankruptcy", "service/bankruptcy.html", "monthly", "0.9"),
        ("main.service_cost", "service/cost.html", "monthly", "0.9"),
        ("main.process", "process.html", "monthly", "0.8"),
        ("main.service_docs", "service/docs.html", "monthly", "0.8"),
        ("main.faq", "faq.html", "monthly", "0.8"),
        ("main.about", "about.html", "monthly", "0.7"),
        ("contact.contact", "contact.html", "monthly", "0.8"),
        ("main.privacy", "privacy.html", "yearly", "0.2"),
        ("main.email_policy", "email_policy.html", "yearly", "0.2"),
    ]
    return xml_response(urlset([
        url_entry(abs_url(ep), template_mtime(tpl), cf, pr)
        for ep, tpl, cf, pr in rows
    ]))


@bp.route("/sitemap-area.xml")
def sitemap_area():
    mt = content_mtime(*CONTENT_SOURCES["area"])
    entries = [url_entry(abs_url("ko.area_hub"), mt, "weekly", "0.9")]
    for gu in Gu.query.order_by(Gu.sort).all():
        entries.append(url_entry(abs_url("ko.page", name=gu.name), mt, "monthly", "0.8"))
    for dong in Dong.query.order_by(Dong.sort).all():
        entries.append(url_entry(abs_url("ko.page", name=dong.name), mt, "monthly", "0.7"))
    return xml_response(urlset(entries))


@bp.route("/sitemap-job.xml")
def sitemap_job():
    mt = content_mtime(*CONTENT_SOURCES["job"])
    entries = [url_entry(abs_url("ko.job_hub"), mt, "weekly", "0.9")]
    for job in Job.query.order_by(Job.sort).all():
        entries.append(url_entry(abs_url("ko.page", name=job.slug_ko), mt, "monthly", "0.7"))
    return xml_response(urlset(entries))


@bp.route("/sitemap-case.xml")
def sitemap_case():
    mt = content_mtime(*CONTENT_SOURCES["case"])
    entries = [url_entry(abs_url("ko.case_hub"), mt, "weekly", "0.9")]
    for c in CaseType.query.order_by(CaseType.sort).all():
        entries.append(url_entry(abs_url("ko.page", name=c.slug_ko), mt, "monthly", "0.7"))
    return xml_response(urlset(entries))


@bp.route("/sitemap-board.xml")
def sitemap_board():
    posts = (
        Post.query.filter_by(is_public=True)
        .order_by(Post.published_at.desc())
        .all()
    )
    newest = posts[0].updated_at or posts[0].published_at if posts else template_mtime("board")
    entries = [url_entry(abs_url("board.case_list"), newest, "daily", "0.9")]
    for p in posts:
        entries.append(url_entry(
            abs_url("board.case_view", slug=p.slug),
            p.updated_at or p.published_at, "monthly", "0.7",
        ))
    return xml_response(urlset(entries))


# ---------- RSS (네이버 서치어드바이저 RSS 제출용) ----------

@bp.route("/rss.xml")
@bp.route("/rss")
@bp.route("/feed")
@bp.route("/feed.xml")
def rss():
    site = SITE_DEFAULTS
    posts = (
        Post.query.filter_by(is_public=True)
        .order_by(Post.published_at.desc())
        .limit(30)
        .all()
    )

    def rfc822(dt):
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return format_datetime(dt)

    items = []
    for p in posts:
        link = abs_url("board.case_view", slug=p.slug)
        item = [
            "    <item>",
            "      <title>%s</title>" % escape(p.title),
            "      <link>%s</link>" % escape(link),
            '      <guid isPermaLink="true">%s</guid>' % escape(link),
            "      <pubDate>%s</pubDate>" % rfc822(p.published_at),
            "      <description><![CDATA[%s]]></description>" % (p.excerpt or ""),
            "      <content:encoded><![CDATA[%s]]></content:encoded>" % (p.body_html or ""),
            "      <category>진행 사례</category>",
        ]
        if p.thumb_path:
            item.append('      <enclosure url="%s" type="image/webp" length="0"/>'
                        % escape(base() + p.thumb_path))
        item.append("    </item>")
        items.append("\n".join(item))

    now = rfc822(datetime.now(timezone.utc))
    body = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/">\n'
        "  <channel>\n"
        "    <title>%s 진행 사례</title>\n" % escape(site["brand"])
        + "    <link>%s</link>\n" % escape(abs_url("board.case_list"))
        + "    <description>수원개인회생·수원개인회생파산 진행 사례. %s에서 실제 진행한 사건을 사실 위주로 기록합니다.</description>\n"
          % escape(site["firm_name"])
        + "    <language>ko</language>\n"
        + "    <lastBuildDate>%s</lastBuildDate>\n" % now
        + "    <generator>lei-law</generator>\n"
        + ("\n".join(items) + "\n" if items else "")
        + "  </channel>\n</rss>\n"
    )
    return xml_response(body, "application/rss+xml; charset=utf-8")


@bp.route("/sitemap-kw-<scheme>-<int:page>.xml")
def sitemap_keyword(scheme, page):
    """서브키워드 사이트맵 — 제도별 분할. 비공개(is_public=False)는 넣지 않는다."""
    if scheme not in SCHEMES or page < 1:
        abort(404)
    mt = content_mtime("app/keyword_sections", "app/scheme_facts.py",
                       "app/keyword_render.py", "app/templates/keyword",
                       "seed/keyword.csv")
    rows = (
        Keyword.query.filter_by(scheme=scheme, is_public=True)
        .order_by(Keyword.id)
        .offset((page - 1) * KW_PER_FILE)
        .limit(KW_PER_FILE)
        .all()
    )
    if not rows:
        abort(404)

    entries = []
    if page == 1:
        # 허브는 첫 파일에만 넣는다 — 크롤러가 여기부터 내려가게
        entries.append(url_entry(abs_url("keyword.hub"), mt, "weekly", "0.8"))
        entries.append(
            url_entry(abs_url("keyword.scheme_hub", scheme=scheme), mt, "weekly", "0.8")
        )
        cats = (
            Keyword.query.with_entities(Keyword.category)
            .filter_by(scheme=scheme, is_public=True)
            .distinct()
            .all()
        )
        for (cat,) in cats:
            entries.append(url_entry(
                abs_url("keyword.category_hub", scheme=scheme, category=cat),
                mt, "weekly", "0.7",
            ))

    entries += [
        url_entry(abs_url("keyword.page", slug=k.slug_ko), mt, "monthly", "0.6")
        for k in rows
    ]
    return xml_response(urlset(entries))
