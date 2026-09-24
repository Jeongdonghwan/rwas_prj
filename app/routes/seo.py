"""SEO 파일: robots.txt, sitemap(index+분할), RSS.

한글 URL이 정식이므로 url_for가 반환하는 퍼센트 인코딩 경로를 그대로 사용한다.
(사이트맵·RSS는 XML 규격상 반드시 인코딩된 절대 URL이어야 한다.)
"""

from datetime import datetime, timezone
from email.utils import format_datetime
from xml.sax.saxutils import escape

from flask import Blueprint, Response, url_for

from app.config import SITE_DEFAULTS
from app.models import CaseType, Dong, Gu, Job, Post

bp = Blueprint("seo", __name__)

CACHE = "public, max-age=600"  # 10분


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
    names = ["pages", "area", "job", "case", "board"]
    now = datetime.now().strftime("%Y-%m-%d")
    items = "\n".join(
        "  <sitemap>\n    <loc>%s/sitemap-%s.xml</loc>\n    <lastmod>%s</lastmod>\n  </sitemap>"
        % (base(), n, now)
        for n in names
    )
    return xml_response(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + items
        + "\n</sitemapindex>\n"
    )


@bp.route("/sitemap-pages.xml")
def sitemap_pages():
    today = datetime.now()
    rows = [
        ("main.index", "daily", "1.0"),
        ("main.service_rehab", "weekly", "0.9"),
        ("main.service_bankruptcy", "weekly", "0.9"),
        ("main.service_cost", "weekly", "0.9"),
        ("main.process", "weekly", "0.8"),
        ("main.service_docs", "weekly", "0.8"),
        ("main.faq", "weekly", "0.8"),
        ("main.about", "monthly", "0.7"),
        ("contact.contact", "monthly", "0.8"),
        ("main.privacy", "yearly", "0.2"),
        ("main.email_policy", "yearly", "0.2"),
    ]
    return xml_response(urlset([
        url_entry(abs_url(ep), today, cf, pr) for ep, cf, pr in rows
    ]))


@bp.route("/sitemap-area.xml")
def sitemap_area():
    today = datetime.now()
    entries = [url_entry(abs_url("ko.area_hub"), today, "weekly", "0.9")]
    for gu in Gu.query.order_by(Gu.sort).all():
        entries.append(url_entry(abs_url("ko.page", name=gu.name), today, "monthly", "0.8"))
    for dong in Dong.query.order_by(Dong.sort).all():
        entries.append(url_entry(abs_url("ko.page", name=dong.name), today, "monthly", "0.7"))
    return xml_response(urlset(entries))


@bp.route("/sitemap-job.xml")
def sitemap_job():
    today = datetime.now()
    entries = [url_entry(abs_url("ko.job_hub"), today, "weekly", "0.9")]
    for job in Job.query.order_by(Job.sort).all():
        entries.append(url_entry(abs_url("ko.page", name=job.slug_ko), today, "monthly", "0.7"))
    return xml_response(urlset(entries))


@bp.route("/sitemap-case.xml")
def sitemap_case():
    today = datetime.now()
    entries = [url_entry(abs_url("ko.case_hub"), today, "weekly", "0.9")]
    for c in CaseType.query.order_by(CaseType.sort).all():
        entries.append(url_entry(abs_url("ko.page", name=c.slug_ko), today, "monthly", "0.7"))
    return xml_response(urlset(entries))


@bp.route("/sitemap-board.xml")
def sitemap_board():
    posts = (
        Post.query.filter_by(is_public=True)
        .order_by(Post.published_at.desc())
        .all()
    )
    entries = [url_entry(abs_url("board.case_list"), datetime.now(), "daily", "0.9")]
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
