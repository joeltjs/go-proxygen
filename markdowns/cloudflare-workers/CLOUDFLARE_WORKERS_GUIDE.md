# Cloudflare Workers Guide

Notes on using Cloudflare Workers as a relay for AI traffic, and where that leaves proxygen.

## Decision (what this guide recommends)

Use the **Worker relay** as the setup of record. One deploy, one URL, nothing to regenerate, no proxy pool and no go-proxygen involved on the relay path.

One thing to drop from earlier planning: Cloudflare does **not** hand out proxy IPs, so there is no "proxy pool fed from Cloudflare" and no `proxies_cloudflare.txt` to generate. The relay is a single endpoint, not a pool. If you want the pool for quota multiplication, that is the separate go-proxygen path; this guide is the relay path.

## Two different tools

| | Proxy pool (go-proxygen) | Worker relay (Cloudflare) |
|---|---|---|
| Exit identities | Hundreds to thousands of rotating IPs | One stable identity (Cloudflare edge IP) |
| Effect on OpenCode quota | Multiplies per-IP quota | Daily quota still applies once |
| Maintenance | Lists rot fast; regenerate regularly | Deploy once, forget it |
| Speed | Depends on proxy quality | Fast, global CDN network |

Short version: pool for volume, relay for stability and hiding your home/VPS IP. The relay does not multiply quota because OpenCode keeps seeing one exit identity.

## Free tier limits and the safe line

| Resource | Official limit | Safe target |
|---|---|---|
| Requests | 100,000/day | <= 75,000/day (75%) |
| CPU time | ~10 ms/request | A pass-through relay sits far below this |
| Memory | 128 MB/isolate | Irrelevant for a relay |
| Egress bandwidth | Free | - |

### Recommended safe numbers (concrete)

- **Daily request ceiling to run:** **75,000 requests/day.** That is 75% of the 100K free cap. It leaves a 25% buffer so bursts and edge cases around account-level quotas never push you into paid billing or a throttle flag.
- **Set 60,000 as your comfort line.** If you want margin squared (double safety), run at 60% of the cap. Nothing on the OpenCode side needs to know about this; it just keeps the Cloudflare counter far from its own ceiling.
- **Fear baseline for billing:** treat anything above 80,000 as the red zone. If your monitoring ever shows that, dial back.

An explicit answer to "how many proxies is that": Cloudflare Workers does **not** hand you proxies — there is no "generate N proxy IPs" here. The relay forwards from whatever edge IP it happens to use. So the only sensible mapping is quota-equivalence (division below), not literal IP count.

## How far it actually stretches (the math)

OpenCode's free tier resets per IP at roughly 40-60 requests/day; plan with 50.

| Strategy | Daily ceiling | Single-IP-day equivalents* |
|---|---|---|
| Direct connection (no pool, no relay) | ~50 requests | 1 |
| Worker relay at the 100K cap, max burn | 100,000 requests | ~2,000 |
| **Worker relay at the recommended safe line** | **75,000 requests** | **~1,500** |
| Worker relay on the double-safe line | 60,000 requests | ~1,200 |

*Equivalents = daily requests divided by 50, i.e. how many one-IP days of demand this covers if every request landed on a fresh IP.

The catch you need to test before trusting those numbers: the equivalence assumes each request exits through an edge IP OpenCode has not already counted today. Cloudflare does not promise per-request IP rotation. If OpenCode ends up seeing one or two stable edge IPs from your colo, the relay collapses back to a single ~50-request day regardless of how high the CF counter climbs. Run a day-one experiment: fire a few hundred requests through the relay and count how many clear before the first 429.

## Recommended pool size (the number that matters daily)

If you are on the proxy-pool path (go-proxygen feeding 9Router) rather than the relay, the working number is **1500 proxies**, and it is the safe sweet spot. That is the number this repo already defaults you toward with `--count 1500`.

Why 1500 is the safe line:

- Cloudflare's free tier allows 100,000 requests/day; the safe ceiling is 75,000/day (75%).
- OpenCode free resets per IP at 40-60 requests/day; plan 50.
- **1500 proxies x 50 = 75,000 requests/day.** That is exactly the same safe free-tier number. When you import 1500 proxies, your potential pool output caps out at the same 75K that Cloudflare calls safe, so you never overshoot the free tier simply by having a 1500-entry pool.
- The two numbers converge deliberately: 1500 is the pool size that maps onto the 75K free-tier safe line without pushing past it. Importing more than 1500 does not buy extra room, because the daily ceiling is already reached — you would only add dying IPs to health-check and regenerate for nothing.
- On the pool path that 75K is genuinely reachable (each request exits from a different proxy IP); on the relay path the same 75K is a hard counter but collapses to ~50/day if OpenCode sees one stable edge IP.

So: **staying at 1500 keeps you safely under the free tier by design.** It is the ceiling, not a starting point to overshoot. With 1500 healthy proxies the practical envelope is roughly 40-60k requests/day, comfortably inside that line.

If you are also running the relay as a fallback identity, keep the two separate: 1500 for the pool path, the 60-75k request math for the relay path. They do not stack into a single larger quota; they are two independent identities.

## How the relay works

A worker is a fetch forwarder: it accepts a request at `yourname.workers.dev` and passes it unchanged to `api.opencode.ai`. OpenCode sees a Cloudflare datacenter IP, not yours.

Honest caveat: edge IPs are shared by millions of workers. Nobody outside Cloudflare can promise how OpenCode treats them (allowed, throttled harder, or blocked). Verify empirically.

## Deploy in brief (wrangler)

```bash
npm install -g wrangler
wrangler login

mkdir cf-relay && cd cf-relay
```

`src/index.js`:

```js
export default {
  async fetch(request) {
    const url = new URL(request.url);
    const target = "https://api.opencode.ai" + url.pathname + url.search;

    const headers = new Headers(request.headers);
    headers.delete("host");

    return fetch(target, {
      method: request.method,
      headers,
      body: request.body,
    });
  },
};
```

`wrangler.toml`:

```toml
name = "oc-relay"
main = "src/index.js"
compatibility_date = "2026-08-01"

[observability]
enabled = true
```

Deploy and grab the URL:

```bash
wrangler deploy
# output: https://oc-relay.<subdomain>.workers.dev
```

## Wiring into 9Router

In the dashboard, create or edit the OpenCode provider connection and point its base URL at the worker:

```
https://oc-relay.<subdomain>.workers.dev/v1
```

All paths (`/v1/chat/completions`, etc.) pass through automatically.

### Where the API key goes

OpenCode's free tier is **no-auth**: it does not need an API key, and 9Router should use a no-auth credential for this connection. So for the free-tier case, there is nothing to paste — leave the connection's auth empty and OpenCode answers anyway.

The worker itself forwards whatever `Authorization` header it receives, so the same relay works for a keyed provider later: put that provider's key in 9Router (not in the worker), and 9Router sends it through the relay untouched. Never hardcode keys into `index.js`; Cloudflare Workers is public and any hardcoded secret leaks.

## Why the relay sometimes "errors"

Most relay failures are header/casing problems, not Cloudflare. Common causes and the fixes already in `index.js`:

- **A stray `host` header.** Forwarding the original `host` breaks TLS routing on the upstream; the code deletes `host` before sending.
- **403s.** Usually the free account has the Relay/Workers subdomain blocked or the `api.opencode.ai` route mismatch; check `compatibility_date` is set (it is) and that the request path resolves against `.../v1/`.
- **429s.** OpenCode rate-limit, not a relay fault. If one stable edge IP appears, back off and accept ~50/day on this identity, or fall back to the pool.
- **Mixed-case / dropped headers.** The worker does a pass-through copy, so header casing is preserved as Cloudflare sends it.

If you still see errors after deploying this exact code, it is almost always the upstream treating the Cloudflare edge IP specially, not a bug in the relay.

## Where go-proxygen fits

Optional and independent:

- Relay only: stable, but the daily quota bites once (one identity)
- Pool only: quota multiplied across thousands of identities, but lists rot fast
- Both on separate 9Router connections: relay as fallback when the pool is having a bad day

`--check` validation does not apply to the relay (a worker is not an HTTP proxy), so pool health stays on its own path.
