# go-proxygen

Fetches free proxies from public lists, deduplicates them, optionally tests each one against the OpenCode API, and writes a single file you can paste straight into [9Router](https://github.com/9router)'s proxy pool batch import.

## Why

Free AI tiers rate-limit by IP. One machine gets one quota. Rotating through a pool of working proxies multiplies that quota by however many unique IPs you can gather. This tool gathers and filters them; 9Router does the rotation.

## Why not just download the lists yourself?

You could paste a raw list into 9Router and skip this tool. Here is what that run looked like for us:

| Step | Raw lists | After go-proxygen |
|---|---|---|
| Lines across 8 public sources | ~340,000 | - |
| Unique after deduplication | ~267,000 | ~267,000 |
| Reachable from OpenCode *right now* | unknown until you try | ~0.2% survive (`--check`) |
| Dead hosts remembered so they never waste your time again | no | yes (`blacklist.txt`) |

Three problems the tool solves that raw lists cannot:

1. **"Listed" does not mean "alive".** Public aggregators keep every candidate their scrapers ever saw. In testing, only about 2 in 1,000 entries could actually complete a request to `api.opencode.ai` at any given moment. Importing raw means importing 266,800 dead IPs and letting 9Router's health check choke on them.
2. **Dead proxies come back forever.** Without a persistent blacklist, every regeneration re-imports the same corpses. go-proxygen remembers failures in `blacklist.txt` and skips them on all future runs.
3. **"Alive" has to mean something.** A proxy that answers ping can still fail TLS through itself, or hang for 30 seconds. `--check` defines alive as *completed a request to your actual target API*, which is the only definition that matters here.

On top of that: dedupe across sources, shuffle so capped runs sample fairly instead of dumping whichever list sorts first, CDN fallback when GitHub raw is down, and output formatted exactly the way 9Router's batch import parses it.

## Build

Requires Go 1.21+. No external dependencies.

```bash
go build -o go-proxygen .
```

## Usage

```bash
# fetch everything, write proxies.txt
./go-proxygen

# cap output at 1500 entries
./go-proxygen --count 1500

# test candidates against https://api.opencode.ai first;
# dead ones are appended to blacklist.txt automatically
./go-proxygen --count 1500 --check

# work on local files only (no network fetch)
./go-proxygen --from-file mylist.txt --check

# add your own source without editing code
./go-proxygen --source https://example.com/proxies.txt
```

### Flags

| Flag | Default | Description |
|---|---|---|
| `--count` | 0 | Max proxies in output. 0 means all found. |
| `--check` | off | Test each candidate through an HTTPS request to `api.opencode.ai`. Failures go to `blacklist.txt`. |
| `--check-timeout` | 6s | Per-proxy timeout during checking. |
| `--fetch-timeout` | 15s | Source download timeout. |
| `--output` | `proxies.txt` | Output file, overwritten on every run. |
| `--config` | | JSON file replacing the built-in source list. |
| `--source` | | Extra source URL. Repeatable. |
| `--from-file` | | Local list file to include. Repeatable. |
| `--no-fetch` | off | Skip remote sources. Use with `--from-file`. |

With both `--check` and `--count`, the tool samples twice your target count, checks those, and keeps survivors. Checking hundreds of thousands of candidates takes hours; always pair large pools with `--count`.

## Output

One proxy per line, matching what 9Router accepts:

```
http://1.2.3.4:8080
socks5://5.6.7.8:1080
```

Entries are shuffled before writing so a capped run spreads across sources instead of drawing from whichever list sorts first.

## Import into 9Router

1. Run the generator.
2. Open the 9Router dashboard and go to **Proxy Pools > Batch Import**.
3. Paste the entire contents of `proxies.txt`.
4. Click import, then run 9Router's own health check to drop anything that died between generation and import.
5. On the provider connection (for example OpenCode), set the rotation strategy to round-robin.

Expect heavy attrition. Public lists decay within hours; in testing, roughly 0.2% of raw candidates survived an API-level check at any given moment. Generate fresh, import fresh, and re-run regularly.

## Blacklist

`blacklist.txt` holds `host:port` pairs that are skipped on every future run. It grows automatically when `--check` finds dead proxies, and you can add entries by hand.

To start over, delete the file.

## Custom sources

Pass a JSON file to replace the built-in list:

```bash
./go-proxygen --config sources.json
```

```json
[
  { "name": "MySource", "url": "https://example.com/list.txt" }
]
```

Sources hosted on `raw.githubusercontent.com` fall back to the jsDelivr CDN automatically if GitHub is unreachable.

## Sources

Free proxies cannot be synthesized; they are real servers found in the wild. Every list on GitHub is an aggregate of the same upstream sites (`free-proxy-list.net`, `sslproxies.org`, `us-proxy.org`, `openproxy.space`, and similar), kept fresh by continuous scrapers. go-proxygen pulls from these aggregators:

- [TheSpeedX/PROXY-List](https://github.com/TheSpeedX/PROXY-List) (HTTP, SOCKS5)
- [proxifly/free-proxy-list](https://github.com/proxifly/free-proxy-list)
- [rix4uni/fresh-proxy-list](https://github.com/rix4uni/fresh-proxy-list)
- [monosans/proxy-list](https://github.com/monosans/proxy-list) (HTTP, SOCKS5)
- [zevtyardt/proxy-list](https://github.com/zevtyardt/proxy-list)
- [roosterkid/openproxylist](https://github.com/roosterkid/openproxylist)

Going straight to the upstream sites instead buys nothing: their layouts change, they rate-limit scrapers, and each needs its own parser. The GitHub layer is the stable interface — raw text over HTTPS, hourly updates, CDN mirrors.

What go-proxygen adds on top of the raw lists: deduplication across sources, a persistent blacklist, and validation that matters for this use case — every candidate is tested against `api.opencode.ai` itself with `--check`, so "alive" means reachable from OpenCode's perspective, not just pingable.

If one repo dies, remove it via `--config` or add replacements with `--source`. Nothing else changes.

## Notes on safety

Proxies see which host you connect to, not what you send: TLS protects the payload end to end. That protection covers transport only. Free-tier AI services decide their own retention policies, so do not send credentials or private data through them regardless of how many proxies you rotate.

## License

[MIT](LICENSE)
