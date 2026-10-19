# -*- coding: utf-8 -*-
"""법률칼럼 자동 작성 — 생성 · 검증 · 저장.

    flask write-columns              # .env 의 COLUMN_PER_DAY 만큼
    flask write-columns --n 1 --dry-run

## 흐름
큐에서 n개 → GPT 작성(JSON) → **검증 게이트** → 통과분만 Post(kind=column) 저장.
실패는 키워드를 pending 으로 남겨 다음 날 다시 시도한다(3회 넘으면 failed).

## 검증 게이트가 막는 것 — 왜 필요한가
자동 생성은 "가끔 틀린다"가 아니라 "확률적으로 반드시 틀린다". 하루 10편이면
한 달에 300편이고, 사람이 매일 다 읽지 않는다. 게이트가 없으면 틀린 글이
그대로 색인된다.

1. **광고규정 금칙어** — 결과 보장·"전문"·"무료"·타 사무소 비교
2. **수치 날조** — 금액·비율·기간이 scheme_facts 에 없는 값이면 탈락.
   모델은 그럴듯한 숫자를 지어낸다. 법률 글에서 틀린 숫자는 그대로 손해다.
3. **유사도** — 기존 칼럼과 3-gram 자카드가 높으면 탈락(양산형 판정 방지)
4. 길이·구조·제목 키워드·내부링크 3개 이상·외부링크 0

## 본문 HTML 은 허용 태그만 남긴다
본문은 화면에 |safe 로 찍힌다. 모델 출력을 그대로 넣으면 <script>든 뭐든 들어간다.
"""
import json
import os
import re
import time
import urllib.request
from html.parser import HTMLParser

from app import db
from app.column_queue import mark_done, mark_failed, pick
from app.config import REGION, SITE_DEFAULTS
from app.keyword_rules import SCHEMES
from app.models import Post
from app.scheme_facts import SCHEME_FACTS

API = "https://api.openai.com/v1/chat/completions"
MIN_CHARS, MAX_CHARS = 1200, 2400
SIM_MAX = 0.45
MIN_LINKS = 3

# 광고규정 — 변호사법·변호사 광고에 관한 규정
BANNED = [
    "100%", "무조건", "반드시 인가", "반드시 면책", "확실히 면책", "보장합니다",
    "보장해", "책임지고", "최저가", "최고의", "업계 1위", "1위", "무료",
    "전문 변호사", "전문가", "전문으로", "다른 사무소", "타 사무소", "어느 곳보다",
]

NAME_TO_CODE = {v: k for k, v in SCHEMES.items()}


# ── 링크 후보 ─────────────────────────────────────────────────────

def link_targets(scheme_code):
    """본문이 걸 수 있는 내부 페이지. **실제로 있는 URL만** 준다 —
    모델에게 자유롭게 링크를 만들게 하면 없는 경로를 지어낸다."""
    from flask import url_for
    base = SITE_DEFAULTS["base_url"]
    t = [
        ("개인회생 신청자격·변제기간", url_for("main.service_rehab")),
        ("개인파산·면책 안내", url_for("main.service_bankruptcy")),
        ("비용 안내", url_for("main.service_cost")),
        ("준비서류", url_for("main.service_docs")),
        ("진행 절차", url_for("main.process")),
        ("자주 묻는 질문", url_for("main.faq")),
        ("상담 신청", url_for("contact.contact")),
        ("지역별 안내", url_for("ko.area_hub")),
    ]
    if scheme_code in SCHEMES:
        t.append(("%s 주제별 안내" % SCHEMES[scheme_code],
                  url_for("keyword.scheme_hub", scheme=scheme_code)))
    return [(name, path) for name, path in t], base


# ── 프롬프트 ──────────────────────────────────────────────────────

