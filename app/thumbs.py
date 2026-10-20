# -*- coding: utf-8 -*-
"""글에 썸네일이 없을 때 쓰는 기본 이미지 — 제목을 얹은 타이틀 카드.

썸네일이 없으면 목록 카드는 빈 회색 칸, ItemList·Article JSON-LD·OG 는 사이트 공통
og.jpg 로 채워진다. 같은 그림이 수백 편에 붙으면 네이버 캐러셀·이미지 검색에서
글끼리 구분이 안 된다. 제목이 들어간 카드는 글마다 다른 이미지가 된다.

- 1200×630 (OG 비율). 목록은 object-fit:cover 라 그대로 쓴다.
- 저장 위치 `static/uploads/auto/` — **이 폴더의 썸네일은 "자동"이라는 표시**다.
  어드민에서 제목을 고치면 다시 그리고, 사진을 올리면 그걸로 바뀐다.
- 폰트는 사이트 self-host 서브셋(woff2)을 그대로 쓴다. 서브셋에 없는 글자는
  두부(□)로 나오므로 그 글자만 빼고 그린다.
"""
import re
from pathlib import Path

from flask import current_app
from PIL import Image, ImageDraw, ImageFont
from fontTools.ttLib import TTFont

from app.config import SITE_DEFAULTS
from app.content import stable_hash

W, H = 1200, 630
AUTO_DIR = "uploads/auto"
PAD = 84

# 배경은 사이트가 이미 쓰는 Unsplash 무료 사진(상업용 무료·저작자표시 불요) 중 하나를
# 제목 해시로 고른다. 사진이 없으면 팔레트 그라데이션으로 떨어진다.
PHOTOS = ["hero-justice.webp", "bg-court.webp", "bg-library.webp",
          "consult.webp", "books.webp"]
BGS = [((124, 34, 49), (74, 18, 30)),     # 딥 버건디
       ((48, 44, 46), (24, 22, 24)),      # 차콜
       ((96, 30, 44), (40, 20, 26))]      # 와인→차콜
GOLD = (214, 184, 132)          # 로고 글자에만 — 골드는 UI 색으로 쓰지 않는다(CLAUDE.md)
CHIP = (232, 222, 224)


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


def _flat_bg(title):
    top, bottom = BGS[stable_hash(title) % len(BGS)]
    img = Image.new("RGB", (W, H), top)
    grad = Image.linear_gradient("L").resize((W, H))
    return Image.composite(Image.new("RGB", (W, H), bottom), img, grad)


