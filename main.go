package main

import (
	"bufio"
	"encoding/json"
	"flag"
	"fmt"
	"net/http"
	"net/url"
	"os"
	"math/rand"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
	"sync"
	"time"
)

const (
	defaultOutput    = "proxies.txt"
	blacklistFile    = "blacklist.txt"
	checkURL         = "https://api.opencode.ai"
	version          = "1.0.0"
	maxScanTokenSize = 1024 * 1024
)

type Source struct {
	Name string `json:"name"`
	URL  string `json:"url"`
}

var defaultSources = []Source{
	{"TheSpeedX HTTP", "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt"},
	{"TheSpeedX SOCKS5", "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks5.txt"},
	{"Proxifly", "https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/all/data.txt"},
	{"rix4uni", "https://raw.githubusercontent.com/rix4uni/fresh-proxy-list/main/proxylist.txt"},
	{"monosans HTTP", "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt"},
	{"monosans SOCKS5", "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks5.txt"},
	{"zevtyardt HTTP", "https://raw.githubusercontent.com/zevtyardt/proxy-list/main/http.txt"},
	{"roosterkid", "https://raw.githubusercontent.com/roosterkid/openproxylist/main/HTTPS_RAW.txt"},
}

var knownSchemes = []string{"http://", "https://", "socks4://", "socks5://"}

type checkResult struct {
	proxy string
	ok    bool
}

func main() {
	count := flag.Int("count", 0, "max proxies in output (0 = all found)")
	doCheck := flag.Bool("check", false, "test candidates against OpenCode before writing")
	checkTimeout := flag.Duration("check-timeout", 6*time.Second, "per-proxy timeout for --check")
	fetchTimeout := flag.Duration("fetch-timeout", 15*time.Second, "source download timeout")
	output := flag.String("output", defaultOutput, "output file (overwritten each run)")
	configPath := flag.String("config", "", "JSON file replacing the built-in source list")
	showVersion := flag.Bool("version", false, "print version and exit")

	var extraSources repeatedFlag
	flag.Var(&extraSources, "source", "additional source URL, repeatable")

	var localFiles repeatedFlag
	flag.Var(&localFiles, "from-file", "local proxy list file to include, repeatable")

	noFetch := flag.Bool("no-fetch", false, "skip remote sources (use with --from-file to work on local lists only)")

	flag.Parse()

	if *showVersion {
		fmt.Println("go-proxygen", version)
		return
	}

	sources := defaultSources
	if *configPath != "" {
		loaded, err := loadSourceConfig(*configPath)
		if err != nil {
			fatalf("reading config %s: %v", *configPath, err)
		}
		sources = loaded
	}
	for i, u := range extraSources.values {
		sources = append(sources, Source{Name: fmt.Sprintf("Extra %d", i+1), URL: u})
	}

	blacklist := loadBlacklist(blacklistFile)
	if len(blacklist) > 0 {
		fmt.Printf("Blacklist loaded: %d entries will be skipped\n", len(blacklist))
	}

	var candidates []string
	if !*noFetch {
		fmt.Println("Fetching sources:")
		fetched := fetchAll(sources, *fetchTimeout)
		for _, batch := range fetched {
			candidates = append(candidates, batch...)
		}
	}

	for _, path := range localFiles.values {
		lines := readLocalFile(path)
		fmt.Printf("  %-18s %6d proxies\n", filepath.Base(path), len(lines))
		candidates = append(candidates, lines...)
	}

	pool := dedupe(candidates)
	if skipped := len(pool) - countNonBlacklisted(pool, blacklist); skipped > 0 {
		fmt.Printf("Skipped %d blacklisted entries\n", skipped)
	}
	candidates = filterBlacklist(pool, blacklist)

	// Free proxies die constantly, so any fixed slice of the list is as good as
	// another. Shuffling spreads the output across sources instead of dumping
	// thousands of entries from whichever source happens to sort first.
	shuffle(candidates)

	fmt.Printf("\nUnique candidates after dedupe: %d\n", len(candidates))

	if *doCheck {
		// Checking is slow; when a count is requested there is no point testing
		// the whole internet. Sample twice the target and keep what survives.
		sample := candidates
		if limit := *count * 2; *count > 0 && len(candidates) > limit {
			sample = candidates[:limit]
			fmt.Printf("Sampling %d candidates for checking (2x target)\n", limit)
		} else if *count <= 0 && len(sample) > 10000 {
			fmt.Fprintf(os.Stderr, "warning: checking %d candidates will take a while; pass --count to sample a subset\n", len(sample))
		}
		fmt.Printf("Checking candidates against %s ...\n", checkURL)
		alive, dead := runChecks(sample, *checkTimeout)
		appendBlacklist(blacklistFile, dead)
		fmt.Printf("Appended %d dead proxies to %s\n", len(dead), blacklistFile)
		candidates = alive
	}

	limit := *count
	if limit <= 0 || limit > len(candidates) {
		limit = len(candidates)
	}
	if *doCheck && limit == 0 {
		fmt.Println("\nNo proxies survived checking. Free lists decay fast; rerun for a fresh sample or raise --count so more candidates get tested.")
	}

	final := candidates[:limit]

	if err := os.WriteFile(*output, []byte(strings.Join(final, "\n")+"\n"), 0o644); err != nil {
		fatalf("writing %s: %v", *output, err)
	}

	fmt.Printf("\nWrote %d proxies to %s\n", len(final), *output)
	fmt.Println("Paste the contents into 9Router > Proxy Pools > Batch Import.")
}