def build_prompt(kw):
    code = NAME_TO_CODE.get(kw.scheme, "rehab")
    facts = SCHEME_FACTS.get(code) or SCHEME_FACTS["rehab"]
    kv = "\n".join("- %s: %s" % (a, b) for a, b in facts["kv"])
    links, _ = link_targets(code)
    link_list = "\n".join("- %s → %s" % (n, p) for n, p in links)

    region_line = ("이 사이트는 %s 지역 사이트다. 관할은 %s." %
                   (REGION["name"], REGION["court"])
                   if REGION.get("court_mode") == "named" else
                   "이 사이트는 전국 대상이다. 관할 법원은 주소지에 따라 다르므로 "
                   "특정 법원 이름을 단정하지 마라.")
    area_line = ("키워드에 지역(%s)이 들어 있다. 그 지역 사람이 읽는다고 생각하고 "
                 "자연스럽게 1~2번 언급하라. 지점이 있는 것처럼 쓰지 마라 — "
                 "사무소는 수원 광교 한 곳이다." % kw.area) if kw.area else ""

    system = (
        "너는 한국 법률사무소 '%s'의 법률칼럼을 쓴다. 독자는 빚 때문에 불안한 일반인이다.\n"
        "원칙:\n"
        "1. **첫 문단(2~3문장)에서 질문에 바로 답한다.** 서론으로 시작하지 않는다.\n"
        "2. 결과를 보장하거나 단정하지 않는다. '상담에서 확인'으로 돌릴 수 있다.\n"
        "3. '전문', '무료', '최고', '1위', '100%%', '무조건' 같은 말을 쓰지 않는다.\n"
        "   다른 사무소와 비교하지 않는다.\n"
        "4. **숫자(기간·금액·비율)는 아래 '사실' 목록에 있는 것만 쓴다.** 목록에 없는 "
        "숫자가 필요하면 숫자 없이 '사정에 따라 다르다'로 쓴다. 지어내면 안 된다.\n"
        "5. 과장된 공감·감탄사 없이 차분하게 쓴다. 문장은 짧게.\n"
        % SITE_DEFAULTS["brand"]
    )
    user = (
        "키워드: %s\n분류(참고용 — 이 단어를 제목·본문에 그대로 쓰지 마라): %s"
        " / 검색의도: %s\n제도: %s\n%s\n%s\n\n"
        "사실(이 숫자만 쓸 수 있다):\n%s\n- 비면책채권: 세금·벌금·양육비 등\n\n"
        "내부링크 후보(이 중 3~5개를 본문 문맥에 자연스럽게 건다. 다른 URL은 금지):\n%s\n\n"
        "구성:\n"
        "- 첫 <p>: 질문에 대한 답 2~3문장\n"
        "- <h2> 소제목 3~4개, 각 아래 <p> 또는 <ul><li>\n"
        "- 마지막 <h2>정리</h2> 아래 요점 2~3문장 + 상담 안내 한 문장\n"
        "- 본문 전체 1,400~2,000자(공백 포함, 태그 제외)\n"
        "- 허용 태그: h2 p ul ol li b a(href만). 그 외 태그·속성 금지\n\n"
        "JSON 으로만 답한다:\n"
        '{"title": "키워드가 자연스럽게 들어간 제목(40자 이내)", '
        '"excerpt": "검색결과용 요약(60~78자)", "body_html": "..."}'
        % (kw.keyword, kw.category, kw.intent, kw.scheme,
           region_line, area_line, kv, link_list)
    )
    return system, user


def call_gpt(system, user, model=None, timeout=300):
    key = os.environ["OPENAI_API_KEY"]
    body = {
        "model": model or os.environ.get("MODEL_WRITER", "gpt-5"),
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": user}],
        "response_format": {"type": "json_object"},
    }
    req = urllib.request.Request(
        API, data=json.dumps(body).encode(),
        headers={"Authorization": "Bearer " + key,
                 "Content-Type": "application/json"})
    d = json.loads(urllib.request.urlopen(req, timeout=timeout).read())
    return json.loads(d["choices"][0]["message"]["content"]), d.get("usage", {})


# ── 정리·검증 ─────────────────────────────────────────────────────

