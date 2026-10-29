# -*- coding: utf-8 -*-
"""OpenAI 호출 오류 처리 점검 — 실제 API 는 부르지 않는다.

    python scripts/test_column_api.py

① 429(분당 한도)는 기다렸다 다시 시도 ② 크레딧 소진(insufficient_quota)은 즉시 중단(fatal)
③ 429 가 계속되면 3번 기다린 뒤 비치명 실패.
"""
import io
import json
import os
import sys
import urllib.error
from email.message import Message
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
os.environ.setdefault("OPENAI_API_KEY", "test")

import app.column_writer as W  # noqa: E402


def http(code, body, retry_after=None):
    h = Message()
    if retry_after:
        h["Retry-After"] = retry_after
    return urllib.error.HTTPError(W.API, code, "x", h, io.BytesIO(json.dumps(body).encode()))


def serve(seq):
    it = iter(seq)

    def urlopen(req, timeout=0):
        x = next(it)
        if isinstance(x, Exception):
            raise x
        return io.BytesIO(json.dumps({"choices": [{"message": {"content": '{"title": "t"}'}}],
                                      "usage": {}}).encode())
    return urlopen


def main():
    waits = []
    W.urllib.request.urlopen = serve([http(429, {"error": {"code": "rate_limit_exceeded"}}, "5"),
                                      http(429, {"error": {}}), None])
    data, _ = W.call_gpt("s", "u", sleep=waits.append)
    assert data == {"title": "t"} and waits == [20, 60], waits

    waits.clear()
    W.urllib.request.urlopen = serve([http(429, {"error": {"code": "insufficient_quota"}})])
    try:
        W.call_gpt("s", "u", sleep=waits.append)
        raise AssertionError("크레딧 소진인데 통과했다")
    except W.ApiError as e:
        assert e.fatal and waits == [], (e, waits)

    waits.clear()
    W.urllib.request.urlopen = serve([http(429, {"error": {}})] * 4)
    try:
        W.call_gpt("s", "u", sleep=waits.append)
        raise AssertionError("계속 429 인데 통과했다")
    except W.ApiError as e:
        assert not e.fatal and waits == [20, 60, 120], waits

    print("PASS — 429 재시도 · 크레딧 소진 즉시 중단 · 계속 429 면 비치명 실패")


if __name__ == "__main__":
    main()
