# -*- coding: utf-8 -*-
"""알리고(Aligo) 문자 발송.

    https://apis.aligo.in/send/     문자 발송
    https://apis.aligo.in/remain/   잔여 건수 조회

## 설계 원칙 두 가지

1. **상담 접수를 절대 실패시키지 않는다.** 문자는 부가 기능이고 접수가 본체다.
   모든 예외를 잡아 로그만 남기고, 접수 자체는 이미 커밋된 뒤에 보낸다.
2. **응답을 지연시키지 않는다.** 외부 API 호출이 몇 초 걸릴 수 있으므로
   별도 스레드에서 보낸다. 사용자는 바로 완료 모달을 본다.

## 설정 (.env)
    ALIGO_USER_ID     알리고 사이트 아이디
    ALIGO_API_KEY     API 키
    ALIGO_SENDER      발신번호 (알리고에 사전 등록된 번호여야 한다)
    ALIGO_TEST_MODE   Y로 두면 실제 발송 없이 응답만 받는다(과금 없음)
    ALIGO_ADMIN_PHONE 설정하면 새 접수 때 사무소에도 알림을 보낸다

**발신 서버 IP를 알리고에 등록해야 실제 발송이 된다.** 등록 전에는
인증 오류가 나며, 그 경우에도 접수는 정상 처리되고 로그에만 남는다.

## 문자 종류
SMS는 90바이트(CP949 기준, 한글 2바이트)까지다. 넘으면 LMS로 보내야 하며
제목이 필요하다. `_msg_type()`이 길이를 보고 자동으로 정한다.
"""
import logging
import os
import re
import threading

import requests

log = logging.getLogger(__name__)

SEND_URL = "https://apis.aligo.in/send/"
REMAIN_URL = "https://apis.aligo.in/remain/"
SMS_BYTE_LIMIT = 90
TIMEOUT = 10


def _conf():
    return {
        "user_id": os.environ.get("ALIGO_USER_ID", "").strip(),
        "api_key": os.environ.get("ALIGO_API_KEY", "").strip(),
        "sender": re.sub(r"\D", "", os.environ.get("ALIGO_SENDER", "")),
        "test": (os.environ.get("ALIGO_TEST_MODE", "") or "").strip().upper(),
        "admin": re.sub(r"\D", "", os.environ.get("ALIGO_ADMIN_PHONE", "")),
    }


def is_configured():
    c = _conf()
    return bool(c["user_id"] and c["api_key"] and c["sender"])


def _byte_len(text):
    """CP949 기준 바이트 수. 알리고가 이 기준으로 SMS/LMS를 가른다."""
    try:
        return len(text.encode("cp949"))
    except UnicodeEncodeError:
        # CP949로 못 쓰는 글자(이모지 등)가 있으면 넉넉히 잡아 LMS로 보낸다
        return SMS_BYTE_LIMIT + 1


def _msg_type(text):
    return "SMS" if _byte_len(text) <= SMS_BYTE_LIMIT else "LMS"


def _clean_phone(phone):
    return re.sub(r"\D", "", phone or "")


def send(receiver, msg, title=None):
    """문자 한 건 발송. 성공 여부와 무관하게 예외를 올리지 않는다.

    반환: {"ok": bool, "reason": str, ...} — 호출 측은 로그 용도로만 쓰면 된다.
    """
    c = _conf()
    if not is_configured():
        log.warning("문자 설정이 없어 발송을 건너뜁니다(ALIGO_* 환경변수 확인)")
        return {"ok": False, "reason": "not_configured"}

    to = _clean_phone(receiver)
    if not to:
        return {"ok": False, "reason": "invalid_receiver"}

    data = {
        "key": c["api_key"],
        "userid": c["user_id"],
        "sender": c["sender"],
        "receiver": to,
        "msg": msg,
        "msg_type": _msg_type(msg),
    }
    if data["msg_type"] == "LMS":
        data["title"] = (title or msg.strip().splitlines()[0])[:40]
    if c["test"] in ("Y", "N"):
        data["testmode_yn"] = c["test"]

    try:
        r = requests.post(SEND_URL, data=data, timeout=TIMEOUT)
        out = r.json()
    except Exception as exc:                      # 네트워크·JSON 등 전부
        log.exception("문자 발송 실패(요청 단계): %s", exc)
        return {"ok": False, "reason": "request_failed", "error": str(exc)}

    # 알리고는 성공 시 result_code가 1 이상(문자열로 올 때가 있어 int 변환)
    try:
        code = int(out.get("result_code", -1))
    except (TypeError, ValueError):
        code = -1
    ok = code > 0
    if ok:
        log.info("문자 발송 성공 to=%s type=%s msg_id=%s",
                 to[-4:].rjust(len(to), "*"), data["msg_type"], out.get("msg_id"))
    else:
        # IP 미등록·잔액 부족 등은 여기로 온다. 접수는 이미 저장된 상태다.
        log.error("문자 발송 거절 code=%s message=%s", out.get("result_code"),
                  out.get("message"))
    return {"ok": ok, "reason": "sent" if ok else "rejected", "response": out}


def send_async(receiver, msg, title=None):
    """응답을 막지 않도록 백그라운드로 보낸다. 실패해도 조용히 로그만 남는다."""
    if not is_configured():
        log.warning("문자 설정이 없어 발송을 건너뜁니다")
        return
    t = threading.Thread(
        target=send, args=(receiver, msg), kwargs={"title": title}, daemon=True
    )
    t.start()


def remain():
    """잔여 발송 건수 조회. 운영 점검용(flask sms-remain)."""
    c = _conf()
    if not is_configured():
        return {"ok": False, "reason": "not_configured"}
    try:
        r = requests.post(
            REMAIN_URL,
            data={"key": c["api_key"], "userid": c["user_id"]},
            timeout=TIMEOUT,
        )
        return {"ok": True, "response": r.json()}
    except Exception as exc:
        return {"ok": False, "reason": "request_failed", "error": str(exc)}


# ── 문안 ────────────────────────────────────────────────────────────
# 거래관계에 따른 안내 문자다. **광고 문구를 넣지 말 것** —
# 광고성 정보가 되면 (광고) 표기와 수신거부 안내 의무가 생긴다(정보통신망법).

def applicant_message(name, firm, phone):
    """신청자에게 보내는 접수 확인.

    **90바이트(SMS) 안에 들어가도록 맞춰 둔 문안이다.** 3글자 이름 기준 87바이트.
    한 줄만 더 붙여도 LMS로 넘어가 요금이 3배가 된다. 문구를 고칠 때는
    `flask sms-check`로 바이트 수를 확인할 것(이름이 길면 자동으로 LMS로 나간다).
    """
    return (
        "[{firm}] {name}님, 상담 신청이 접수되었습니다.\n"
        "30분 내 연락드립니다. {phone}"
    ).format(firm=firm, name=name, phone=phone)


def admin_message(name, phone, debt, area):
    """사무소에 보내는 새 접수 알림."""
    parts = ["[상담 접수] %s %s" % (name, phone)]
    if debt:
        parts.append("채무 %s" % debt)
    if area:
        parts.append("지역 %s" % area)
    return " / ".join(parts)
