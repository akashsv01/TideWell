"""Send a Health Auto Export-style payload to the TideWell webhook, without a phone."""
import argparse, json, re, sys, urllib.error, urllib.request
from datetime import date
from pathlib import Path

SAMPLE = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "health_auto_export_sample.json"
_DATE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")

def shifted_to_today(text):
    days = [date.fromisoformat(d) for d in _DATE.findall(text)]
    if not days:
        return text
    delta = date.today() - max(days)
    return _DATE.sub(lambda m: (date.fromisoformat(m.group(1)) + delta).isoformat(), text)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--token", required=True)
    ap.add_argument("--url", default="http://localhost:8000")
    ap.add_argument("--file", type=Path, default=None)
    args = ap.parse_args()
    body = args.file.read_text(encoding="utf-8") if args.file else shifted_to_today(SAMPLE.read_text())
    json.loads(body)
    req = urllib.request.Request(
        args.url.rstrip("/") + "/wearables/apple-health", data=body.encode(), method="POST",
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {args.token}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            print(json.dumps(json.load(resp), indent=2))
    except urllib.error.HTTPError as e:
        sys.exit(f"HTTP {e.code}: {e.read().decode(errors='replace')}")

if __name__ == "__main__":
    main()
