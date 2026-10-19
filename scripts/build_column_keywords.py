# -*- coding: utf-8 -*-
"""법률칼럼 키워드 — **문의로 이어지는 것만** 고른다.

    python scripts/build_column_keywords.py            # 미리보기
    python scripts/build_column_keywords.py --write    # seed/column_keywords.csv

## 선별 원칙 (2026-10 재설계)

1. **문의가 나오는 제도에 집중한다.** 개인회생·개인파산은 변호사가 하는 일이다.
   신용회복·워크아웃은 위원회에 직접 가는 제도라 그 검색자는 사무소로 잘 안 온다
   — 그래서 단독으로는 안 쓰고 **"신용회복 하다가 개인회생으로"** 같은 비교·전환
   주제로만 쓴다. 그 검색자를 사무소로 끌어오는 자리다.

2. **조합이 핵심이다.** 사람은 "수원 직장인 개인회생", "간호사 개인회생 사례",
   "도박빚 개인회생 가능"처럼 **자기 처지**로 검색한다.
   지역×직업 / 지역×상황 / 지역·직업·상황×사례 / 직업·상황×질문.

3. **말이 돼야 한다.** 예전 키워드는 제도명을 기계적으로 바꿔 끼워
   "신용회복 중 이사하면 법원이 바뀌나요"(위원회 절차에 법원) 같은 틀린 말과
   "보증채무가 있을 때 개인회생"(문장이 끊김) 같은 어색한 말이 170개 넘게 있었다.
   이제 템플릿마다 **쓸 수 있는 제도를 직접 지정**하고, 검색어처럼 짧게 쓴다.

4. **'사례'는 지어내지 않는다.** 키워드는 "직장인 개인회생 사례"여도 글은
   "이런 처지에서 보통 어떻게 되는가"를 설명한다. 실제 사건처럼 쓰면 허위광고다
   (작성기 프롬프트·검증 게이트가 막는다).

5. 양산 페이지(seed/keyword.csv)와 **똑같은 키워드는 뺀다** — 자기 사이트끼리 경쟁한다.
   광고규정상 위험한 말(후기·추천·잘하는 곳·1위·무료)은 키워드에도 안 넣는다.
"""
import argparse
import collections
import csv
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT = ROOT / "seed" / "column_keywords.csv"

R, P = "개인회생", "개인파산"

# ── 검색어로 쓰는 직업·상황 이름 ─────────────────────────────────
# DB 이름("프리랜서(3.3%)", "택시·버스·화물 기사")은 화면용이라 검색어로는 어색하다.
# (검색어, 묶음) — 묶음에 따라 붙일 질문이 다르다.
JOBS = [
    ("직장인", "급여"), ("공무원", "공직"), ("교사", "공직"), ("군인", "공직"),
    ("간호사", "면허"), ("금융권 종사자", "금융"),
    ("자영업자", "사업"), ("소상공인", "사업"), ("법인 대표", "사업"),
    ("프리랜서", "불규칙"), ("배달라이더", "불규칙"), ("택시기사", "불규칙"),
    ("화물차 기사", "불규칙"), ("건설 일용직", "불규칙"),
    ("주부", "무소득"), ("무직자", "무소득"), ("대학생", "무소득"), ("은퇴자", "무소득"),
]
# 소득이 없거나 끊긴 직업은 파산이 맞는 경우가 많다 → 개인파산도 붙인다
JOB_ALSO_P = {"무소득", "사업"}

# 구 단위(또는 도산레이의 17개 시도)에는 **수요가 큰 직업·상황만** 조합한다.
# 전부 조합하면 "장안구 군인 개인회생" "권선구 군인 개인회생"처럼 지역만 다르고
# 할 말이 같은 글이 4~17번 반복된다 — 칼럼으로 피하려던 양산형 그 자체다.
TOP_JOBS = ["직장인", "자영업자", "프리랜서", "공무원", "주부", "무직자"]
TOP_JOBS_GU = ["직장인", "자영업자", "프리랜서"]
TOP_CASES = ["카드빚", "대출 돌려막기", "도박빚", "사업 실패", "코인 손실"]
TOP_CASES_GU = ["카드빚", "대출 돌려막기", "도박빚"]

