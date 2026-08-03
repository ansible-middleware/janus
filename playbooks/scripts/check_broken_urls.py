"""Scan a collection tree for http(s) URLs and verify they respond."""

from __future__ import annotations

import argparse
import re
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

URL_PATTERN = re.compile(
    r"https?://[^\s\)\]>'\"<]+|"
    r"(?<=\()[\'\"]?(https?://[^\'\"\s\)\]]+)[\'\"]?(?=\))"
)
SKIP_URL_PATTERN = re.compile(
    r"(localhost|127\.0\.0\.1|example\.(com|org)|testclient|\.local|\{\{|\}\}|mailto:)",
    re.IGNORECASE,
)
SCAN_SUFFIXES = {".md", ".rst", ".html"}
SCAN_FILENAMES = {"readme.md", "galaxy.yml", "changelog.md", "changelog.rst"}
SKIP_DIRS = {"molecule", "tests", ".git", "upstream", "downstream", ".ansible", "templates"}
USER_AGENT = "janus-url-check/1.0"
MAX_GET_BYTES = 1024
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 2
# Host responded but denied access or throttled the request; treat as reachable.
REACHABLE_NON_SUCCESS_STATUSES = frozenset({401, 403, 429})


def should_scan(path: Path) -> bool:
    name_lower = path.name.lower()
    suffix_lower = path.suffix.lower()
    if name_lower in SCAN_FILENAMES:
        return True
    if suffix_lower in SCAN_SUFFIXES:
        return True
    if "docs" in path.parts and suffix_lower in {".md", ".rst", ".html"}:
        return True
    return False


def iter_files(root: Path):
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if should_scan(path):
            yield path


def normalize_url(url: str) -> str:
    return url.rstrip(".,;:)\"'")


def extract_urls(text: str) -> set[str]:
    urls: set[str] = set()
    for match in URL_PATTERN.finditer(text):
        candidate = match.group(1) if match.lastindex else match.group(0)
        candidate = normalize_url(candidate)
        if candidate and not SKIP_URL_PATTERN.search(candidate):
            urls.add(candidate)
    return urls


def request_url(url: str, method: str, timeout: int) -> tuple[int | None, str | None]:
    request = urllib.request.Request(
        url,
        method=method,
        headers={"User-Agent": USER_AGENT},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            if method == "GET":
                response.read(MAX_GET_BYTES)
            return response.status, None
    except urllib.error.HTTPError as exc:
        # Redirects (3xx) and other sub-400 codes mean the host is reachable.
        if exc.code < 400 or exc.code in REACHABLE_NON_SUCCESS_STATUSES:
            return exc.code, None
        return exc.code, f"HTTP {exc.code}"
    except Exception as exc:  # noqa: BLE001 - report any connectivity failure
        return None, str(exc)


def check_url(url: str, timeout: int) -> tuple[str, str | None]:
    last_error: str | None = None
    for attempt in range(MAX_RETRIES):
        error = request_url(url, "HEAD", timeout)[1]
        if error is None:
            return url, None

        # Some servers reject HEAD while GET succeeds.
        error = request_url(url, "GET", timeout)[1]
        if error is None:
            return url, None

        last_error = error
        if attempt < MAX_RETRIES - 1:
            time.sleep(RETRY_DELAY_SECONDS)

    return url, last_error


def collect_urls(root: Path) -> dict[str, list[str]]:
    url_sources: dict[str, list[str]] = {}
    for path in iter_files(root):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        relative_path = str(path.relative_to(root))
        for url in extract_urls(text):
            url_sources.setdefault(url, []).append(relative_path)
    return url_sources


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, help="Collection root directory to scan")
    parser.add_argument("--timeout", type=int, default=15, help="HTTP timeout in seconds")
    parser.add_argument("--workers", type=int, default=8, help="Concurrent URL checks")
    args = parser.parse_args()

    if not args.root.is_dir():
        print(f"Collection root does not exist: {args.root}", file=sys.stderr)
        return 2

    url_sources = collect_urls(args.root)
    unique_urls = sorted(url_sources)
    if not unique_urls:
        print(f"No URLs found under {args.root}")
        return 0

    failures: list[tuple[str, str, str]] = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(check_url, url, args.timeout): url for url in unique_urls}
        for future in as_completed(futures):
            url, error = future.result()
            if error:
                sources = ", ".join(sorted(set(url_sources[url])))
                failures.append((url, error, sources))

    if failures:
        print("Broken URL check failed:", file=sys.stderr)
        for url, error, sources in sorted(failures):
            print(f"  {url}", file=sys.stderr)
            print(f"    error: {error}", file=sys.stderr)
            print(f"    found in: {sources}", file=sys.stderr)
        return 1

    print(f"Checked {len(unique_urls)} URL(s) under {args.root}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
