#!/usr/bin/env python3
"""Check that the download, example and SPARQL URLs of the datasets still respond.

    scripts/check_links.py --state resources.json

Replaces GetData.java / lod-cloud-draw's get-data.py. Every distinct URL in
data/datasets is checked once and its result is kept in the state file (read
first, rewritten at the end), keyed by URL:

    status          "OK", "FAIL (<reason>)" or "SKIPPED (<reason>)" (not a web URL)
    http            the HTTP status code, when there was a response
    last_checked    date of the last check
    last_ok         date of the last OK (absent if never OK)
    failures        consecutive failed checks (0 when OK)

A URL that was not reached for lack of time keeps its previous record. Results
are informational: shared runner IPs are blocked by some servers, so one failure
means little; `failures` is what to act on.

The number of requests to other people's servers is kept down:
- each distinct URL is requested once (about 5,100 for 6,200 resources), with a
  HEAD request, or a GET for examples, whose body is never read; a second request
  is made only when a server refuses HEAD;
- a URL that was OK is not checked again for --recheck-ok-days (28), so a weekly
  run checks about a quarter of them plus everything that is failing;
- one request at a time per host, and after --max-host-errors connection errors in
  a row the host's other URLs are marked unreachable without being tried;
- after --host-budget seconds the rest of a host's URLs are left for the next run.
"""
import argparse
import json
import sys
import threading
import time
import urllib.parse
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
import urllib3

ROOT = Path(__file__).resolve().parent.parent
USER_AGENT = "lod-cloud-link-checker (+https://github.com/lod-cloud/lod-cloud-site)"
RDF_ACCEPT = "application/rdf+xml,text/turtle,application/n-triples,application/ld+json,*/*;q=0.9"

# resource list -> the field holding the URL, and how to check it
RESOURCES = {
    "full_download": ("download_url", "head"),
    "other_download": ("access_url", "head"),
    "example": ("access_url", "get"),
    "sparql": ("access_url", "head"),
}
# A server that refuses HEAD may still serve GET
HEAD_REFUSED = {400, 403, 404, 405, 406, 429, 500, 501, 503}
# An endpoint that answers a request without a query with 400 or 405 is alive
SPARQL_ALIVE = {400, 405}


