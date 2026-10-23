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
parser.add_argument("--check-only", action="store_true", help="Validate references without copying assets")
args = parser.parse_args()

report = Path(args.report).resolve()
source_root = Path(args.source_root).resolve()
destination_root = Path(args.destination_root).resolve()
if not args.check_only:
    destination_root.mkdir(parents=True, exist_ok=True)

collector = LocalReferenceParser()
documents = sorted(source_root.glob("*.html"))
if report not in documents:
    documents.append(report)
for document in documents:
    collector.feed(document.read_text(encoding="utf-8-sig"))

# Evidence paths also live in the data (measurements, photo reviews, registry
# records), even when a page does not render a separate hyperlink to each file.
def data_references(value):
    if isinstance(value, dict):
        for item in value.values():
            data_references(item)
    elif isinstance(value, list):
        for item in value:
            data_references(item)
    elif isinstance(value, str) and value.startswith("sources/") and "\n" not in value and len(value) < 500:
        collector.references.add(value)


data_path = source_root / "listings.json"
if data_path.is_file():
    data_references(json.loads(data_path.read_text(encoding="utf-8-sig")))

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
    if source.suffix.lower() == ".html" and source.parent == source_root:
        continue
    if not args.check_only:
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not destination.is_file() or destination.stat().st_size != source.stat().st_size:
            shutil.copy2(source, destination)
    copied += 1

result = {
    "report": str(report),
    "referencesCopiedOrVerified": copied,
    "checkOnly": args.check_only,
    "missing": missing,
}
print(json.dumps(result, ensure_ascii=False))
if missing:
    raise SystemExit(2)
