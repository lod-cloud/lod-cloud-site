import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import domains  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


class DomainsTest(unittest.TestCase):
    def test_the_jekyll_plugin_has_the_same_domains(self):
        ruby = (ROOT / "site" / "_plugins" / "lodcloud.rb").read_text(encoding="utf-8")
        block = ruby[ruby.index("DOMAINS = {"):ruby.index("}.freeze")]
        found = dict(re.findall(r'"(\w+)" => \["([^"]+)"', block))
        self.assertEqual(found, domains.DOMAINS)

    def test_the_schema_has_the_same_keys(self):
        import json
        schema = json.loads((ROOT / "schema" / "dataset.schema.json").read_text(encoding="utf-8"))
        self.assertEqual(schema["properties"]["domain"]["enum"], list(domains.DOMAINS))
