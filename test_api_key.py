"""Kiểm tra API key mới + Free Tier Manager trước khi chạy full flow."""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from lab_utils.env_setup import load_lab_env, require_api_key
from lab_utils.free_llm_man import get_tier_manager, print_tier_status, reset_daily_usage

load_lab_env()
require_api_key()

print("=" * 60)
print("KIỂM TRA API KEY + FREE TIER")
print("=" * 60)

# Reset usage nếu là ngày mới hoặc lần đầu
tier = get_tier_manager()
print_tier_status()

print()
print("Kiểm tra kết nối Gemini API...")
try:
    import os
    import time
    from google import genai

    client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

    # Thử gọi model nhẹ nhất — có retry nếu 429
    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            response = client.models.generate_content(
                model="gemini-2.0-flash-lite",
                contents="Say 'OK' in one word.",
            )
            print(f"  ✓ API key hoạt động: {response.text.strip()}")
            tier.record_call(tokens=10)
            break
        except Exception as inner_e:
            err = str(inner_e)
            if "429" in err and attempt < max_attempts - 1:
                wait = 15
                print(f"  ⏳ Rate limited, đợi {wait}s... (attempt {attempt+1}/{max_attempts})")
                time.sleep(wait)
            else:
                raise

    print_tier_status()

except Exception as e:
    print(f"  ✗ Lỗi API: {e}")
    print("  Kiểm tra lại GOOGLE_API_KEY trong .env")

print()
print("=" * 60)
print("✓ Kiểm tra hoàn tất")
print("=" * 60)