CASES = [
    ("도박빚", True), ("코인 손실", True), ("주식 손실", True),
    ("카드빚", True), ("대출 돌려막기", True), ("사업 실패", True),
    ("보증빚", True), ("이혼 빚", True), ("병원비", True),
]  # (검색어, 개인파산도 붙일지)

# ── 템플릿 ─────────────────────────────────────────────────────
# (분류, 템플릿, 쓸 제도들, 검색의도)
# {r}=지역 {j}=직업 {c}=상황 {s}=제도

COMBO_REGION_JOB = ("지역직업", "{r} {j} {s}", "처지 맞춤 상담 탐색")
COMBO_REGION_CASE = ("지역상황", "{r} {c} {s}", "처지 맞춤 상담 탐색")
REGION_CASE_STUDY = ("지역사례", "{r} {s} 사례", "비슷한 사례 탐색")
JOB_CASE_STUDY = ("직업사례", "{j} {s} 사례", "비슷한 사례 탐색")
CASE_CASE_STUDY = ("상황사례", "{c} {s} 사례", "비슷한 사례 탐색")
REGION_JOB_STUDY = ("지역직업사례", "{r} {j} {s} 사례", "비슷한 사례 탐색")

# 직업 묶음별 질문 — 그 직업 사람이 실제로 걱정하는 것만
JOB_Q = {
    "급여": ["{j} {s} 회사에 알려지나요", "{j} {s} 월급 압류 풀리나요",
             "{j} {s} 변제금 계산", "{j} {s} 중 이직하면"],
    "공직": ["{j} {s} 징계 받나요", "{j} {s} 소속 기관에 알려지나요",
             "{j} {s} 승진 불이익 있나요", "{j} {s} 신청 전 확인할 것"],
    # 간호사는 징계보다 면허가 걱정이다
    "면허": ["{j} {s} 면허에 영향 있나요", "{j} {s} 병원에 알려지나요",
             "{j} {s} 야간수당도 소득에 들어가나요", "{j} {s} 신청 전 확인할 것"],
    "금융": ["{j} {s} 회사에 알려지나요", "{j} {s} 해고 사유 되나요",
             "{j} {s} 성과급도 소득에 들어가나요", "{j} {s} 신청 전 확인할 것"],
    "사업": ["{j} {s} 사업 계속할 수 있나요", "{j} {s} 소득 증명 방법",
             "{j} {s} 폐업 후 신청", "{j} {s} 사업자 대출도 되나요"],
    "불규칙": ["{j} {s} 소득 증명 방법", "{j} {s} 수입이 들쑥날쑥할 때",
               "{j} {s} 가능할까요", "{j} {s} 변제금 정하는 기준"],
    "무소득": ["{j} {s} 가능할까요", "{j} {s} 소득 없을 때",
               "{j} {s} 신청 방법", "{j} {s} 가족 재산 영향"],
}

# 상황별 질문
CASE_Q = ["{c} {s} 가능할까요", "{c} {s} 면책되나요", "{c} {s} 기각 사유",
          "{c} {s} 준비 서류", "{c} {s} 신청 전 주의할 점"]
# 개인회생에는 '면책'보다 '인가'가 맞는 표현 → 따로 둔다
CASE_Q_R_ONLY = ["{c} {s} 변제금 계산"]

