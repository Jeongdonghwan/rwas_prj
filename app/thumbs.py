# -*- coding: utf-8 -*-
"""글에 썸네일이 없을 때 쓰는 기본 이미지 — 큰 글자 포스터형 카드.

썸네일이 없으면 목록 카드는 빈 회색 칸, ItemList·Article JSON-LD·OG 는 사이트 공통
og.jpg 로 채워진다. 같은 그림이 수백 편에 붙으면 네이버 웹문서 썸네일·캐러셀에서
글끼리 구분이 안 된다. 글마다 키워드가 박힌 카드를 만든다.

구성(의뢰인 레퍼런스: 키워드 / 전화번호 / 문구 / 사무소명 — 큰 글자, 강한 대비)
    [키워드]            ← 그 글의 검색 키워드(없으면 제목)
    [ 1644-6755 ]       ← 흰 박스 안 전화번호
    빠른 접수 · 변호사 직접 상담
    ⌂ 법률사무소 레이

**중요 글자는 전부 가운데 정사각형(630×630) 안에 둔다.** 네이버 웹문서 결과는
og:image 를 정사각형으로 잘라 보여준다 — 가로로 긴 카드의 양 끝 글자는 거기서 사라진다.
크기는 OG 표준 1200×630 을 유지하고 양옆은 장식(엠블럼 워터마크)만 둔다.

- 저장 위치 `static/uploads/auto/` — **이 폴더의 썸네일은 "자동"이라는 표시**다.
  어드민에서 제목을 고치면 다시 그리고, 사진을 올리면 그걸로 바뀐다.
- 파일명에 내용 해시를 넣어 바뀔 때마다 URL 이 달라진다(캐시 무효화). 옛 파일은 지운다.
- 폰트는 사이트 self-host 서브셋(woff2)을 그대로 쓴다. 서브셋에 없는 글자는 빼고 그린다.
"""
from pathlib import Path

from flask import current_app
from PIL import Image, ImageDraw, ImageFont
from fontTools.ttLib import TTFont

from app.config import SITE_DEFAULTS
from app.content import stable_hash

W, H = 1200, 630
SAFE = 600                      # 가운데 정사각형(630) 안쪽 여백 포함 실제 글자 폭
CX = W // 2
AUTO_DIR = "uploads/auto"

BG = (251, 249, 244)            # 사이트 --paper(아이보리)
BURGUNDY = (31, 43, 72)         # --green (실값 곤색, 2026-10-23 팔레트) — 이름은 호환용
CHARCOAL = (29, 29, 31)         # --ink
GOLD = (138, 106, 52)           # 로고 글자에만 — UI 색으로 쓰지 않는다(CLAUDE.md)
TAGLINE = "빠른 접수 · 변호사 직접 상담"   # 결과를 암시하는 말("안전한 마무리" 등)은 쓰지 않는다


def _font_path(weight):
    return Path(current_app.static_folder) / "fonts" / ("pretendard-%d.woff2" % weight)


_cmap = None


def _covered(text):
    """서브셋에 있는 글자만 남긴다."""
    global _cmap
    if _cmap is None:
        _cmap = set(TTFont(str(_font_path(800))).getBestCmap())
    return "".join(c for c in text if c == " " or ord(c) in _cmap)


def _wrap(draw, text, font, width):
    """어절 단위 줄바꿈. 한 어절이 너무 길면 글자 단위로 자른다."""
    lines, cur = [], ""
    for word in text.split():
        cand = (cur + " " + word).strip()
        if draw.textlength(cand, font=font) <= width:
            cur = cand
            continue
        if cur:
            lines.append(cur)
        cur = word
        while draw.textlength(cur, font=font) > width:
            i = len(cur)
            while i > 1 and draw.textlength(cur[:i], font=font) > width:
                i -= 1
            lines.append(cur[:i])
            cur = cur[i:]
    if cur:
        lines.append(cur)
    return lines


def _fit(draw, text, weight, max_size, min_size, width, max_lines):
    """폭 안에 max_lines 줄 이하로 들어가는 가장 큰 글자 크기와 줄 목록."""
    for size in range(max_size, min_size - 1, -4):
        font = ImageFont.truetype(str(_font_path(weight)), size)
        lines = _wrap(draw, text, font, width)
        if len(lines) <= max_lines:
            return font, size, lines
    lines = lines[:max_lines]
    lines[-1] = lines[-1].rstrip() + "…"
    return font, size, lines


