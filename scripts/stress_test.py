"""Dev-only stress harness for the Postgres money path and a Bucket-B courier route.

Task 8.7 / design Decision 14. NOT a production dependency and NOT part of the
pytest suite — a standalone load generator using the already-present ``httpx``.
It drives hundreds of concurrent requests to validate (not trust) the psycopg
pool + Starlette threadpool sizing under burst:

- bounded p99 latency (the event loop never stalls — a slow courier ``await`` on
  one request must not freeze the pure-DB requests),
- no pool-exhaustion crash (bursts queue on the pool wait timeout, then fail
  clean with a 5xx rather than hanging or crashing the worker),
- graceful queueing (throughput holds and errors stay near zero under load).

Scenarios:
- ``money``   — pure-DB path: alternating ``GET /v1/products`` and ``GET /v1/cart``
                (sync/threadpooled handlers → psycopg pool). Isolates DB/pool
                behaviour from courier latency.
- ``courier`` — Bucket-B path: ``POST /v1/delivery/calculate`` in approximate mode.
                Reads the cart from the pool, then holds the request open across a
                real courier HTTP ``await``. This is the handler shape that would
                stall the loop if DB work were on it, so it is the key proof route.
- ``mixed``   — both interleaved, so a slow courier ``await`` runs alongside fast
                DB requests; p99 of the DB requests staying low is the stall proof.

Usage (against the running Compose backend):

    .venv/bin/python scripts/stress_test.py --scenario mixed --concurrency 200 --requests 4000

Every knob has a default, so a bare ``python scripts/stress_test.py`` runs a
sensible mixed burst.
"""

from __future__ import annotations

import argparse
import asyncio
import time
from collections import Counter
from dataclasses import dataclass, field

import httpx

DEFAULT_BASE_URL = "http://127.0.0.1:8001"

# Approximate-mode body: reads the cart (DB) then quotes both couriers (await).
# items_total_cents stays under the €50 free-shipping short-circuit so the courier
# await actually runs — that is the whole point of this route as a load target.
_CALCULATE_BODY = {
    "method": "door",
    "city": "София",
    "items_total_cents": 2000,
    "couriers": ["speedy", "econt"],
}


@dataclass
class Result:
    """One request's outcome."""

    latency_ms: float
    status: int  # 0 == transport error (timeout / connect / read)
    error: str | None = None


@dataclass
class Stats:
    """Accumulated outcomes for one run."""

    results: list[Result] = field(default_factory=list)

    def add(self, r: Result) -> None:
        self.results.append(r)

    def summarize(self, wall_seconds: float) -> str:
        latencies = sorted(r.latency_ms for r in self.results)
        n = len(latencies)
        statuses = Counter(r.status for r in self.results)
        errors = Counter(r.error for r in self.results if r.error)

        def pct(p: float) -> float:
            if not latencies:
                return 0.0
            idx = min(n - 1, int(round((p / 100.0) * (n - 1))))
            return latencies[idx]

        # A 503/504 or transport error under load is the pool-exhaustion /
        # queue-overflow signal we explicitly want to surface.
        ok = sum(c for s, c in statuses.items() if 200 <= s < 400)
        pool_exhaustion = statuses.get(503, 0) + statuses.get(504, 0)
        transport_errors = statuses.get(0, 0)

        lines = [
            f"  requests:        {n}",
            f"  wall time:       {wall_seconds:.2f}s",
            f"  throughput:      {n / wall_seconds:.1f} req/s" if wall_seconds else "",
            f"  success (2xx/3xx): {ok}  ({100.0 * ok / n:.1f}%)" if n else "",
            f"  latency p50:     {pct(50):.1f} ms",
            f"  latency p95:     {pct(95):.1f} ms",
            f"  latency p99:     {pct(99):.1f} ms",
            f"  latency max:     {latencies[-1]:.1f} ms" if latencies else "",
            f"  status codes:    {dict(sorted(statuses.items()))}",
            f"  pool-exhaustion (503/504): {pool_exhaustion}",
            f"  transport errors:          {transport_errors}",
        ]
        if errors:
            lines.append(f"  error kinds:     {dict(errors)}")
        return "\n".join(line for line in lines if line)


