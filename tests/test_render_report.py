import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RENDERER = ROOT / "render_report.py"


def listing(listing_id, section, source, cadastre_links=None):
    return {
        "id": listing_id,
        "section": section,
        "address": listing_id,
        "district": "Центр",
        "price": 1,
        "area": 1,
        "land": 1,
        "coords": None,
        "map": "https://maps.example/" + listing_id,
        "reason": "test",
        "sources": [source],
        "cadastreLinks": cadastre_links or [],
        "qualified_all_criteria": False,
    }


class RenderReportLinkTests(unittest.TestCase):
    def test_unverified_urls_are_links_but_removed_urls_are_text(self):
        rieltor_url = "https://rieltor.ua/ternopol/houses-sale/view/12247407/"
        olx_url = "https://www.olx.ua/d/uk/obyavlenie/test-IDOoUlA.html"
        removed_url = "https://www.olx.ua/d/uk/obyavlenie/test-IDGone.html"
        cadastre_url = "https://cadastre.example/123"
        catalog_url = "https://catalog.example/search"
        removed_catalog_url = "https://catalog.example/removed"
        data = {
            "checkedAt": "2026-10-05T12:00:00+03:00",
            "listings": [
                listing(
                    "rieltor",
                    "excluded",
                    {"url": rieltor_url, "label": "rieltor.ua", "verified": False, "removed": False},
                    [{"url": cadastre_url, "number": "123", "verified": False}],
                ),
                listing(
                    "olx",
                    "active",
                    {"url": olx_url, "label": "olx.ua", "verified": False, "removed": False},
                ),
                listing(
                    "removed",
                    "removed",
                    {"url": removed_url, "label": "olx.ua", "verified": False, "removed": True},
                ),
            ],
            "sources": [
                {
                    "name": "Catalog",
                    "url": catalog_url,
                    "verified": False,
                    "removed": False,
                    "coverage": "test",
                    "limitations": "test",
                },
                {
                    "name": "Removed catalog",
                    "url": removed_catalog_url,
                    "verified": False,
                    "removed": True,
                    "coverage": "test",
                    "limitations": "test",
                },
            ],
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            source = temp / "listings.json"
            output = temp / "report"
            source.write_text(json.dumps(data), encoding="utf-8")
            subprocess.run(
                [sys.executable, str(RENDERER), "--input", str(source), "--out", str(output)],
                check=True,
                capture_output=True,
                text=True,
            )

            active_html = (output / "index.html").read_text(encoding="utf-8")
            excluded_html = (output / "excluded.html").read_text(encoding="utf-8")
            removed_html = (output / "removed.html").read_text(encoding="utf-8")
            cadastre_html = (output / "cadastre.html").read_text(encoding="utf-8")
            sources_html = (output / "sources.html").read_text(encoding="utf-8")
            report_md = (output / "report.md").read_text(encoding="utf-8")

            self.assertIn(f'href="{rieltor_url}">rieltor.ua 12247407</a>', excluded_html)
            self.assertIn(f'href="{olx_url}">olx.ua IDOoUlA</a>', active_html)
            self.assertNotIn(f'href="{removed_url}"', removed_html)
            self.assertIn("olx.ua IDGone — сторінку видалено", removed_html)
            self.assertIn(f'href="{cadastre_url}">123</a> — не перевірено', cadastre_html)
            self.assertIn(f'href="{catalog_url}">Catalog</a> — не перевірено', sources_html)
            self.assertNotIn(f'href="{removed_catalog_url}"', sources_html)
            self.assertIn(f"[rieltor]({rieltor_url}) (не перевірена)", report_md)


if __name__ == "__main__":
    unittest.main()