def _photo_bg(title):
    """스톡 사진을 1200×630 으로 채워 자르고, 글자가 읽히게 어둡게 깐다."""
    name = PHOTOS[stable_hash("photo::" + title) % len(PHOTOS)]
    path = Path(current_app.static_folder) / "img" / name
    if not path.exists():
        return None
    ph = Image.open(path).convert("RGB")
    scale = max(W / ph.width, H / ph.height)
    ph = ph.resize((round(ph.width * scale), round(ph.height * scale)), Image.LANCZOS)
    x, y = (ph.width - W) // 2, (ph.height - H) // 2
    ph = ph.crop((x, y, x + W, y + H))
    # 좌측(글자 쪽) 더 어둡게 — 가로 그라데이션 알파로 검정을 덮는다
    shade = Image.linear_gradient("L").rotate(90, expand=True).resize((W, H))
    shade = shade.point(lambda v: 150 + (255 - v) * 70 // 255)   # 좌 220 → 우 150
    return Image.composite(Image.new("RGB", (W, H), (16, 14, 15)), ph, shade)


def render(title, label="법률칼럼"):
    """PIL 이미지를 돌려준다."""
    img = _photo_bg(title) or _flat_bg(title)
    d = ImageDraw.Draw(img)

    f600 = lambda s: ImageFont.truetype(str(_font_path(600)), s)
    f800 = lambda s: ImageFont.truetype(str(_font_path(800)), s)

    # 좌상단 라벨 칩
    lf = f600(28)
    lw = d.textlength(label, font=lf)
    d.rounded_rectangle((PAD, PAD, PAD + lw + 44, PAD + 52), radius=26,
                        outline=CHIP, width=2)
    d.text((PAD + 22, PAD + 26), label, font=lf, fill=CHIP, anchor="lm")

    # 제목 — 3줄 안에 들어갈 때까지 줄인다
    text = _covered(title)
    for size in (76, 68, 60, 54, 48):
        tf = f800(size)
        lines = _wrap(d, text, tf, W - PAD * 2)
        if len(lines) <= 3:
            break
    lines = lines[:3]
    lh = int(size * 1.32)
    y = 200 + (3 - len(lines)) * lh // 2
    for ln in lines:
        d.text((PAD, y), ln, font=tf, fill=(255, 255, 255))
        y += lh

    # 하단 — 엠블럼 + 사무소명 / 도메인
    d.line((PAD, H - 128, W - PAD, H - 128), fill=(255, 255, 255, 60), width=1)
    x = PAD
    emblem = Path(current_app.static_folder) / "img" / "emblem.png"
    if emblem.exists():
        em = Image.open(emblem).convert("RGBA")
        em.thumbnail((60, 54))
        img.paste(em, (x, H - 98), em)
        x += em.width + 16
    d.text((x, H - 70), "법률사무소 레이", font=f800(36), fill=GOLD, anchor="lm")
    domain = SITE_DEFAULTS["base_url"].split("://")[-1]
    d.text((W - PAD, H - 70), domain, font=f600(26),
           fill=(255, 255, 255), anchor="rm")
    return img


def is_auto(path):
    return bool(path) and ("/%s/" % AUTO_DIR) in path


def make(post, label=None):
    """post 에 기본 썸네일을 붙인다(커밋은 호출자가). 경로를 돌려준다.

    파일명은 글 id — 제목을 고쳐 다시 그리면 같은 파일을 덮어쓴다.
    """
    if label is None:
        label = "진행 사례" if post.kind == "case" else "법률칼럼"
    absdir = Path(current_app.static_folder) / AUTO_DIR
    absdir.mkdir(parents=True, exist_ok=True)
    name = "%s-%d.jpg" % (post.kind or "post", post.id)
    render(post.title, label).save(absdir / name, "JPEG", quality=86,
                                   optimize=True, progressive=True)
    # 같은 경로를 덮어쓰면 브라우저·검색엔진 캐시가 옛 그림을 쥔다 — 버전 꼬리표
    ver = stable_hash(post.title) % 100000
    post.thumb_path = "/static/%s/%s?v=%d" % (AUTO_DIR, name, ver)
    post.thumb_alt = post.title[:200]
    return post.thumb_path


if __name__ == "__main__":
    # 자가 점검: 짧은·긴·서브셋 밖 글자 제목이 3줄 안에 그려지는지
    import sys
    from app import create_app
    app = create_app()
    with app.app_context():
        out = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
        for i, t in enumerate(["개인회생 중 이직하면 어떻게 되나요",
                               "수원 자영업자 개인회생, 사업을 계속하면서 빚을 정리할 수 있는지 꼼꼼하게 살펴봅니다",
                               "똠양꿍 뷁 개인파산 기간"]):
            im = render(t)
            assert im.size == (W, H)
            im.save(out / ("thumb-test-%d.jpg" % i), quality=86)
        print("OK", out)


# ── 본문 삽화(타입 1) ─────────────────────────────────────────────
_H2 = re.compile(r"(<h2>(.*?)</h2>)", re.S)
PHOTO_SIZE = {"hero-justice.webp": (1600, 1067), "bg-court.webp": (1600, 1067),
              "bg-library.webp": (1600, 1067), "consult.webp": (1200, 801),
              "books.webp": (1200, 800)}


def illustrate(body_html, title, n=2):
    """1번째·3번째 소제목 아래에 스톡 사진을 넣는다(대륜식 '대목차마다 사진').

    대표 이미지에 쓴 사진은 피하고, alt 는 '제목 — 소제목'으로 써서 이미지 검색에
    글 내용이 걸리게 한다. 소제목이 2개 이하면 1장만 넣는다.
    """
    hero = PHOTOS[stable_hash("photo::" + title) % len(PHOTOS)]
    pool = [p for p in PHOTOS if p != hero]
    start = stable_hash("ill::" + title) % len(pool)
    out, k, hits = [], 0, 0
    pos = 0
    for i, m in enumerate(_H2.finditer(body_html)):
        out.append(body_html[pos:m.end()])
        pos = m.end()
        if i in (0, 2) and hits < n:
            name = pool[(start + hits) % len(pool)]
            w, h = PHOTO_SIZE.get(name, (1600, 1067))
            sub = re.sub(r"<[^>]+>", "", m.group(2)).strip()
            alt = ("%s — %s" % (title, sub))[:120]
            out.append('<figure class="pic"><img src="/static/img/%s" alt="%s" '
                       'width="%d" height="%d" loading="lazy"></figure>'
                       % (name, alt.replace('"', "'"), w, h))
            hits += 1
    out.append(body_html[pos:])
    return "".join(out)