// --- sources ---

func loadSourceConfig(path string) ([]Source, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	var sources []Source
	if err := json.Unmarshal(data, &sources); err != nil {
		return nil, err
	}
	if len(sources) == 0 {
		return nil, fmt.Errorf("no sources defined")
	}
	return sources, nil
}

// mirrors returns fallback URLs for a source. If GitHub raw is unreachable,
// the same file is retried through the jsDelivr CDN.
func mirrors(rawURL string) []string {
	urls := []string{rawURL}
	const prefix = "https://raw.githubusercontent.com/"
	if !strings.HasPrefix(rawURL, prefix) {
		return urls
	}
	rest := strings.TrimPrefix(rawURL, prefix) // owner/repo/branch/path...
	parts := strings.SplitN(rest, "/", 3)
	if len(parts) == 3 {
		urls = append(urls,
			fmt.Sprintf("https://cdn.jsdelivr.net/gh/%s/%s@%s", parts[0], parts[1], parts[2]))
	}
	return urls
}

func fetchAll(sources []Source, timeout time.Duration) [][]string {
	results := make([][]string, len(sources))
	var wg sync.WaitGroup
	for i, s := range sources {
		wg.Add(1)
		go func(i int, s Source) {
			defer wg.Done()
			results[i] = fetchOne(s, timeout)
		}(i, s)
	}
	wg.Wait()
	return results
}

func fetchOne(s Source, timeout time.Duration) []string {
	client := &http.Client{Timeout: timeout}
	for _, u := range mirrors(s.URL) {
		resp, err := client.Get(u)
		if err != nil || resp.StatusCode != http.StatusOK {
			if resp != nil {
				resp.Body.Close()
			}
			continue
		}
		var lines []string
		scanner := bufio.NewScanner(resp.Body)
		scanner.Buffer(make([]byte, maxScanTokenSize), maxScanTokenSize)
		for scanner.Scan() {
			if p, ok := normalizeLine(scanner.Text()); ok {
				lines = append(lines, p)
			}
		}
		resp.Body.Close()
		via := "github"
		if u != s.URL {
			via = "jsdelivr"
		}
		fmt.Printf("  %-18s %6d proxies  (%s)\n", s.Name, len(lines), via)
		return lines
	}
	fmt.Printf("  %-18s failed (all mirrors)\n", s.Name)
	return nil
}

func readLocalFile(path string) []string {
	f, err := os.Open(path)
	if err != nil {
		fmt.Printf("  %-18s failed (%v)\n", filepath.Base(path), err)
		return nil
	}
	defer f.Close()

	var lines []string
	scanner := bufio.NewScanner(f)
	scanner.Buffer(make([]byte, maxScanTokenSize), maxScanTokenSize)
	for scanner.Scan() {
		if p, ok := normalizeLine(scanner.Text()); ok {
			lines = append(lines, p)
		}
	}
	return lines
}

// --- parsing ---

// normalizeLine turns one raw line into a full proxy URL. Lines without an
// explicit scheme are treated as HTTP proxies, which matches how the source
// lists publish them.
func normalizeLine(raw string) (string, bool) {
	line := strings.TrimSpace(raw)
	if line == "" || strings.HasPrefix(line, "#") {
		return "", false
	}

	candidate := line
	if i := strings.IndexAny(line, "|,"); i >= 0 {
		candidate = strings.TrimSpace(line[:i])
	}

	scheme := "http"
	hostPort := candidate

	lower := strings.ToLower(candidate)
	for _, p := range knownSchemes {
		if strings.HasPrefix(lower, p) {
			scheme = strings.TrimSuffix(p, "://")
			hostPort = candidate[len(p):]
			break
		}
	}
	if at := strings.LastIndex(hostPort, "@"); at >= 0 {
		hostPort = hostPort[at+1:]
	}

	parts := strings.Split(hostPort, ":")
	if len(parts) != 2 || !isIPv4(parts[0]) || !isDigits(parts[1]) {
		return "", false
	}
	return fmt.Sprintf("%s://%s:%s", scheme, parts[0], parts[1]), true
}

