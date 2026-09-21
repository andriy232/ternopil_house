import argparse
import json
import shutil
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit


class LocalReferenceParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.references = set()

    def handle_starttag(self, tag, attrs):
        for name, value in attrs:
            if name in {"src", "href"} and value:
                self.references.add(value)


def local_path(value):
    if value.startswith(("#", "data:", "mailto:", "javascript:")):
        return None
    parsed = urlsplit(value)
    if parsed.scheme or parsed.netloc:
        return None
    path = unquote(parsed.path).replace("/", "\\").lstrip("\\")
    return Path(path) if path else None


parser = argparse.ArgumentParser()
parser.add_argument("--report", required=True)
parser.add_argument("--source-root", required=True)
parser.add_argument("--destination-root", required=True)
args = parser.parse_args()

report = Path(args.report).resolve()
source_root = Path(args.source_root).resolve()
destination_root = Path(args.destination_root).resolve()
destination_root.mkdir(parents=True, exist_ok=True)

html = report.read_text(encoding="utf-8-sig")
collector = LocalReferenceParser()
collector.feed(html)

copied = 0
missing = []
for value in sorted(collector.references):
    relative = local_path(value)
    if relative is None:
        continue
    source = (source_root / relative).resolve()
    destination = (destination_root / relative).resolve()
    if not source.is_relative_to(source_root) or not destination.is_relative_to(destination_root):
        missing.append({"reference": value, "reason": "outside report directory"})
        continue
    if not source.is_file():
        missing.append({"reference": value, "reason": "source file missing"})
        continue
    if source == report:
        continue
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not destination.is_file() or destination.stat().st_size != source.stat().st_size:
        shutil.copy2(source, destination)
    copied += 1

result = {
    "report": str(report),
    "referencesCopiedOrVerified": copied,
    "missing": missing,
}
print(json.dumps(result, ensure_ascii=False))
if missing:
    raise SystemExit(2)
