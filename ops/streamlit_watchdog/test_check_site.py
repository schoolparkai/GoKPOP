"""Local browser fixtures, not evidence of waking the real Streamlit app."""
import contextlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import tempfile
import threading
import unittest

from playwright.sync_api import sync_playwright

from check_site import Config, SITE_URL, WAKE_BUTTON, monitor, safe_text

HEALTHY = '''<!doctype html><meta charset="utf-8"><h1>GOKPOP 2.0</h1>
<div>69.44 / 100점</div>
<label><input type="radio" name="menu" checked>점수 보기</label>
<label><input type="radio" name="menu">직접 계산</label>
<label><input type="radio" name="menu">감상 노트</label>'''
SLEEP = '<h1>Zzzz. This app has gone to sleep due to inactivity.</h1>'


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path.split('?')[0]
        status = 200
        if path == '/healthy':
            body = HEALTHY
        elif path == '/iframe':
            body = '<iframe title="streamlitApp" src="/healthy"></iframe>'
        elif path == '/zero-height':
            body = '<style>body{height:0}main{position:fixed;inset:0}</style><main>' + HEALTHY + '</main>'
        elif path == '/sleep':
            body = SLEEP + f'''<button onclick="location.href='/warming'">{WAKE_BUTTON}</button>'''
        elif path == '/sleep-iframe':
            body = '<iframe title="streamlitApp" src="/sleep"></iframe>'
        elif path == '/warming':
            body = '<p>Starting app...</p><script>setTimeout(()=>location.href="/healthy",100)</script>'
        elif path == '/sleep-stuck':
            body = SLEEP + f'<button onclick="this.dataset.clicked=1">{WAKE_BUTTON}</button>'
        elif path == '/sleep-error':
            body = SLEEP + f'''<button onclick="location.href='/app-error'">{WAKE_BUTTON}</button>'''
        elif path == '/sleep-no-button':
            body = SLEEP
        elif path == '/wrong-score':
            body = HEALTHY.replace('69.44', '68.00')
        elif path == '/button-only':
            body = f'<p>Unrelated page</p><button>{WAKE_BUTTON}</button>'
        elif path == '/app-error':
            body = HEALTHY + '<div data-testid="stException">RuntimeError: test fixture</div>'
        elif path == '/unavailable':
            body, status = '<h1>Service unavailable</h1>', 503
        else:
            body = '<p>Loading...</p>'
        encoded = ('<!doctype html><meta charset="utf-8">' + body).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, *args):
        pass


class BrowserCases(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f'http://127.0.0.1:{cls.server.server_port}'
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch(headless=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def check(self, path):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'new-run'
            context = self.browser.new_context()
            page = context.new_page()
            config = Config(url=self.base + path, initial_timeout=.4, wake_timeout=.7,
                            poll=.05, navigation_timeout=2, network_retry_delay=.01)
            with contextlib.redirect_stdout(None):
                result = monitor(page, config, out)
            events = json.loads((out / 'events.json').read_text(encoding='utf-8'))
            self.assertEqual(result, json.loads((out / 'result.json').read_text(encoding='utf-8')))
            self.assertTrue((out / 'final.png').exists())
            context.close()
            return result, events

    def test_healthy(self):
        r, _ = self.check('/healthy')
        self.assertEqual(r['status'], 'healthy')
        self.assertFalse(r['wake_clicked'])
        self.assertFalse(r['wake_confirmed'])

    def test_cloud_iframe(self):
        r, _ = self.check('/iframe')
        self.assertEqual(r['status'], 'healthy')

    def test_fixed_streamlit_content_with_zero_height_body(self):
        r, _ = self.check('/zero-height')
        self.assertEqual(r['status'], 'healthy')

    def test_sleep_warm_then_healthy(self):
        r, e = self.check('/sleep')
        self.assertEqual(r['status'], 'healthy')
        self.assertTrue(r['wake_confirmed'])
        self.assertEqual(sum(x['event'] == 'wake_button_clicked' for x in e), 1)

    def test_sleep_inside_frame(self):
        r, _ = self.check('/sleep-iframe')
        self.assertEqual(r['status'], 'healthy')
        self.assertTrue(r['wake_confirmed'])

    def test_sleep_button_click_does_not_imply_success(self):
        r, e = self.check('/sleep-stuck')
        self.assertEqual(r['error_code'], 'wake_timeout')
        self.assertFalse(r['wake_confirmed'])
        self.assertEqual(sum(x['event'] == 'wake_button_clicked' for x in e), 1)

    def test_error_after_wake(self):
        r, _ = self.check('/sleep-error')
        self.assertEqual(r['error_code'], 'application_error')
        self.assertTrue(r['wake_clicked'])
        self.assertFalse(r['wake_confirmed'])

    def test_sleep_without_button(self):
        r, _ = self.check('/sleep-no-button')
        self.assertEqual(r['error_code'], 'sleep_button_missing')
        self.assertFalse(r['wake_clicked'])

    def test_button_without_sleep_text_not_clicked(self):
        r, _ = self.check('/button-only')
        self.assertEqual(r['error_code'], 'loading_timeout')
        self.assertFalse(r['wake_clicked'])

    def test_wrong_score_is_not_healthy(self):
        r, _ = self.check('/wrong-score')
        self.assertEqual(r['error_code'], 'loading_timeout')
        self.assertFalse(r['wake_confirmed'])

    def test_app_exception_even_with_score_is_failure(self):
        r, _ = self.check('/app-error')
        self.assertEqual(r['error_code'], 'application_error')
        self.assertFalse(r['wake_clicked'])

    def test_http_503_not_retried_or_awakened(self):
        r, _ = self.check('/unavailable')
        self.assertEqual(r['error_code'], 'http_error')
        self.assertEqual(r['navigation_attempts'], 1)
        self.assertFalse(r['wake_clicked'])

    def test_network_error_at_most_two_navigations(self):
        # A closed local port exercises real Chromium transport errors.
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        port = server.server_port
        server.server_close()
        with tempfile.TemporaryDirectory() as tmp:
            page = self.browser.new_page()
            with contextlib.redirect_stdout(None):
                r = monitor(page, Config(url=f'http://127.0.0.1:{port}/', initial_timeout=.1,
                                         network_retry_delay=.01, navigation_timeout=.2), Path(tmp) / 'run')
            page.close()
            self.assertEqual(r['error_code'], 'network_error')
            self.assertEqual(r['navigation_attempts'], 2)
            self.assertFalse(r['wake_clicked'])


class SafetyCases(unittest.TestCase):
    def test_only_fixed_production_or_loopback_url(self):
        self.assertTrue(Config().production)
        for url in ('https://example.com/', SITE_URL + '?token=value', 'http://example.com/',
                    'http://user:pass@localhost:1234/'):
            with self.assertRaises(ValueError):
                Config(url=url)

    def test_redact_diagnostic_url_and_email(self):
        text = safe_text('See https://example.com/?token=abc api_key=abcdef test@example.com')
        self.assertNotIn('abcdef', text)
        self.assertNotIn('test@example.com', text)
        self.assertNotIn('?token=', text)


if __name__ == '__main__':
    unittest.main()
