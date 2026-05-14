import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "seo_supercheck.py"


def run_checker(*args):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *map(str, args)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


class SeoSupercheckTests(unittest.TestCase):
    def test_good_fixture_has_no_critical_findings(self):
        result = run_checker(ROOT / "tests" / "fixtures" / "good", "--json")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        findings = [finding for page in json.loads(result.stdout) for finding in page["findings"]]
        self.assertFalse([finding for finding in findings if finding["level"] == "critical"])

    def test_bad_fixture_reports_critical_findings(self):
        result = run_checker(ROOT / "tests" / "fixtures" / "bad", "--json")
        self.assertEqual(result.returncode, 1)
        findings = [finding for page in json.loads(result.stdout) for finding in page["findings"]]
        messages = "\n".join(finding["message"] for finding in findings)
        self.assertIn("Missing html lang attribute", messages)
        self.assertIn("Missing meta description", messages)
        self.assertIn("Missing H1", messages)
        self.assertIn("image(s) missing alt", messages)
        self.assertIn("disallows the entire site", messages)

    def test_sitewide_fixture_reports_cross_page_and_policy_issues(self):
        result = run_checker(ROOT / "tests" / "fixtures" / "sitewide", "--base-url", "https://example.com", "--json")
        self.assertEqual(result.returncode, 1)
        pages = json.loads(result.stdout)
        findings = [finding for page in pages for finding in page["findings"]]
        messages = "\n".join(finding["message"] for finding in findings)
        self.assertIn("Duplicate title", messages)
        self.assertIn("Duplicate meta description", messages)
        self.assertIn("Duplicate canonical URL", messages)
        self.assertIn("Page is in sitemap but has robots noindex", messages)
        self.assertIn("Invalid JSON-LD script", messages)
        self.assertIn("Heading hierarchy jumps", messages)
        self.assertIn("local link(s) point to missing files", messages)
        self.assertIn("robots.txt contains a noindex directive", messages)
        self.assertIn("duplicate sitemap URL", messages)


if __name__ == "__main__":
    unittest.main()
