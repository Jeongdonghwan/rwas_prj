"""블록·FAQ·문장 회전 헬퍼.

중복 콘텐츠 방지 전략: variant_set(A/B/C) 3값 회전 대신 **엔티티 이름을 시드로 한
FNV-1a 해시**로 블록·FAQ·문장을 고르게 분산시킨다. 블록이 키당 6종이면
본문 조합은 6×6×6 = 216가지, FAQ는 결정적 셔플로 순서·구성까지 달라진다.
같은 페이지는 항상 같은 결과(멱등) — 크롤러가 보는 내용이 요청마다 바뀌지 않는다.
"""

import hashlib

from flask import current_app
from jinja2 import Environment

from app.models import ContentBlock, Faq
from app.variants import POOLS


def stable_hash(s):
    """실행 간 고정 해시. 파이썬 hash()는 PYTHONHASHSEED 때문에 쓸 수 없다.

    **FNV-1a를 쓰지 않는 이유**: 하위 비트 확산이 약해 `% n`(n이 작을 때)이
    편향된다. 키 접미사가 'lf_sec1'/'lf_sec5'/'lf_sec9'처럼 끝 문자만 다르면
    (0x31·0x35·0x39는 모두 4로 나눈 나머지가 1) 세 키가 같은 변형을 골라
    두 페이지가 10개 섹션을 전부 공유하는 일이 실제로 발생했다.
    blake2b는 avalanche가 보장되므로 `% n`이 균등하다.
    """
    return int.from_bytes(
        hashlib.blake2b(str(s).encode("utf-8"), digest_size=8).digest(), "big"
    )


def pick(seed, key, options):
    """seed+key 해시로 options에서 하나 선택 (결정적)."""
    if not options:
        return None
    return options[stable_hash(f"{seed}::{key}") % len(options)]


def get_block(block_key, seed):
    rows = (
        ContentBlock.query.filter_by(block_key=block_key)
        .order_by(ContentBlock.variant)
        .all()
    )
    if not rows:
        return ""
    return pick(seed, block_key, rows).body_html


# 받침 유무로 갈리는 조사 쌍 — (받침 있음, 받침 없음)
JOSA_PAIRS = {
    "은는": ("은", "는"), "이가": ("이", "가"), "을를": ("을", "를"),
    "과와": ("과", "와"), "으로로": ("으로", "로"), "이라라": ("이라", "라"),
}


def josa(word, pair="은는"):
    """단어 뒤에 받침에 맞는 조사를 붙여 돌려준다.

        {{ site.firm_name|josa('은는') }} → '법률사무소 레이는'  (레이: 받침 없음)
        {{ '매탄동'|josa('은는') }}        → '매탄동은'          (동: 받침 있음)

    이름이 DB에서 오기 때문에 '레이은', '매탄동는' 같은 오류가 실제로 있었다.
    조사가 필요한 자리에는 반드시 이 필터를 쓸 것.
    """
    w = str(word or "")
    if not w:
        return w
    a, b = JOSA_PAIRS.get(pair, JOSA_PAIRS["은는"])
    code = ord(w[-1])
    if 0xAC00 <= code <= 0xD7A3:          # 한글 음절
        jong = (code - 0xAC00) % 28
        # 'ㄹ' 받침은 '로'를 쓴다 (서울로, 시청역으로)
        if jong == 8 and pair == "으로로":
            return w + b
        return w + (a if jong else b)
    if code in range(0x30, 0x3A):          # 숫자 — 읽는 소리 기준
        return w + (a if w[-1] in "0136780" else b)
    return w + b                            # 영문·기호는 받침 없음으로 처리


def render_tpl(text, **vars):
    """문장 풀·DB 템플릿 렌더. 앱의 jinja_env를 쓰는 이유는 josa 같은
    커스텀 필터를 풀 문장 안에서도 쓸 수 있게 하기 위함이다."""
    if not text:
        return ""
    try:
        return current_app.jinja_env.from_string(text).render(**vars)
    except RuntimeError:                    # 앱 컨텍스트 밖(스크립트 등)
        env = Environment(autoescape=True)
        env.filters["josa"] = josa
        return env.from_string(text).render(**vars)


def vtext(seed, key, rank=None, **vars):
    """POOLS[key] 문장 풀에서 하나 골라 변수 치환. 템플릿에서 직접 호출.

    rank를 주면 해시 대신 `(hash(key) + rank) % n`으로 고른다. 페이지 수가
    변형 수 이하인 유형(구 4개 × 변형 4개)에서 라틴 방진이 되어 **서로 다른
    페이지가 한 섹션도 겹치지 않는다**. 페이지가 더 많은 유형(동 31개)에
    쓰면 rank가 같은 페이지끼리 전부 겹치므로 그쪽은 rank 없이 해시를 쓴다.
    """
    pool = POOLS.get(key, [])
    if not pool:
        return ""
    t = pool[(stable_hash(key) + rank) % len(pool)] if rank is not None \
        else pick(seed, key, pool)
    return render_tpl(t, **vars)


def vlist(seed, key, count, **vars):
    """POOLS[key]를 결정적 셔플해 count개 반환 (리스트 항목 회전용)."""
    pool = POOLS.get(key, [])
    if not pool:
        return []
    ordered = sorted(pool, key=lambda t: stable_hash(f"{seed}::{key}::{t[:24]}"))
    return [render_tpl(t, **vars) for t in ordered[:count]]


def pick_faqs(scope, seed, count, kind="qa", **vars):
    """scope 풀을 seed로 결정적 셔플해 count개 선택, 변수 치환.

    회전(offset)이 아니라 셔플이라 페이지별로 질문 구성 자체가 달라진다.
    """
    pool = Faq.query.filter_by(scope=scope, kind=kind).order_by(Faq.sort).all()
    if not pool:
        return []
    ordered = sorted(pool, key=lambda f: stable_hash(f"{seed}::{kind}::{f.id}"))
    return [
        {
            "q": render_tpl(f.question_tpl, **vars),
            "a": render_tpl(f.answer_tpl, **vars),
        }
        for f in ordered[:count]
    ]
