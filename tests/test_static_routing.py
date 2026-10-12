import sys
import threading
import unittest
from functools import partial
from html.parser import HTMLParser
from http.server import HTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urljoin, urlparse
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from server import SGRRequestHandler


class AssetParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = set()

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        url = attrs.get("href") if tag == "link" else attrs.get("src")
        if tag in ("link", "script", "img") and url and not urlparse(url).scheme:
            self.urls.add(url)


class StaticRoutingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = HTTPServer(
            ("127.0.0.1", 0), partial(SGRRequestHandler, directory=str(ROOT))
        )
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def test_entry_urls_load_local_assets_from_the_final_document_url(self):
        for path in ("/", "/index.html", "/evaluacion2/index.html"):
            with self.subTest(path=path):
                with urlopen(self.base_url + path, timeout=5) as response:
                    document_url = response.url
                    parser = AssetParser()
                    parser.feed(response.read().decode("utf-8"))
                self.assertIn("css/sgr_eval2.css", parser.urls)
                self.assertIn("../assets/municipal/logo-la-serena.svg", parser.urls)
                for asset in sorted(parser.urls):
                    try:
                        with urlopen(urljoin(document_url, asset), timeout=5) as response:
                            self.assertEqual(response.status, 200, asset)
                            self.assertTrue(response.read(), asset)
                            if asset.endswith(".css"):
                                self.assertEqual(response.headers.get_content_type(), "text/css")
                    except HTTPError as error:
                        error.close()
                        self.fail(f"{path}: {asset} returned HTTP {error.code}")


if __name__ == "__main__":
    unittest.main()