# 생활 사건 질문 — 제도를 템플릿마다 지정한다(법원 용어는 회생·파산에만)
LIFE = [
    # (분류, 템플릿, 제도)
    ("진행중변화", "{s} 중 이직하면 어떻게 되나요", [R]),
    ("진행중변화", "{s} 중 퇴사하면 변제는", [R]),
    ("진행중변화", "{s} 중 월급이 오르면 변제금도 오르나요", [R]),
    ("진행중변화", "{s} 중 소득이 끊기면", [R]),
    ("진행중변화", "{s} 중 결혼하면 배우자 소득 반영되나요", [R]),
    ("진행중변화", "{s} 중 이혼하면", [R, P]),
    ("진행중변화", "{s} 중 이사하면 법원이 바뀌나요", [R, P]),
    ("진행중변화", "{s} 중 출산하면 변제금 줄어드나요", [R]),
    ("진행중변화", "{s} 변제금 한 번 밀리면", [R]),
    ("진행중변화", "{s} 중 추가 대출 받으면", [R, P]),

    ("생활영향", "{s} 하면 회사에 알려지나요", [R, P]),
    ("생활영향", "{s} 하면 가족이 알게 되나요", [R, P]),
    ("생활영향", "{s} 중 전세 계약 가능한가요", [R, P]),
    ("생활영향", "{s} 중 자동차 계속 탈 수 있나요", [R, P]),
    ("생활영향", "{s} 중 체크카드 쓸 수 있나요", [R, P]),
    ("생활영향", "{s} 중 휴대폰 할부 되나요", [R, P]),
    ("생활영향", "{s} 중 해외여행 가능한가요", [R, P]),
    ("생활영향", "{s} 중 보험 유지할 수 있나요", [R, P]),
    ("생활영향", "{s} 하면 자녀 취업에 영향 있나요", [R, P]),
    ("생활영향", "{s} 하면 통장 막히나요", [R, P]),

    ("주의사항", "{s} 직전 대출 받으면 문제 되나요", [R, P]),
    ("주의사항", "{s} 전에 재산 정리하면 안 되는 이유", [R, P]),
    ("주의사항", "{s} 채권자 목록에서 빠뜨리면", [R, P]),
    ("주의사항", "{s} 전 가족에게 먼저 갚으면", [R, P]),
    ("주의사항", "{s} 신청 전 카드 쓰면", [R, P]),
    ("주의사항", "{s} 소득 적게 신고하면", [R]),
    ("주의사항", "{s} 전에 차 팔아도 되나요", [R, P]),
    ("주의사항", "{s} 보정명령 받았을 때", [R, P]),

    ("이후관리", "{s} 끝나면 신용은 언제 회복되나요", [R, P]),
    ("이후관리", "{s} 후 대출은 언제부터", [R, P]),
    ("이후관리", "{s} 후 신용카드 다시 만들 수 있나요", [R, P]),
    ("이후관리", "{s} 기록 얼마나 남나요", [R, P]),
    ("이후관리", "{s} 후 전세대출 되나요", [R, P]),
    ("이후관리", "{s} 면책 후 다시 어려워지면", [R, P]),

    ("재산채무", "전세보증금 있으면 {s} 불리한가요", [R, P]),
    ("재산채무", "퇴직금도 {s} 재산에 들어가나요", [R, P]),
    ("재산채무", "보험 해약환급금 {s} 영향", [R, P]),
    ("재산채무", "자동차 있으면 {s} 어떻게 되나요", [R, P]),
    ("재산채무", "청약통장 {s} 재산인가요", [R, P]),
    ("재산채무", "대부업 빚도 {s} 되나요", [R, P]),
    ("재산채무", "지인에게 빌린 돈도 {s} 되나요", [R, P]),
    ("재산채무", "세금 체납 있으면 {s}", [R, P]),
    ("재산채무", "학자금 대출도 {s} 되나요", [R, P]),
    ("재산채무", "보증 선 빚도 {s} 되나요", [R, P]),
    ("재산채무", "월급 압류됐는데 {s} 하면 풀리나요", [R, P]),
    ("재산채무", "소송 들어왔는데 {s} 늦은 건가요", [R, P]),

    ("결정판단", "{s} 언제 시작해야 하나요", [R, P]),
    ("결정판단", "{s} 미루면 생기는 일", [R, P]),
    ("결정판단", "돌려막기 중이라면 {s} 고민할 때", [R]),
    ("결정판단", "이자만 갚고 있다면 {s}", [R]),
    ("결정판단", "빚이 얼마부터 {s} 하나요", [R, P]),
    ("결정판단", "집 있어도 {s} 되나요", [R, P]),
    ("결정판단", "소득 적어도 {s} 되나요", [R]),
    ("결정판단", "{s} 혼자 하면 어려운 점", [R, P]),

    ("상담비용", "{s} 상담 전에 준비할 것", [R, P]),
    ("상담비용", "{s} 상담에서 꼭 물어볼 것", [R, P]),
    ("상담비용", "{s} 비대면 진행 되나요", [R, P]),
    ("상담비용", "{s} 비용 나눠 낼 수 있나요", [R, P]),
    ("상담비용", "{s} 기간 얼마나 걸리나요", [R, P]),

    ("오해정정", "{s} 하면 빚이 전부 없어지나요", [R, P]),
    ("오해정정", "{s} 하면 평생 대출 못 받나요", [R, P]),
    ("오해정정", "{s} 하면 직장 잃나요", [R, P]),
    ("오해정정", "{s} 한 번만 할 수 있나요", [R, P]),
    ("오해정정", "{s} 신용불량자만 하나요", [R, P]),
]

