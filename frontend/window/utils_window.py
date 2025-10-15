from pathlib import Path

def safe_exists(p):
    """يتأكد من وجود الملف أو المسار بأمان بدون رفع استثناء."""
    try:
        return p and Path(p).exists()
    except Exception:
        return False
