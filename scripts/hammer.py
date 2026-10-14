import sys
from collections import Counter
import httpx

BASE = "http://localhost:8000"

def main() -> None:
    path = sys.argv[1] if len(sys.argv) > 1 else "/prices?limit=1"
    count = int(sys.argv[2]) if len(sys.argv) > 2 else 65
    codes, last = Counter(), None
    with httpx.Client(base_url=BASE, timeout=30) as client:
        for _ in range(count):
            last = client.get(path)
            codes[last.status_code] += 1
    for code, n in sorted(codes.items()):
        print(f" HTTP {code}: {n} requests")
    keep = ("x-ratelimit", "retry-after", "x-cache")
    print("Last response headers:", {k: v for k, v in last.headers.items() if k.startswith(keep)})

if __name__ == "__main__":
    main()