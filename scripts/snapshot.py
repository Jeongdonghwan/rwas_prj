"""출력 스냅샷 — 리팩터링이 페이지를 바꾸지 않았음을 증명하는 용도.

지역 설정을 config로 뽑아내는 작업은 6,000곳이 넘는 문자열을 건드린다.
눈으로 훑어서는 한 글자 틀어진 걸 못 잡는다. 그래서 **작업 전에 찍고, 작업 후에
다시 찍어 비교한다.**

    python scripts/snapshot.py before.json     # 작업 전
    python scripts/snapshot.py after.json      # 작업 후
    python scripts/snapshot.py --diff before.json after.json

키워드 페이지는 11,952개 전부 돌면 오래 걸려서 결정적 표본만 쓴다
(`--sample`로 조절). 표본은 id 정렬 후 균등 간격이라 매번 같은 집합이다.
"""

import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SAMPLE = 400

# 사이트맵·RSS의 시각 필드. 소스 파일 mtime에서 나오므로 **코드를 고치면 당연히
# 바뀐다.** 이것까지 FAIL로 잡으면 게이트가 매번 울려서 쓸모가 없어진다.
# 그래서 본문 해시와 따로 기록해 "시각만 바뀜"과 "내용이 바뀜"을 구분한다.
# 응답을 bytes 그대로 해싱하므로 패턴도 bytes여야 한다
TIME_FIELDS = re.compile(
    rb"<lastmod>.*?</lastmod>|<pubDate>.*?</pubDate>|<lastBuildDate>.*?</lastBuildDate>",
    re.S,
)


def fixed_paths():
    return [
        "/", "/about/", "/contact/", "/process/", "/faq/",
        "/service/rehab/", "/service/bankruptcy/", "/service/cost/", "/service/docs/",
        "/privacy/", "/email-policy/",
        "/지역별-개인회생/", "/직업별-개인회생/", "/상황별-개인회생/",
        "/사례/", "/모아보기/",
        "/robots.txt", "/sitemap.xml", "/sitemap-pages.xml",
        "/sitemap-area.xml", "/sitemap-job.xml", "/sitemap-case.xml", "/rss.xml",
    ]


def build(out_path, sample=SAMPLE):
    from app import create_app
    from app.models import CaseType, Dong, Gu, Job, Keyword

    app = create_app()
    client = app.test_client()
    shots, missing = {}, []

    with app.app_context():
        paths = list(fixed_paths())
        for gu in Gu.query.order_by(Gu.sort).all():
            paths.append("/%s-개인회생/" % gu.name)
        for d in Dong.query.order_by(Dong.sort).all():
            paths.append("/%s-개인회생/" % d.name)
        for j in Job.query.order_by(Job.sort).all():
            paths.append("/%s-개인회생/" % (j.slug_ko or j.slug))
        for c in CaseType.query.order_by(CaseType.sort).all():
            paths.append("/%s-개인회생/" % (c.slug_ko or c.slug))

        # 키워드는 균등 간격 표본 — 매 실행 같은 집합이 나와야 비교가 된다
        rows = Keyword.query.order_by(Keyword.id).all()
        if rows:
            step = max(1, len(rows) // sample)
            paths += ["/%s/" % r.slug_ko for r in rows[::step][:sample]]

    for p in paths:
        r = client.get(p)
        if r.status_code != 200:
            missing.append((p, r.status_code))
            continue
        body = r.get_data()
        full = hashlib.blake2b(body, digest_size=16).hexdigest()
        # HTML은 공백을 접어서 비교한다. 템플릿에 {% if %}를 넣으면 빈 줄이
        # 생기는데 그것까지 FAIL로 잡으면 게이트가 매번 울려 쓸모가 없어진다.
        # 글자가 바뀌면 여전히 잡힌다.
        core = hashlib.blake2b(
            b" ".join(body.split()), digest_size=16
        ).hexdigest()
        if p.endswith(".xml"):
            core = hashlib.blake2b(
                b" ".join(TIME_FIELDS.sub(b"", body).split()), digest_size=16
            ).hexdigest()
        shots[p] = [full, core]

    Path(out_path).write_text(
        json.dumps({"shots": shots, "missing": missing}, ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    print("페이지 %d개 기록 → %s" % (len(shots), out_path))
    if missing:
        print("200이 아닌 경로 %d개: %s" % (len(missing), missing[:5]))
    return shots


def diff(a_path, b_path):
    a = json.loads(Path(a_path).read_text(encoding="utf-8"))["shots"]
    b = json.loads(Path(b_path).read_text(encoding="utf-8"))["shots"]
    def core(v):
        """시각 필드를 뺀 본문 해시. 구버전 스냅샷(문자열)도 읽을 수 있게 둔다."""
        return v[1] if isinstance(v, list) else v

    only_a = sorted(set(a) - set(b))
    only_b = sorted(set(b) - set(a))
    both = set(a) & set(b)
    changed = sorted(k for k in both if core(a[k]) != core(b[k]))
    time_only = sorted(k for k in both if core(a[k]) == core(b[k]) and a[k] != b[k])

    print("기준 %d개 / 비교 %d개" % (len(a), len(b)))
    print("  사라진 경로   : %d" % len(only_a))
    print("  새 경로       : %d" % len(only_b))
    print("  내용 바뀜     : %d" % len(changed))
    print("  시각만 바뀜   : %d  (사이트맵 lastmod — 소스를 고쳤으면 정상)"
          % len(time_only))
    for k in (only_a + only_b + changed)[:20]:
        print("    %s" % k)
    ok = not (only_a or only_b or changed)
    print("\n%s" % ("PASS — 본문이 동일하다" if ok else "FAIL — 위 경로를 확인할 것"))
    return 0 if ok else 1


if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] == "--diff":
        sys.exit(diff(args[1], args[2]))
    build(args[0] if args else "snapshot.json")