ALLOWED_TAGS = {"h2", "p", "ul", "ol", "li", "b", "strong", "a", "br"}


class _Clean(HTMLParser):
    """허용 태그만 남긴다. a 는 href 만, 그것도 내부 경로만."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out = []

    def handle_starttag(self, tag, attrs):
        if tag not in ALLOWED_TAGS:
            return
        if tag == "a":
            href = dict(attrs).get("href") or ""
            if not href.startswith("/") or href.startswith("//"):
                return          # 외부·상대 이상 링크는 태그째 버린다(글자는 남는다)
            self.out.append('<a href="%s">' % href.replace('"', "%22"))
            self._open_a = True
            return
        self.out.append("<%s>" % tag)

    def handle_endtag(self, tag):
        if tag == "a":
            if getattr(self, "_open_a", False):
                self.out.append("</a>")
                self._open_a = False
            return
        if tag in ALLOWED_TAGS and tag != "br":
            self.out.append("</%s>" % tag)

    def handle_data(self, data):
        self.out.append(data.replace("<", "&lt;").replace(">", "&gt;"))


def clean_html(html):
    c = _Clean()
    c.feed(html or "")
    return "".join(c.out)


def plain(html):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).strip()


def _allowed_numbers(code):
    """사실 목록에 등장하는 숫자 표현. 이것 말고는 쓸 수 없다."""
    facts = SCHEME_FACTS.get(code) or {}
    text = " ".join(b for _, b in facts.get("kv", [])) + " " + (facts.get("summary") or "")
    text += " 비면책채권 세금 벌금 양육비"
    return set(re.findall(r"\d+(?:[~\-]\d+)?\s*(?:년|개월|주|일|억|만 ?원|원|%)", text))


NUM_RE = re.compile(r"\d+(?:[~\-]\d+)?\s*(?:년|개월|주|억|만 ?원|원|%)")


_JOSA = ("에서", "으로", "에게", "하고", "이나", "을", "를", "이", "가", "은",
         "는", "에", "의", "도", "로", "과", "와", "만", "나")
# 용언 어미 — "이직하면" → "이직", "공무원인데" → "공무원"
_ENDINGS = ("하면", "인데", "하나요", "되나요", "받나요", "있으면", "없으면")
# 질문 꼬리 — 제목에 없어도 되는 말
_STOP = {"하고", "있을", "있나요", "되나요", "할까요", "어떻게", "하면", "하나요",
         "있는", "없는", "해도", "되는", "때", "중", "후", "전", "수", "것",
         "이유", "방법", "무엇인가요", "생기는", "달라지는", "확인할",
         "있으면", "없으면", "받나요", "진행", "알려지나요", "되면"}


def _core_words(kw):
    """키워드에서 제목에 들어가야 할 내용어. 조사를 떼고 질문 꼬리는 버린다.

    조사를 안 떼면 "돌려막기를"과 제목의 "돌려막기"가 안 맞아 멀쩡한 글이
    떨어진다(실제로 그랬다).
    """
    out = []
    for w in re.findall(r"[가-힣]{2,}", kw.keyword):
        if w in _STOP:
            continue
        for j in _ENDINGS + _JOSA:
            if len(w) > len(j) + 1 and w.endswith(j):
                w = w[:-len(j)]
                break
        # 조사를 뗀 뒤에 지역·제도명인지 다시 본다("개인회생은" → "개인회생")
        if len(w) >= 2 and w not in _STOP and w not in (kw.area, kw.scheme):
            out.append(w)
    return out


def _grams(t, n=3):
    t = re.sub(r"\s+", "", t)
    return {t[i:i + n] for i in range(len(t) - n + 1)}


def validate(kw, data, existing_grams):
    errs = []
    title = (data.get("title") or "").strip()
    excerpt = (data.get("excerpt") or "").strip()
    body = clean_html(data.get("body_html") or "")
    text = plain(body)
    code = NAME_TO_CODE.get(kw.scheme, "rehab")

    if not title:
        errs.append("제목 없음")
    if len(title) > 45:
        errs.append("제목 %d자" % len(title))
    core = _core_words(kw)
    if core and not any(w in title for w in core):
        errs.append("제목에 키워드 핵심어 없음 %s" % core[:3])
    if not (40 <= len(excerpt) <= 79):
        errs.append("요약 %d자(40~79)" % len(excerpt))
    if not (MIN_CHARS <= len(text) <= MAX_CHARS):
        errs.append("본문 %d자(%d~%d)" % (len(text), MIN_CHARS, MAX_CHARS))
    if body.count("<h2>") < 3:
        errs.append("소제목 %d개(3개 이상)" % body.count("<h2>"))

    links = re.findall(r'<a href="(/[^"]*)">', body)
    if len(links) < MIN_LINKS:
        errs.append("내부링크 %d개(%d개 이상)" % (len(links), MIN_LINKS))
    valid = {p for _, p in link_targets(code)[0]}
    bad_links = [l for l in links if l not in valid]
    if bad_links:
        errs.append("없는 경로 링크 %s" % bad_links[:2])

    whole = title + " " + excerpt + " " + text
    hit = [b for b in BANNED if b in whole]
    if hit:
        errs.append("금칙어 %s" % hit)

    allowed = {re.sub(r"\s+", "", x) for x in _allowed_numbers(code)}
    nums = {re.sub(r"\s+", "", x) for x in NUM_RE.findall(whole)}
    made_up = sorted(n for n in nums if n not in allowed)
    if made_up:
        errs.append("사실 목록에 없는 수치 %s" % made_up[:4])

    g = _grams(text)
    if g and existing_grams:
        worst = max(len(g & e) / len(g | e) for e in existing_grams)
        if worst >= SIM_MAX:
            errs.append("기존 칼럼과 유사도 %.2f" % worst)

    return errs, {"title": title, "excerpt": excerpt, "body_html": body,
                  "chars": len(text)}


# ── 실행 ──────────────────────────────────────────────────────────

def _existing_grams():
    return [_grams(plain(p.body_html))
            for p in Post.query.filter_by(kind=Post.KIND_COLUMN).all()]


def run(n, dry_run=False, log=print):
    # cron(CLI)에는 요청이 없어 url_for 가 실패한다 — 내부링크 후보를 만들려면 필요하다
    from flask import current_app
    with current_app.test_request_context():
        return _run(n, dry_run, log)


def _run(n, dry_run, log):
    from app.routes.admin import unique_slug

    kws = pick(n)
    if not kws:
        log("대기 키워드 없음")
        return []
    existing = _existing_grams()
    results = []
    for kw in kws:
        t = time.time()
        try:
            system, user = build_prompt(kw)
            data, usage = call_gpt(system, user)
        except Exception as e:
            reason = "API 오류: %s" % e
            log("  ✗ %s — %s" % (kw.keyword, reason))
            if not dry_run:
                mark_failed(kw, reason)
            results.append((kw.keyword, False, reason))
            continue

        errs, out = validate(kw, data, existing)
        took = time.time() - t
        if errs:
            log("  ✗ %s (%.0f초) — %s" % (kw.keyword, took, " / ".join(errs)))
            if not dry_run:
                mark_failed(kw, " / ".join(errs))
            results.append((kw.keyword, False, errs))
            continue

        log("  ✓ %s (%.0f초, %d자, 토큰 out %s)"
            % (kw.keyword, took, out["chars"], usage.get("completion_tokens")))
        if dry_run:
            results.append((kw.keyword, True, out))
            continue

        post = Post(kind=Post.KIND_COLUMN, slug=unique_slug(out["title"]),
                    title=out["title"], excerpt=out["excerpt"],
                    body_html=out["body_html"], is_public=True)
        db.session.add(post)
        db.session.commit()
        mark_done(kw, post.id)
        existing.append(_grams(plain(out["body_html"])))
        results.append((kw.keyword, True, post.slug))
    return results
