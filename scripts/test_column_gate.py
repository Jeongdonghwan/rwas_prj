# -*- coding: utf-8 -*-
"""칼럼 검증 게이트가 실제로 막는지 확인한다.

    python scripts/test_column_gate.py

자동 생성 글이 통과하는 것만 보면 게이트가 아무것도 안 막는지 알 수 없다.
일부러 나쁜 글을 넣어 각 규칙이 걸리는지 본다. API 호출 없음.
"""
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from app import create_app  # noqa: E402

KW = SimpleNamespace(keyword="개인회생 진행 중 이직하면 어떻게 되나요",
                     area="", scheme="개인회생", category="상황변화", intent="")


def article(**over):
    """기본은 통과하는 글. over 로 한 군데만 망가뜨린다."""
    body = ("<p>개인회생 중 이직해도 절차는 이어집니다. 소득이 바뀌면 법원에 알리고 "
            "변제계획 변경을 검토합니다.</p>"
            + "".join("<h2>소제목 %d</h2><p>%s</p>" % (i, "이직 후 소득 변동을 정리합니다. " * 22)
                      for i in range(3))
            + '<p><a href="/service/rehab/">신청자격</a> · <a href="/process/">절차</a> · '
              '<a href="/contact/">상담</a></p>')
    d = {"title": "개인회생 중 이직하면 달라지는 것",
         "excerpt": "개인회생 중 이직해도 절차는 이어지지만 소득 변동은 법원에 알려야 합니다. 확인할 것을 정리합니다.",
         "body_html": body}
    d.update(over)
    return d


def main():
    from app.column_writer import validate

    app = create_app()
    cases = [
        ("정상 글", {}, None),
        ("금칙어 '무조건'", {"body_html": article()["body_html"]
                             .replace("이어집니다", "무조건 면책됩니다")}, "금칙어"),
        ("금칙어 '무료'", {"excerpt": "무료 상담으로 개인회생 이직 문제를 확인하세요. 소득 변동 신고 방법을 정리합니다."}, "금칙어"),
        ("없는 수치 '7년'", {"body_html": article()["body_html"]
                               .replace("이어집니다", "7년 동안 이어집니다")}, "수치"),
        ("없는 금액 '300만원'", {"body_html": article()["body_html"]
                                 .replace("이어집니다", "300만원이 듭니다")}, "수치"),
        ("외부 링크", {"body_html": article()["body_html"]
                       .replace('/process/', 'https://evil.example/')}, "내부링크"),
        ("없는 내부 경로", {"body_html": article()["body_html"]
                            .replace('/process/', '/없는경로/')}, "없는 경로"),
        ("너무 짧음", {"body_html": "<p>짧다</p><h2>a</h2><h2>b</h2><h2>c</h2>"}, "본문"),
        ("스크립트 주입", {"body_html": article()["body_html"]
                          + "<script>alert(1)</script>"}, None),
        ("제목에 핵심어 없음", {"title": "알아두면 좋은 이야기"}, "제목"),
        # 모델이 요약을 80자 넘게 쓰는 일이 잦다 — 버리지 않고 다듬어 통과시켜야 한다
        ("긴 요약 90자", {"excerpt": "개인회생 중 이직해도 절차는 계속되지만 소득이 바뀌면 법원에 알려야 합니다. "
                                    "변제계획 변경 여부와 필요한 서류, 놓치기 쉬운 신고 시점을 함께 정리했습니다."}, None),
    ]

    fail = 0
    with app.app_context(), app.test_request_context():
        for name, over, must in cases:
            errs, out = validate(KW, article(**over), [])
            joined = " / ".join(errs)
            if must is None:
                ok = not errs
                if name == "스크립트 주입":
                    ok = ok and "<script" not in out["body_html"]
                if name.startswith("긴 요약"):
                    ok = ok and len(out["excerpt"]) <= 79
            else:
                ok = must in joined
            fail += not ok
            print("  %s %-16s %s" % ("✓" if ok else "✗", name, joined or "통과"))

    print("\n%s" % ("PASS — 게이트가 전부 제대로 막는다" if not fail
                    else "FAIL %d건" % fail))
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