# 신용회복·워크아웃·채무조정 검색자를 사무소로 데려오는 자리 — 비교·전환형만
COMPARE = [
    "신용회복과 {s} 차이", "워크아웃과 {s} 뭐가 나을까요",
    "신용회복 하다가 {s}으로 바꿀 수 있나요", "워크아웃 실패 후 {s}",
    "채무조정 거절되면 {s}", "신용회복 중 {s} 신청 가능한가요",
    "새출발기금과 {s} 차이", "{s}과 개인파산 중 뭘 해야 하나요",
]

# 시도 → 검색에 쓰는 짧은 이름 (도산레이). "대전광역시 개인회생"은 아무도 안 친다
SIDO_SHORT = {
    "서울특별시": "서울", "부산광역시": "부산", "대구광역시": "대구",
    "인천광역시": "인천", "광주광역시": "광주", "대전광역시": "대전",
    "울산광역시": "울산", "세종특별자치시": "세종", "경기도": "경기",
    "강원특별자치도": "강원", "충청북도": "충북", "충청남도": "충남",
    "전북특별자치도": "전북", "전라남도": "전남", "경상북도": "경북",
    "경상남도": "경남", "제주특별자치도": "제주",
}

BANNED_IN_KW = ("후기", "추천", "잘하는", "1위", "무료", "최고", "싼 곳", "저렴한 곳")


def _dong_label(city, dong):
    """두 글자 동은 일반 단어와 겹친다(이동·사동·평동) → 도시명을 붙인다."""
    return "%s %s" % (city, dong) if len(dong) <= 2 else dong


def regions():
    """(도시급, 구급, 동급) 지역 이름. 도산레이는 시도가 도시급이다."""
    from app.config import REGION
    from app.models import Dong, Gu

    gus = [g.name for g in Gu.query.order_by(Gu.sort).all()]
    if REGION.get("area_mode") == "sido":
        return [SIDO_SHORT.get(g, g) for g in gus], [], []
    city = REGION["name"]
    dongs = [_dong_label(city, d.name) for d in Dong.query.order_by(Dong.sort).all()]
    # 구 이름은 시를 안 붙인다 — 사람은 "영통구 직장인 개인회생"으로 검색하고,
    # 이 사이트들의 구(장안·영통·상록·단원·처인·수지·분당 …)는 다른 도시와 안 겹친다
    return [city], gus, dongs