async def _session_client(base_url: str, timeout: float) -> httpx.AsyncClient:
    """A client with its own session cookie, mirroring one anonymous shopper."""
    client = httpx.AsyncClient(base_url=base_url, timeout=timeout)
    # Prime the session cookie the way the browser does (middleware sets it).
    await client.get("/v1/cart")
    return client


async def _one_request(client: httpx.AsyncClient, scenario: str, i: int) -> Result:
    start = time.perf_counter()
    try:
        if scenario == "courier":
            resp = await client.post("/v1/delivery/calculate", json=_CALCULATE_BODY)
        elif scenario == "money":
            # Alternate the two pure-DB reads.
            resp = (
                await client.get("/v1/products", params={"limit": 20})
                if i % 2 == 0
                else await client.get("/v1/cart")
            )
        else:  # mixed: ~1 in 3 requests is the slow courier await
            if i % 3 == 0:
                resp = await client.post("/v1/delivery/calculate", json=_CALCULATE_BODY)
            elif i % 3 == 1:
                resp = await client.get("/v1/products", params={"limit": 20})
            else:
                resp = await client.get("/v1/cart")
    except httpx.HTTPError as exc:
        elapsed = (time.perf_counter() - start) * 1000.0
        return Result(latency_ms=elapsed, status=0, error=type(exc).__name__)
    elapsed = (time.perf_counter() - start) * 1000.0
    return Result(latency_ms=elapsed, status=resp.status_code)


async def _worker(
    client: httpx.AsyncClient,
    scenario: str,
    queue: asyncio.Queue[int],
    stats: Stats,
) -> None:
    while True:
        try:
            i = queue.get_nowait()
        except asyncio.QueueEmpty:
            return
        stats.add(await _one_request(client, scenario, i))
        queue.task_done()


async def run(base_url: str, scenario: str, concurrency: int, requests: int, timeout: float) -> int:
    stats = Stats()
    queue: asyncio.Queue[int] = asyncio.Queue()
    for i in range(requests):
        queue.put_nowait(i)

    # One client (=one session) per concurrent virtual user.
    clients = await asyncio.gather(
        *(_session_client(base_url, timeout) for _ in range(concurrency))
    )
    print(
        f"Stress: scenario={scenario} concurrency={concurrency} "
        f"requests={requests} target={base_url}"
    )
    start = time.perf_counter()
    try:
        await asyncio.gather(*(_worker(c, scenario, queue, stats) for c in clients))
    finally:
        await asyncio.gather(*(c.aclose() for c in clients))
    wall = time.perf_counter() - start

    print("\nResults:")
    print(stats.summarize(wall))

    # Non-zero exit if the run showed a hard failure signal, so CI/manual runs
    # can gate on it. A handful of clean 5xx under extreme burst is queueing, not
    # a crash; treat >1% failures as a fail.
    failures = sum(1 for r in stats.results if r.status == 0 or r.status >= 500)
    fail_rate = failures / len(stats.results) if stats.results else 1.0
    verdict = "PASS" if fail_rate <= 0.01 else "FAIL"
    print(f"\nVerdict: {verdict}  (failure rate {100.0 * fail_rate:.2f}%)")
    return 0 if verdict == "PASS" else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--scenario", choices=["money", "courier", "mixed"], default="mixed")
    parser.add_argument("--concurrency", type=int, default=200)
    parser.add_argument("--requests", type=int, default=4000)
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="Per-request client timeout (s). Kept high so pool-wait queueing "
        "shows as latency, not a client-side abort.",
    )
    args = parser.parse_args()
    return asyncio.run(
        run(
            base_url=args.base_url,
            scenario=args.scenario,
            concurrency=args.concurrency,
            requests=args.requests,
            timeout=args.timeout,
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