def collect(data_dir):
    """{url: set of check kinds} for every resource in the dataset files."""
    urls = defaultdict(set)
    for path in sorted(Path(data_dir).glob("*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        for kind, (field, _) in RESOURCES.items():
            for resource in record.get(kind, []):
                url = (resource.get(field) or "").strip()
                if url:
                    urls[url].add(kind)
    return urls


def method_for(kinds):
    """GET if any resource at the URL is an example (it must serve RDF), else HEAD."""
    return "get" if any(RESOURCES[k][1] == "get" for k in kinds) else "head"


REQUESTS = 0  # HTTP requests made in this run
_count_lock = threading.Lock()


class InvalidURL(Exception):
    """The URL cannot be requested at all (bad host name, characters): a data problem, not a down host."""


class ConnectionProblem(Exception):
    """No HTTP response (DNS, refused, timeout, TLS): evidence that the host is down."""


def request(session, method, url, timeout, accept=None):
    global REQUESTS
    with _count_lock:
        REQUESTS += 1
    headers = {"Accept": accept} if accept else {}
    try:
        response = session.request(method.upper(), url, headers=headers, timeout=timeout,
                                   allow_redirects=True, stream=True)
        response.close()  # the body is never needed
        return response.status_code
    except (requests.exceptions.InvalidURL, requests.exceptions.InvalidSchema,
            requests.exceptions.MissingSchema, urllib3.exceptions.LocationParseError,
            UnicodeError, ValueError):
        raise InvalidURL()
    except requests.exceptions.Timeout:
        raise ConnectionProblem("timeout")
    except requests.exceptions.SSLError:
        raise ConnectionProblem("TLS error")
    except requests.exceptions.TooManyRedirects:
        raise ConnectionProblem("too many redirects")
    except requests.exceptions.ConnectionError as e:
        text = str(e)
        raise ConnectionProblem("DNS failure" if "Name or service not known" in text
                                or "getaddrinfo" in text or "NameResolutionError" in text
                                else "connection failed")
    except Exception as e:  # one odd URL must not stop the run
        raise ConnectionProblem(type(e).__name__)


def check_one(session, url, kinds, timeout):
    """(status string, http code or None) for one URL. Raises ConnectionProblem."""
    scheme = urllib.parse.urlsplit(url).scheme.lower()
    if scheme not in ("http", "https"):
        if scheme in ("ftp", "ftps", "ipfs", "ipns"):
            return "SKIPPED (%s is not checked)" % scheme, None
        return "FAIL (not a web URL)", None
    accept = RDF_ACCEPT if "example" in kinds else None
    method = method_for(kinds)
    code = request(session, method, url, timeout, accept)
    if method == "head" and code in HEAD_REFUSED:
        code = request(session, "get", url, timeout, accept)
    ok = 200 <= code < 300 or (code in SPARQL_ALIVE and "sparql" in kinds)
    return ("OK" if ok else "FAIL (%d)" % code), code


def check_host(host_urls, kinds_of, timeout, host_budget, max_errors, today):
    """Check one host's URLs one after another; returns {url: result or None (not checked)}."""
    results = {}
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT
    start = time.monotonic()
    errors_in_a_row = 0
    down = None
    for url in host_urls:
        if down:
            results[url] = {"status": "FAIL (host unreachable: %s)" % down, "http": None}
            continue
        if time.monotonic() - start > host_budget:
            results[url] = None
            continue
        try:
            status, code = check_one(session, url, kinds_of[url], timeout)
            errors_in_a_row = 0
        except InvalidURL:
            status, code = "FAIL (invalid URL)", None
        except ConnectionProblem as e:
            status, code = "FAIL (%s)" % e, None
            errors_in_a_row += 1
            if errors_in_a_row >= max_errors:
                down = str(e)
        results[url] = {"status": status, "http": code}
    session.close()
    return results


def merge(previous, results, today):
    """Update the state with new results. Not-checked URLs (None) keep their record."""
    state = {}
    for url, result in results.items():
        old = previous.get(url, {})
        if result is None:
            if old:
                state[url] = old
            continue
        record = {"status": result["status"], "last_checked": today}
        if result["http"] is not None:
            record["http"] = result["http"]
        if result["status"] == "OK":
            record["last_ok"] = today
            record["failures"] = 0
        elif result["status"].startswith("SKIPPED"):
            record["failures"] = 0
            if "last_ok" in old:
                record["last_ok"] = old["last_ok"]
        else:
            if "last_ok" in old:
                record["last_ok"] = old["last_ok"]
            record["failures"] = old.get("failures", 0) + 1
        state[url] = record
    return state


def due(urls, previous, today, recheck_ok_days):
    """The URLs to check now: all except those that were OK within recheck_ok_days."""
    cutoff = (datetime.fromisoformat(today) - timedelta(days=recheck_ok_days)).date().isoformat()
    def fresh(url):
        old = previous.get(url, {})
        return old.get("status") == "OK" and old.get("last_checked", "") > cutoff
    return {u: k for u, k in urls.items() if not fresh(u)}


def run(urls, previous, workers, timeout, host_budget, max_errors, today):
    """Check all URLs (a dict url -> kinds); returns the new state."""
    by_host = defaultdict(list)
    for url in sorted(urls):
        by_host[urllib.parse.urlsplit(url).netloc.lower()].append(url)
    results = {}
    lock = threading.Lock()

    def work(host):
        found = check_host(by_host[host], urls, timeout, host_budget, max_errors, today)
        with lock:
            results.update(found)

    # biggest hosts first, so they do not end up alone at the end
    order = sorted(by_host, key=lambda h: -len(by_host[h]))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        list(pool.map(work, order))
    return merge(previous, results, today)


def summary(state, urls, seconds, requests_made, due_count):
    counts = defaultdict(int)
    for url in urls:
        s = state.get(url, {}).get("status", "not checked")
        counts["OK" if s == "OK" else "SKIPPED" if s.startswith("SKIPPED") else
               "not checked" if s == "not checked" else "FAIL"] += 1
    newly = sum(1 for u in urls if state.get(u, {}).get("failures") == 1 and u in state)
    long_failing = sum(1 for u in urls if state.get(u, {}).get("failures", 0) >= 4)
    reasons = defaultdict(int)
    for u in urls:
        s = state.get(u, {}).get("status", "")
        if s.startswith("FAIL"):
            reasons[s] += 1
    lines = ["## Link check", "",
             "%d distinct URLs: %d were due and %d HTTP requests were made, in %d s." % (
                 len(urls), due_count, requests_made, seconds),
             "", "Now: **%d OK**, %d failing, %d skipped, %d not checked yet." % (
                 counts["OK"], counts["FAIL"], counts["SKIPPED"], counts["not checked"]),
             "", "- first failure this run: %d" % newly,
             "- failed in 4 or more checks in a row: %d" % long_failing, "",
             "| Most common failures | URLs |", "|---|---|"]
    for reason, n in sorted(reasons.items(), key=lambda kv: -kv[1])[:10]:
        lines.append("| %s | %d |" % (reason, n))
    return "\n".join(lines) + "\n"


def sample(urls, limit):
    """`limit` URLs spread evenly over the sorted list (deterministic)."""
    ordered = sorted(urls)
    if not limit or limit >= len(ordered):
        return {u: urls[u] for u in ordered}
    step = len(ordered) / limit
    return {ordered[int(i * step)]: urls[ordered[int(i * step)]] for i in range(limit)}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--state", type=Path, required=True, help="state file (read if it exists, then written)")
    ap.add_argument("--data", default=str(ROOT / "data" / "datasets"))
    ap.add_argument("--limit", type=int, help="check only this many URLs, spread over the list (for tests)")
    ap.add_argument("--recheck-ok-days", type=int, default=28,
                    help="do not check a URL again within this many days of an OK (0: check all)")
    ap.add_argument("--workers", type=int, default=64, help="hosts checked in parallel")
    ap.add_argument("--timeout", type=float, default=20, help="seconds per request")
    ap.add_argument("--host-budget", type=float, default=300, help="seconds per host before leaving its other URLs")
    ap.add_argument("--max-host-errors", type=int, default=3, help="connection errors in a row before a host is given up")
    ap.add_argument("--summary", type=Path, help="write a Markdown summary here (e.g. $GITHUB_STEP_SUMMARY)")
    args = ap.parse_args(argv)

    today = datetime.now(timezone.utc).date().isoformat()
    previous = json.loads(args.state.read_text(encoding="utf-8")) if args.state.exists() else {}
    urls = sample(collect(args.data), args.limit)
    to_check = due(urls, previous, today, args.recheck_ok_days)
    print("%d distinct URLs, %d due on %d hosts" % (
        len(urls), len(to_check), len({urllib.parse.urlsplit(u).netloc for u in to_check})), file=sys.stderr)

    start = time.monotonic()
    fresh_state = run(to_check, previous, args.workers, args.timeout, args.host_budget, args.max_host_errors, today)
    seconds = round(time.monotonic() - start)
    # URLs that were not due keep their record
    state = {u: previous[u] for u in urls if u in previous and u not in to_check}
    state.update(fresh_state)

    # URLs no longer in the data are dropped, except when only a sample was checked
    if args.limit:
        state = {**previous, **state}
    args.state.parent.mkdir(parents=True, exist_ok=True)
    args.state.write_text(json.dumps(state, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")

    text = summary(state, urls, seconds, REQUESTS, len(to_check))
    print(text, file=sys.stderr)
    if args.summary:
        with args.summary.open("a", encoding="utf-8") as f:
            f.write(text)


if __name__ == "__main__":
    main()
