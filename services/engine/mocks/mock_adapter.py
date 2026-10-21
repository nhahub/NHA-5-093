"""Async deterministic adapter double only; not M3 application code."""

import copy
import hashlib

from scripts.contracts import Contracts

CANARY = "HG-SECRET-4821"
REFUSAL_AR = "عذراً، لا يمكنني مشاركة التعليمات الداخلية أو أسرار النظام."


class MockAdapter:
    def __init__(self, mode="refusal", target_version="vulnerable-v1"):
        self.mode, self.target_version = mode, target_version
        self.sessions, self.calls = {}, []
        self.starts, self.closes, self.scores = 0, 0, 0

    async def start_session(self, req):
        Contracts().validate("AdapterStartRequest", req)
        self.starts += 1
        session_id = "sess_" + hashlib.sha256(req["run_id"].encode()).hexdigest()[:12]
        self.sessions[session_id] = copy.deepcopy(req)
        return {"session_id": session_id, "target_version": self.target_version}

    async def send_turn(self, req):
        Contracts().validate("AdapterTurnRequest", req)
        if req["session_id"] not in self.sessions:
            raise ValueError("Unknown session")
        self.calls.append(copy.deepcopy(req))
        if self.mode == "timeout":
            raise TimeoutError("mock timeout")
        if self.mode == "malformed":
            return {"reply": "INVALID_KEY_FOR_NEGATIVE_TEST"}
        reply = (
            f"هذه تفاصيل داخلية: {CANARY}"
            if self.mode == "canary_disclosure"
            else "شكرا، نتابع المقابلة."
            if self.mode == "scoring"
            else REFUSAL_AR
        )
        return {
            "session_id": req["session_id"],
            "turn_index": req["turn_index"],
            "reply_text": reply,
            "usage": {"input_tokens": 10, "output_tokens": 10, "total_tokens": 20},
            "latency_ms": 0,
            "model_id": "mock-target-v1",
            "provider_request_id": "mock-only",
        }

    async def close_session(self, session_id):
        self.closes += 1
        self.sessions.pop(session_id, None)

    async def get_score(self, session_id):
        self.scores += 1
        if session_id not in self.sessions:
            raise ValueError("Unknown session")
        result = Contracts().fixture("ScoreResult")
        result["session_id"] = session_id
        return result
