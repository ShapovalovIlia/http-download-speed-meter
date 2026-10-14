"""Measure ten sequential HTTP downloads using the Python standard library."""
import argparse
from dataclasses import dataclass
import time
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from urllib.error import URLError

REQUEST_COUNT = 10
CHUNK_SIZE = 64 * 1024


@dataclass(frozen=True)
class Result:
    total_bytes: int
    total_seconds: float
    request_count: int

    @property
    def average_seconds(self):
        return self.total_seconds / self.request_count

    @property
    def megabytes_per_second(self):
        return self.total_bytes / self.total_seconds / 1_000_000


def measure_download(url: str, timeout: float = 30.0) -> Result:
    parsed = urlsplit(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ValueError("URL must use HTTP or HTTPS and include a hostname")
    if timeout <= 0:
        raise ValueError("Timeout must be positive")
    total_bytes, total_seconds = 0, 0.0
    for _ in range(REQUEST_COUNT):
        request = Request(url, headers={
            "User-Agent": "http-download-meter/1.0",
            "Cache-Control": "no-cache",
            "Accept-Encoding": "identity",
        })
        started = time.perf_counter()
        with urlopen(request, timeout=timeout) as response:
            while chunk := response.read(CHUNK_SIZE):
                total_bytes += len(chunk)
        total_seconds += time.perf_counter() - started
    if total_seconds <= 0:
        raise ValueError("Elapsed download time must be positive")
    return Result(total_bytes, total_seconds, REQUEST_COUNT)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url", help="URL of a sufficiently large HTTP(S) file")
    parser.add_argument("--timeout", type=float, default=30.0,
                        help="Socket operation timeout in seconds (default: 30)")
    args = parser.parse_args()
    try:
        result = measure_download(args.url, args.timeout)
    except (ValueError, URLError, OSError) as error:
        parser.exit(1, f"Measurement failed: {error}\n")
    print(f"Requests: {result.request_count}")
    print(f"Downloaded bytes: {result.total_bytes}")
    print(f"Total request time: {result.total_seconds:.6f} s")
    print(f"Average complete request: {result.average_seconds:.6f} s")
    print(f"Download rate: {result.megabytes_per_second:.3f} MB/s")
    print(f"Download rate: {result.megabytes_per_second * 8:.3f} Mbit/s")


if __name__ == "__main__":
    main()
