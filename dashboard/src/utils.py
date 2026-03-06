from datetime import datetime, timezone

def now_utc():
    return datetime.now(timezone.utc)

def fmt_bytes(n):
    if n is None:
        return "-"
    n = float(n)
    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    for u in units:
        if n < 1024 or u == units[-1]:
            if u in ("GB", "TB"):
                return f"{n:.0f} {u}"
            return f"{n:.2f} {u}"
        n /= 1024.0

def pct(used, total):
    if not total:
        return 0.0
    return float(used) / float(total) * 100.0

def bar_color(p):
    if p < 70:
        return "green"
    if p < 85:
        return "orange"
    return "red"