# -*- coding: utf-8 -*-
"""Pretendard woff2를 한국어 상용 글자로 서브셋해 self-host 파일을 만든다.

    python scripts/build_fonts.py

**왜 필요한가**: CDN의 pretendard.min.css에는 unicode-range가 없어서 브라우저가
쓰이는 굵기마다 **전체 한글 글리프(굵기당 약 750KB)** 를 통째로 받는다.
400·600·700·800 네 굵기를 쓰므로 첫 방문에 약 3MB가 폰트로만 나간다.
게다가 CSS @import라 site.css를 다 받은 뒤에야 폰트 CSS를 발견하는 직렬 체인이었다.

**서브셋 기준**: EUC-KR(KS X 1001) 상용 한글 2,350자 + 사이트에서 실제 쓰이는 글자
+ 라틴/숫자/문장부호/기호. 어드민에서 새 글을 써도 일반적인 한국어는 모두 커버된다.
(KS X 1001 밖 희귀 음절이 필요해지면 FALLBACK_TEXT에 추가하고 다시 돌릴 것.)

원본 woff2는 저장소에 넣지 않는다 — 이 스크립트가 CDN에서 받아 서브셋만 남긴다.
"""
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "app" / "static" / "fonts"
CDN = ("https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9"
       "/packages/pretendard/dist/web/static/woff2")

# (파일명, CSS font-weight) — site.css가 쓰는 굵기만
WEIGHTS = [("Regular", 400), ("SemiBold", 600), ("Bold", 700), ("ExtraBold", 800)]

EXTRA = (
    " !\"#$%&'()*+,-./0123456789:;<=>?@"
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`"
    "abcdefghijklmnopqrstuvwxyz{|}~"
    "·—–…※⁄∼~「」『』〈〉《》【】"
    "①②③④⑤⑥⑦⑧⑨⑩→←↑↓✓✔※○●◦□■◇◆★☆"
    "₩$€¥%‰°㎡㎞㎏±×÷≤≥≠∞"
    "“”‘’″′"
)


def korean_common():
    """KS X 1001 완성형 상용 한글 2,350자.

    주의: 파이썬의 'euc-kr' 코덱은 실제로 CP949라 한글 11,172자를 전부 통과시킨다.
    그래서 인코딩 성공 여부가 아니라 **바이트 영역**으로 걸러야 한다 —
    KS X 1001 한글은 선두 0xB0~0xC8, 후미 0xA1~0xFE 구간에 있다.
    """
    out = []
    for cp in range(0xAC00, 0xD7A4):
        ch = chr(cp)
        try:
            b = ch.encode("euc-kr")
        except UnicodeEncodeError:
            continue
        if len(b) == 2 and 0xB0 <= b[0] <= 0xC8 and b[1] >= 0xA1:
            out.append(ch)
    return "".join(out)


def site_chars():
    """사이트가 실제로 렌더하는 모든 글자(있으면 사용)."""
    p = ROOT / "scripts" / "_used_chars.txt"
    return p.read_text(encoding="utf-8") if p.exists() else ""


def main():
    try:
        from fontTools import subset  # noqa: F401
    except ImportError:
        sys.exit("fonttools가 없습니다:  pip install fonttools brotli")

    OUT.mkdir(parents=True, exist_ok=True)
    text = "".join(sorted(set(korean_common() + site_chars() + EXTRA)))
    print("서브셋 대상 글자수: %d" % len(text))

    txt_path = OUT / "_subset.txt"
    txt_path.write_text(text, encoding="utf-8")

    total_before = total_after = 0
    for name, weight in WEIGHTS:
        src = OUT / ("Pretendard-%s.woff2" % name)
        if not src.exists():
            url = "%s/Pretendard-%s.woff2" % (CDN, name)
            print("  내려받는 중: %s" % url)
            urllib.request.urlretrieve(url, src)
        before = src.stat().st_size
        dst = OUT / ("pretendard-%d.woff2" % weight)
        subprocess.run([
            sys.executable, "-m", "fontTools.subset", str(src),
            "--text-file=%s" % txt_path,
            "--output-file=%s" % dst,
            "--flavor=woff2",
            "--layout-features=*",
            "--no-hinting",
            "--desubroutinize",
        ], check=True)
        after = dst.stat().st_size
        total_before += before
        total_after += after
        print("  %-10s %7.0f KB → %6.0f KB" % (name, before / 1024, after / 1024))
        src.unlink()          # 원본(750KB)은 저장소에 남기지 않는다

    txt_path.unlink()
    print("합계 %.1f MB → %.0f KB (%.0f%% 감소)"
          % (total_before / 1048576, total_after / 1024,
             (1 - total_after / total_before) * 100))


if __name__ == "__main__":
    main()
