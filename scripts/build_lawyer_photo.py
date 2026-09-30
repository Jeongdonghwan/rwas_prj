# -*- coding: utf-8 -*-
"""대표변호사 사진 보정·리사이즈.

    python scripts/build_lawyer_photo.py

원본(Downloads/CSY_5372/CSY_5372.JPG)은 **EXIF 회전이 걸려 있다.**
`ImageOps.exif_transpose`를 빼먹으면 가로로 읽혀 엉뚱한 곳을 자르게 된다.

원본 상태: 배경 회색 벽이 균일하지 않고(밝기 148~197) 전체적으로 어둡고 차갑다.
보정은 감마로 중간톤을 올리고, 가장자리만 살짝 들어 비네팅을 완화하고,
아주 약하게 따뜻하게 민다. 강하게 하면(감마 .80 이상) 배경이 한쪽만 날아가
부자연스러워진다 — 실제로 비교해보고 아래 값으로 정했다.

산출물
    lawyer-card.webp  720x900  (4:5, y180부터 크롭) — 소개·메인·동 페이지
    lawyer-900.webp   900x1350 (2:3 원본 비율)
    lawyer-480.webp   480x720  (2:3, 모바일)
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter, ImageOps

SRC = Path.home() / "Downloads" / "CSY_5372" / "CSY_5372.JPG"
OUT = Path(__file__).resolve().parent.parent / "app" / "static" / "img"

# 비교 끝에 정한 값. 더 올리면 배경이 한쪽만 날아간다.
GAMMA, BRIGHT, CONTRAST = 0.86, 1.09, 1.09
WARM = (1.025, 1.0, 0.985)
EDGE_LIFT = 0.09          # 가장자리(배경) 비네팅 완화
CROP_TOP = 180            # 머리 위 여백이 커서 잘라낸다


def tone(im):
    a = np.asarray(im).astype(np.float32) / 255.0
    a = np.power(a, GAMMA)
    h, w, _ = a.shape
    yy, xx = np.mgrid[0:h, 0:w]
    r = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2)
    a = a + np.clip((r - 0.55) / 0.85, 0, 1)[..., None] * EDGE_LIFT
    a = np.clip(a, 0, 1)
    for i, k in enumerate(WARM):
        a[..., i] *= k
    im = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))
    im = ImageEnhance.Brightness(im).enhance(BRIGHT)
    im = ImageEnhance.Contrast(im).enhance(CONTRAST)
    return im.filter(ImageFilter.UnsharpMask(radius=2, percent=42, threshold=3))


def main():
    if not SRC.exists():
        sys.exit("원본이 없습니다: %s" % SRC)
    full = ImageOps.exif_transpose(Image.open(SRC)).convert("RGB")
    print("원본 %s (EXIF 회전 적용)" % (full.size,))

    base = tone(full)
    card = tone(full.crop((0, CROP_TOP, full.width, CROP_TOP + int(full.width * 1.25))))

    for name, im, size in [
        ("lawyer-card.webp", card, (720, 900)),
        ("lawyer-900.webp", base, (900, 1350)),
        ("lawyer-480.webp", base, (480, 720)),
    ]:
        p = OUT / name
        im.resize(size, Image.LANCZOS).save(p, "WEBP", quality=88, method=6)
        print("  %-20s %s  %5.0f KB" % (name, size, p.stat().st_size / 1024))


if __name__ == "__main__":
    main()