def build():
    cities, gus, dongs = regions()
    upper = cities + gus           # 시·구 — 조합 키워드에 쓴다
    rows = []

    def add(cat, kw, scheme, area, intent):
        rows.append((cat, kw.strip(), scheme, area, intent))

    multi_city = len(cities) > 1         # 도산레이: 17개 시도가 각각 '시'다

    def jobs_for(level):
        if level == "city" and not multi_city:
            return JOBS
        names = TOP_JOBS if level == "city" else TOP_JOBS_GU
        return [(j, g) for j, g in JOBS if j in names]

    def cases_for(level):
        if level == "city" and not multi_city:
            return CASES
        names = TOP_CASES if level == "city" else TOP_CASES_GU
        return [(c, p) for c, p in CASES if c in names]

    levels = [(r, "city") for r in cities] + [(r, "gu") for r in gus]

    # 1) 지역×직업
    cat, tpl, intent = COMBO_REGION_JOB
    for r, lv in levels:
        for j, grp in jobs_for(lv):
            add(cat, tpl.format(r=r, j=j, s=R), R, r, intent)
            if grp in JOB_ALSO_P and lv == "city":
                add(cat, tpl.format(r=r, j=j, s=P), P, r, intent)

    # 2) 지역×상황
    cat, tpl, intent = COMBO_REGION_CASE
    for r, lv in levels:
        for c, also_p in cases_for(lv):
            add(cat, tpl.format(r=r, c=c, s=R), R, r, intent)
            if also_p and lv == "city":
                add(cat, tpl.format(r=r, c=c, s=P), P, r, intent)

    # 3) 지역×사례 — 동 단위까지(동네 이름으로 비슷한 사례를 찾는 검색이 실제로 있다)
    cat, tpl, intent = REGION_CASE_STUDY
    for r in upper + dongs:
        add(cat, tpl.format(r=r, s=R), R, r, intent)
    for r in upper:
        add(cat, tpl.format(r=r, s=P), P, r, intent)

    # 4) 직업×사례, 5) 상황×사례
    cat, tpl, intent = JOB_CASE_STUDY
    for j, grp in JOBS:
        add(cat, tpl.format(j=j, s=R), R, "", intent)
        if grp in JOB_ALSO_P:
            add(cat, tpl.format(j=j, s=P), P, "", intent)
    cat, tpl, intent = CASE_CASE_STUDY
    for c, also_p in CASES:
        add(cat, tpl.format(c=c, s=R), R, "", intent)
        if also_p:
            add(cat, tpl.format(c=c, s=P), P, "", intent)

    # 6) 지역×직업×사례 — 수요 큰 직업만
    cat, tpl, intent = REGION_JOB_STUDY
    for r, lv in levels:
        for j, _ in jobs_for("gu" if lv == "gu" else ("city" if multi_city else "gu")):
            add(cat, tpl.format(r=r, j=j, s=R), R, r, intent)

    # 7) 직업×질문
    for j, grp in JOBS:
        for q in JOB_Q[grp]:
            add("직업질문", q.format(j=j, s=R), R, "", "직업별 걱정 해소")
        if grp in JOB_ALSO_P:
            for q in JOB_Q[grp][:2]:
                add("직업질문", q.format(j=j, s=P), P, "", "직업별 걱정 해소")

    # 8) 상황×질문
    for c, also_p in CASES:
        for q in CASE_Q + CASE_Q_R_ONLY:
            if "면책되나요" in q:
                continue          # 회생은 '면책'보다 '인가'가 먼저 — 아래 파산에서만
            add("상황질문", q.format(c=c, s=R), R, "", "상황별 가능 여부")
        if also_p:
            for q in CASE_Q:
                add("상황질문", q.format(c=c, s=P), P, "", "상황별 가능 여부")

    # 9) 생활 사건
    for cat, tpl, schemes in LIFE:
        for s in schemes:
            add(cat, tpl.format(s=s), s, "", "생활 속 궁금증")

    # 10) 비교·전환 — 신용회복·워크아웃 검색자를 데려오는 자리
    for tpl in COMPARE:
        add("제도비교", tpl.format(s=R), R, "", "제도 선택")

    # ── 거르기 ─────────────────────────────────────────────────
    taken = set()
    mass = ROOT / "seed" / "keyword.csv"
    if mass.exists():
        with open(mass, encoding="utf-8") as f:
            taken = {r["keyword"].replace(" ", "") for r in csv.DictReader(f)}

    out, seen, dropped = [], set(), collections.Counter()
    for row in rows:
        kw = row[1]
        key = kw.replace(" ", "")
        if key in seen:
            dropped["중복"] += 1
            continue
        if key in taken:
            dropped["양산 페이지와 같음"] += 1
            continue
        if any(b in kw for b in BANNED_IN_KW):
            dropped["광고규정"] += 1
            continue
        seen.add(key)
        out.append(row)
    return out, dropped


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--sample", type=int, default=3, help="분류별 예시 개수")
    args = ap.parse_args()

    from app import create_app
    from app.config import REGION

    app = create_app()
    with app.app_context():
        rows, dropped = build()

    print("지역 %s · 총 %d개 · 하루 2편 기준 %d일치 (약 %.1f개월)"
          % (REGION["name"], len(rows), len(rows) // 2, len(rows) / 2 / 30))
    if dropped:
        print("  제외:", dict(dropped))
    sch = collections.Counter(r[2] for r in rows)
    print("  제도: %s" % ", ".join("%s %d" % kv for kv in sch.most_common()))
    print()
    by = collections.OrderedDict()
    for r in rows:
        by.setdefault(r[0], []).append(r[1])
    for cat, kws in by.items():
        print("  %-8s %4d   %s" % (cat, len(kws), " | ".join(kws[:args.sample])))

    if args.write:
        OUT.parent.mkdir(exist_ok=True)
        with open(OUT, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["category", "keyword", "scheme", "area", "intent"])
            w.writerows(rows)
        print("\n저장: %s (%d행)" % (OUT, len(rows)))


if __name__ == "__main__":
    main()
