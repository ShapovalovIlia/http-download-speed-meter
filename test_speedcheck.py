import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from speedcheck import Result, measure_download


class SpeedCheckTest(unittest.TestCase):
    def test_ten_sequential_complete_downloads(self):
        payload = b"synthetic payload " * 65536
        stats = {"count": 0, "active": 0, "peak": 0}
        lock = threading.Lock()

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                with lock:
                    stats["count"] += 1
                    stats["active"] += 1
                    stats["peak"] = max(stats["peak"], stats["active"])
                try:
                    time.sleep(0.002)
                    self.send_response(200)
                    self.send_header("Content-Length", str(len(payload)))
                    self.end_headers()
                    self.wfile.write(payload)
                finally:
                    with lock:
                        stats["active"] -= 1
            def log_message(self, *args):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            result = measure_download(f"http://127.0.0.1:{server.server_port}/file")
            self.assertEqual(result.request_count, 10)
            self.assertEqual(stats["count"], 10)
            self.assertEqual(stats["peak"], 1)
            self.assertEqual(result.total_bytes, len(payload) * 10)
            self.assertGreater(result.total_seconds, 0)
            self.assertAlmostEqual(result.average_seconds, result.total_seconds / 10)
        finally:
            server.shutdown()
            server.server_close()
            worker.join()

    def test_units_and_invalid_inputs(self):
        result = Result(10_000_000, 2.0, 10)
        self.assertEqual(result.megabytes_per_second, 5.0)
        for url, timeout in [("file:///tmp/file", 1), ("https://", 1),
                             ("https://example.com/file", 0)]:
            with self.subTest(url=url, timeout=timeout):
                with self.assertRaises(ValueError):
                    measure_download(url, timeout)


if __name__ == "__main__":
    unittest.main()