def render(headline, phone=None):
    headline = _covered(headline) or "개인회생 상담"
    phone = phone or SITE_DEFAULTS["phone"]
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    # 양옆 장식 — 정사각형 크롭 밖이라 내용은 두지 않는다
    emblem_path = Path(current_app.static_folder) / "img" / "emblem.png"
    emblem = Image.open(emblem_path).convert("RGBA") if emblem_path.exists() else None
    if emblem:
        wm = emblem.copy()
        wm.thumbnail((260, 260))
        a = wm.getchannel("A").point(lambda v: v * 7 // 100)      # 7% 투명도
        wm.putalpha(a)
        img.paste(wm, (40, (H - wm.height) // 2), wm)
        img.paste(wm, (W - 40 - wm.width, (H - wm.height) // 2), wm)
    d.rectangle((0, 0, W, 8), fill=BURGUNDY)
    d.rectangle((0, H - 8, W, H), fill=BURGUNDY)

    # 1) 키워드 — 2줄까지, 폭에 맞춰 축소
    kf, ks, klines = _fit(d, headline, 800, 92, 48, SAFE, 2)
    klh = int(ks * 1.18)
    kh = klh * len(klines)

    # 2) 전화번호 박스
    pf, ps, _ = _fit(d, phone, 800, 124, 60, SAFE - 80, 1)
    box_h = int(ps * 1.5)

    # 3) 문구, 4) 사무소명
    tf = ImageFont.truetype(str(_font_path(800)), 36)
    bf = ImageFont.truetype(str(_font_path(700)), 26)
    gap = 26
    total = kh + gap + box_h + gap + 44 + 18 + 40
    y = (H - total) // 2

    for ln in klines:
        d.text((CX, y), ln, font=kf, fill=BURGUNDY, anchor="ma")
        y += klh
    y += gap

    bw = int(d.textlength(phone, font=pf)) + 80
    d.rounded_rectangle((CX - bw // 2, y, CX + bw // 2, y + box_h), radius=22,
                        fill=(255, 255, 255), outline=CHARCOAL, width=4)
    d.text((CX, y + box_h // 2), phone, font=pf, fill=CHARCOAL, anchor="mm")
    y += box_h + gap

    d.text((CX, y), TAGLINE, font=tf, fill=BURGUNDY, anchor="ma")
    y += 44 + 18

    brand = "법률사무소 레이"
    bwid = int(d.textlength(brand, font=bf))
    ex = 0
    if emblem:
        em = emblem.copy()
        em.thumbnail((40, 36))
        ex = em.width + 10
        img.paste(em, (CX - (bwid + ex) // 2, y), em)
    d.text((CX - (bwid + ex) // 2 + ex, y + 18), brand, font=bf, fill=GOLD, anchor="lm")
    return img


def page_og(headline):
    """지역·직업·상황 페이지 전용 OG 카드 경로(/static/...). 없으면 그린다.

    공통 og.jpg 를 모든 동 페이지가 쓰면 네이버 웹문서 썸네일이 전부 같은 그림이 된다.
    파일명은 헤드라인 해시 — 한글 파일명을 피하고, 문구가 바뀌면 URL 도 바뀐다.
    여러 워커가 동시에 그려도 깨지지 않게 임시 파일에 쓰고 rename 한다.
    """
    absdir = Path(current_app.static_folder) / AUTO_DIR / "page"
    name = "page-%08d.jpg" % (stable_hash("og::" + headline) % 10 ** 8)
    path = absdir / name
    if not path.exists():
        absdir.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp%d" % (id(path) % 10000))
        render(headline).save(tmp, "JPEG", quality=88, optimize=True, progressive=True)
        tmp.replace(path)
    return "/static/%s/page/%s" % (AUTO_DIR, name)


def is_auto(path):
    return bool(path) and ("/%s/" % AUTO_DIR) in path


def headline_for(post):
    """카드 큰 글자 — 칼럼은 큐의 검색 키워드, 없으면 제목."""
    try:
        from app.models import ColumnKeyword
        kw = ColumnKeyword.query.filter_by(post_id=post.id).first()
        if kw and kw.keyword:
            return kw.keyword
    except Exception:
        pass
    return post.title


def make(post):
    """post 에 기본 썸네일을 붙인다(커밋은 호출자가). 경로를 돌려준다."""
    head = headline_for(post)
    absdir = Path(current_app.static_folder) / AUTO_DIR
    absdir.mkdir(parents=True, exist_ok=True)
    stem = "%s-%d" % (post.kind or "post", post.id)
    ver = stable_hash("v2::" + head) % 100000
    name = "%s-%d.jpg" % (stem, ver)
    for old in absdir.glob(stem + "-*.jpg"):       # 이전 버전 정리
        if old.name != name:
            old.unlink(missing_ok=True)
    (absdir / (stem + ".jpg")).unlink(missing_ok=True)   # v1 파일명
    render(head).save(absdir / name, "JPEG", quality=88, optimize=True, progressive=True)
    post.thumb_path = "/static/%s/%s" % (AUTO_DIR, name)
    post.thumb_alt = ("%s | %s %s" % (head, SITE_DEFAULTS["phone"], "법률사무소 레이"))[:200]
    return post.thumb_path


if __name__ == "__main__":
    # 자가 점검: 짧은·긴·서브셋 밖 글자 제목이 정사각형 안에 그려지는지
    import sys
    from app import create_app
    app = create_app()
    with app.app_context():
        out = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
        for i, t in enumerate(["개인회생", "안산 이혼 빚 개인회생 사례",
                               "수원 자영업자 개인회생, 사업을 계속하면서 빚을 정리할 수 있는지",
                               "똠양꿍 뷁 개인파산 기간"]):
            im = render(t)
            assert im.size == (W, H)
            im.save(out / ("thumb-test-%d.jpg" % i), quality=88)
        print("OK", out)
