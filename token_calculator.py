#!/usr/bin/env python3
"""
Token Usage Calculator for DeepSeek V4 Flash Free
Based on OpenCode free tier quotas
"""

# Parameters from analysis
REQUESTS_PER_PROXY = 40  # Estimated quota per IP per day
PROXY_COUNT_CONSERVATIVE = 499
PROXY_COUNT_OPTIMAL = 500
PROXY_COUNT_AGGRESSIVE = 750

# DeepSeek V4 Flash Free specifications (estimated)
avg_prompt_tokens = 50       # Average user prompt length
avg_response_tokens = 500    # Average AI response (conservative)
max_context_per_request = 128_000  # Model's context window (not relevant here)

def calculate_tokens(proxies, name):
    """Calculate total daily token usage"""
    
    total_requests = proxies * REQUESTS_PER_PROXY
    
    # Calculate input/output tokens separately
    input_tokens_daily = total_requests * avg_prompt_tokens
    output_tokens_daily = total_requests * avg_response_tokens
    total_tokens_daily = input_tokens_daily + output_tokens_daily
    
    return {
        'name': name,
        'proxies': proxies,
        'total_requests': total_requests,
        'input_tokens': input_tokens_daily,
        'output_tokens': output_tokens_daily,
        'total_tokens': total_tokens_daily,
        'requests_per_proxy': REQUESTS_PER_PROXY
    }

def main():
    print("=" * 70)
    print("🔮 DEEPSEEK V4 FLASH FREE TOKEN USAGE CALCULATOR")
    print("=" * 70)
    
    scenarios = [
        ("Conservative (499)", 499),
        ("Optimal (500)", 500),
        ("Aggressive (750)", 750),
        ("Maximum Safe (1000)", 1000),
    ]
    
    results = []
    for name, count in scenarios:
        result = calculate_tokens(count, name)
        results.append(result)
        
        print(f"\n{name.capitalize()} SCENARIO")
        print("-" * 70)
        print(f"Proxies Used:              {result['proxies']:,}")
        print(f"Total Requests/Day:        {result['total_requests']:,}")
        print(f"Input Tokens/Day:          {result['input_tokens']:,} (~{result['input_tokens']/1e6:.1f}M)")
        print(f"Output Tokens/Day:         {result['output_tokens']:,} (~{result['output_tokens']/1e6:.1f}M)")
        print(f"TOTAL Tokens/Day:          {result['total_tokens']:,} (~{result['total_tokens']/1e6:.2f}M)")
        print(f"Requests per Proxy:        {result['requests_per_proxy']}")
    
    # Summary table
    print("\n" + "=" * 70)
    print("📊 SUMMARY TABLE")
    print("=" * 70)
    print(f"{'Scenario':<25} {'Req/Day':>15} {'Tokens/Day':>20}")
    print("-" * 60)
    
    for r in results:
        print(f"{r['name']:<25} {r['total_requests']:>15,} {r['total_tokens']:>20,}")
    
    # Realistic average scenario
    print("\n" + "=" * 70)
    print("💡 REALISTIC AVERAGE DAILY USE")
    print("=" * 70)
    
    print("""
If you use typical prompts:
• Short query: ~50-100 prompt tokens → ~200-500 response tokens
• Medium query: ~200-500 prompt tokens → ~500-1000 response tokens
• Long query: ~1000+ prompt tokens → ~1000-2000 response tokens

With 500 proxies × 40 requests each:
→ Total possible: ~20,000 requests/day
→ Realistic average output: ~10M tokens/day (assuming 500 tokens/response)
→ This equals approximately:
   • 20,000 moderate-length conversations
   • OR 10,000 detailed responses
   • OR 5,000 creative writing sessions

At 500 tokens/response avg:
→ Monthly capacity: ~300 MILLION tokens (FREE!)
→ Daily cost if paid (OpenAI rates): ~$50-100/month
→ Actual cost: $0 - YOU GET IT FOR FREE! 🎉
""")

if __name__ == "__main__":
    main()
