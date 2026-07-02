"""Quản lý gọi Gemini API trong giới hạn Free Tier.

Gemini 2.5 Flash Free Tier (ước tính an toàn):
  - RPM:  10 requests / phút  (Google giới hạn ~15 RPM)
  - RPD:  1000 requests / ngày (Google giới hạn ~1500 RPD)
  - TPM:  không giới hạn cứng ở free tier

Tích hợp với governance audit và retry exponential backoff.
Dùng file JSON để lưu trạng thái daily usage giữa các lần khởi động lại server.
"""

from __future__ import annotations

import asyncio
import json
import time
import warnings
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path
from typing import Any, Callable

# ── Giới hạn Free Tier (an toàn) ──────────────────────────────────────────
FREE_TIER_LIMITS = {
    "rpm": 10,      # requests per minute (Google: ~15)
    "rpd": 1000,    # requests per day      (Google: ~1500)
    "max_retries": 5,
    "base_delay": 2.0,   # giây — exponential backoff
    "max_delay": 60.0,   # giây
}

# File lưu trạng thái daily usage
_STATE_DIR = Path(__file__).resolve().parent.parent / "logs"
_STATE_FILE = _STATE_DIR / "free_tier_usage.json"


# ── Data models ────────────────────────────────────────────────────────────
@dataclass
class TierUsage:
    """Trạng thái sử dụng free tier trong ngày."""
    date: str = field(default_factory=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    total_requests: int = 0
    total_tokens: int = 0
    requests_by_minute: dict[str, int] = field(default_factory=dict)
    # minute_key -> count (cho sliding window RPM)
    _recent_calls: list[float] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "date": self.date,
            "total_requests": self.total_requests,
            "total_tokens": self.total_tokens,
            "requests_by_minute": self.requests_by_minute,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "TierUsage":
        return cls(
            date=d.get("date", ""),
            total_requests=d.get("total_requests", 0),
            total_tokens=d.get("total_tokens", 0),
            requests_by_minute=d.get("requests_by_minute", {}),
        )


# ── Free Tier Manager ──────────────────────────────────────────────────────
class FreeTierManager:
    """Quản lý gọi API trong giới hạn free tier với retry backoff."""

    def __init__(
        self,
        limits: dict | None = None,
        state_file: Path | None = None,
    ):
        self.limits = limits or FREE_TIER_LIMITS
        self.state_file = state_file or _STATE_FILE
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self._lock = asyncio.Lock()
        self._sync_lock = False  # fallback cho sync calls
        self.usage = self._load_state()
        self._call_times: list[float] = []  # sliding window cho RPM

    # ── Persistence ────────────────────────────────────────────────────
    def _load_state(self) -> TierUsage:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if self.state_file.exists():
            try:
                data = json.loads(self.state_file.read_text(encoding="utf-8"))
                usage = TierUsage.from_dict(data)
                if usage.date == today:
                    return usage
            except (json.JSONDecodeError, KeyError):
                pass
        return TierUsage(date=today)

    def _save_state(self) -> None:
        self.state_file.write_text(
            json.dumps(self.usage.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    # ── Rate checks ────────────────────────────────────────────────────
    def _clean_old_calls(self) -> None:
        """Xóa các call cũ hơn 60 giây khỏi sliding window."""
        now = time.time()
        self._call_times = [t for t in self._call_times if now - t < 60]

    def check_rpm(self) -> tuple[bool, str]:
        """Kiểm tra RPM — có thể gọi tiếp không?"""
        self._clean_old_calls()
        rpm_limit = self.limits["rpm"]
        current_rpm = len(self._call_times)
        if current_rpm >= rpm_limit:
            return False, (
                f"Đã đạt giới hạn RPM ({current_rpm}/{rpm_limit}). "
                f"Vui lòng đợi {60 - (time.time() - self._call_times[0]):.0f}s."
            )
        return True, "ok"

    def check_rpd(self) -> tuple[bool, str]:
        """Kiểm tra RPD — còn quota ngày không?"""
        rpd_limit = self.limits["rpd"]
        if self.usage.total_requests >= rpd_limit:
            return False, (
                f"Đã đạt giới hạn RPD ({self.usage.total_requests}/{rpd_limit}). "
                f"Vui lòng thử lại vào ngày mai."
            )
        return True, "ok"

    def check_limits(self) -> tuple[bool, str]:
        """Kiểm tra tất cả giới hạn."""
        ok, msg = self.check_rpm()
        if not ok:
            return False, msg
        ok, msg = self.check_rpd()
        if not ok:
            return False, msg
        return True, "ok"

    # ── Record usage ───────────────────────────────────────────────────
    def record_call(self, tokens: int = 0) -> None:
        """Ghi nhận một lần gọi API thành công."""
        now = time.time()
        self._call_times.append(now)
        self.usage.total_requests += 1
        self.usage.total_tokens += tokens

        minute_key = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M")
        self.usage.requests_by_minute[minute_key] = (
            self.usage.requests_by_minute.get(minute_key, 0) + 1
        )
        self._save_state()

    # ── Status & warnings ──────────────────────────────────────────────
    def status(self) -> dict:
        """Trả về trạng thái sử dụng hiện tại."""
        self._clean_old_calls()
        rpd_pct = round(self.usage.total_requests / self.limits["rpd"] * 100, 1)
        return {
            "date": self.usage.date,
            "rpm_current": len(self._call_times),
            "rpm_limit": self.limits["rpm"],
            "rpd_current": self.usage.total_requests,
            "rpd_limit": self.limits["rpd"],
            "rpd_percent": rpd_pct,
            "total_tokens": self.usage.total_tokens,
            "warning": (
                f"⚠️ Đã dùng {rpd_pct}% quota ngày ({self.usage.total_requests}/{self.limits['rpd']})"
                if rpd_pct >= 80
                else None
            ),
        }

    def warn_if_near_limit(self) -> str | None:
        """Cảnh báo nếu gần giới hạn."""
        st = self.status()
        warnings_list = []
        if st["rpm_current"] >= st["rpm_limit"] * 0.8:
            warnings_list.append(
                f"RPM sắp hết: {st['rpm_current']}/{st['rpm_limit']}"
            )
        if st["rpd_percent"] >= 80:
            warnings_list.append(st["warning"])
        return "; ".join(warnings_list) if warnings_list else None

    # ── Retry with backoff ─────────────────────────────────────────────
    async def call_with_retry(
        self,
        fn: Callable,
        *args,
        tokens_estimate: int = 500,
        **kwargs,
    ) -> Any:
        """Gọi hàm LLM với retry exponential backoff khi gặp 429.

        Args:
            fn: Hàm async cần gọi (vd: model.generate_content_async)
            tokens_estimate: Số token ước tính cho lần gọi này
            *args, **kwargs: Truyền vào fn

        Returns:
            Kết quả từ fn

        Raises:
            RuntimeError: Khi vượt giới hạn hoặc hết retry
        """
        async with self._lock:
            ok, msg = self.check_limits()
            if not ok:
                raise RuntimeError(f"Free tier limit: {msg}")

        max_retries = self.limits["max_retries"]
        base_delay = self.limits["base_delay"]
        max_delay = self.limits["max_delay"]

        for attempt in range(max_retries + 1):
            try:
                result = await fn(*args, **kwargs)
                async with self._lock:
                    self.record_call(tokens=tokens_estimate)
                warn = self.warn_if_near_limit()
                if warn:
                    warnings.warn(warn)
                return result
            except Exception as e:
                error_str = str(e)
                is_429 = "429" in error_str or "RESOURCE_EXHAUSTED" in error_str
                if not is_429 or attempt >= max_retries:
                    raise

                delay = min(base_delay * (2 ** attempt), max_delay)
                print(
                    f"  ⏳ Free tier retry {attempt + 1}/{max_retries} "
                    f"sau {delay:.0f}s (429 RESOURCE_EXHAUSTED)..."
                )
                await asyncio.sleep(delay)

        raise RuntimeError("Hết retry — API vẫn trả về 429")


# ── Singleton ──────────────────────────────────────────────────────────────
_manager: FreeTierManager | None = None


def get_tier_manager() -> FreeTierManager:
    """Lấy singleton FreeTierManager."""
    global _manager
    if _manager is None:
        _manager = FreeTierManager()
    return _manager


# ── Utility: in trạng thái ─────────────────────────────────────────────────
def print_tier_status() -> None:
    """In trạng thái free tier ra console."""
    mgr = get_tier_manager()
    st = mgr.status()
    bar_len = 30
    filled = int(st["rpd_percent"] / 100 * bar_len)
    bar = "█" * filled + "░" * (bar_len - filled)
    print(f"  Free Tier [{bar}] {st['rpd_percent']}%")
    print(f"  RPM: {st['rpm_current']}/{st['rpm_limit']}  "
          f"RPD: {st['rpd_current']}/{st['rpd_limit']}  "
          f"Tokens: {st['total_tokens']}")
    if st["warning"]:
        print(f"  {st['warning']}")


def reset_daily_usage() -> None:
    """Reset bộ đếm daily usage (dùng khi test)."""
    global _manager
    _manager = FreeTierManager()
    _manager.usage = TierUsage()
    _manager._call_times = []
    _manager._save_state()
    print("✓ Đã reset free tier usage")


# ── CLI ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("Free Tier Manager — Gemini 2.5 Flash")
    print("=" * 60)
    print_tier_status()
    print()
    print(f"Limits: RPM={FREE_TIER_LIMITS['rpm']}, "
          f"RPD={FREE_TIER_LIMITS['rpd']}, "
          f"retries={FREE_TIER_LIMITS['max_retries']}")
    print(f"State file: {_STATE_FILE}")