func isIPv4(s string) bool {
	octets := strings.Split(s, ".")
	if len(octets) != 4 {
		return false
	}
	for _, o := range octets {
		n, err := strconv.Atoi(o)
		if err != nil || n < 0 || n > 255 || (len(o) > 1 && o[0] == '0') {
			return false
		}
	}
	return true
}

func isDigits(s string) bool {
	if s == "" {
		return false
	}
	for _, c := range s {
		if c < '0' || c > '9' {
			return false
		}
	}
	return true
}

// --- dedupe & blacklist ---

func dedupe(all []string) map[string]string {
	pool := make(map[string]string)
	for _, p := range all {
		key := p[strings.Index(p, "://")+3:]
		if _, exists := pool[key]; !exists {
			pool[key] = p
		}
	}
	return pool
}

func filterBlacklist(pool map[string]string, blacklist map[string]struct{}) []string {
	out := make([]string, 0, len(pool))
	for key, p := range pool {
		if _, blocked := blacklist[key]; !blocked {
			out = append(out, p)
		}
	}
	sort.Strings(out)
	return out
}

func countNonBlacklisted(pool map[string]string, blacklist map[string]struct{}) int {
	n := 0
	for key := range pool {
		if _, blocked := blacklist[key]; !blocked {
			n++
		}
	}
	return n
}

func loadBlacklist(path string) map[string]struct{} {
	set := make(map[string]struct{})
	data, err := os.ReadFile(path)
	if err != nil {
		return set
	}
	for _, line := range strings.Split(string(data), "\n") {
		line = strings.TrimSpace(line)
		if line != "" && !strings.HasPrefix(line, "#") {
			set[line] = struct{}{}
		}
	}
	return set
}

func appendBlacklist(path string, hostPorts []string) {
	if len(hostPorts) == 0 {
		return
	}
	set := loadBlacklist(path)
	for _, k := range hostPorts {
		set[k] = struct{}{}
	}
	keys := make([]string, 0, len(set))
	for k := range set {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	_ = os.WriteFile(path, []byte(strings.Join(keys, "\n")+"\n"), 0o644)
}

// --- checking ---

func runChecks(candidates []string, timeout time.Duration) (alive, dead []string) {
	sem := make(chan struct{}, 500)
	results := make(chan checkResult, len(candidates))
	var wg sync.WaitGroup

	for _, p := range candidates {
		wg.Add(1)
		go func(proxy string) {
			defer wg.Done()
			sem <- struct{}{}
			defer func() { <-sem }()

			proxyU, err := url.Parse(proxy)
			if err != nil {
				results <- checkResult{proxy, false}
				return
			}

			client := &http.Client{
				Timeout:   timeout,
				Transport: &http.Transport{Proxy: http.ProxyURL(proxyU)},
				CheckRedirect: func(*http.Request, []*http.Request) error {
					return http.ErrUseLastResponse
				},
			}
			resp, err := client.Get(checkURL)
			if err != nil {
				results <- checkResult{proxy, false}
				return
			}
			resp.Body.Close()
			results <- checkResult{proxy, true}
		}(p)
	}

	go func() {
		wg.Wait()
		close(results)
	}()

	done := 0
	total := len(candidates)
	for r := range results {
		done++
		if r.ok {
			alive = append(alive, r.proxy)
		} else {
			dead = append(dead, r.proxy)
		}
		fmt.Printf("\r  checked %d/%d  alive=%d  dead=%d", done, total, len(alive), len(dead))
	}
	fmt.Println()

	sort.Strings(alive)
	sort.Strings(dead)
	return alive, dead
}

func shuffle(items []string) {
	rand.New(rand.NewSource(time.Now().UnixNano())).Shuffle(
		len(items),
		func(i, j int) { items[i], items[j] = items[j], items[i] },
	)
}

// --- misc ---

type repeatedFlag struct {
	values []string
}

func (r *repeatedFlag) String() string { return strings.Join(r.values, ", ") }
func (r *repeatedFlag) Set(v string) error {
	r.values = append(r.values, v)
	return nil
}

func fatalf(format string, args ...any) {
	fmt.Fprintf(os.Stderr, "go-proxygen: "+format+"\n", args...)
	os.Exit(1)
}
