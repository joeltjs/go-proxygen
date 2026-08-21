#!/usr/bin/env python3
"""
Token Calculator v2 - With Multiple Free Models
Calculates combined usage across different free tier models
"""

# Parameters (same as before)
PROXY_COUNT = 1500
REQUESTS_PER_PROXY = 40
DAILY_REQUESTS = PROXY_COUNT * REQUESTS_PER_PROXY  # 60,000

# Model distribution strategy (balanced across free tiers)
MODEL_SPLITS = {
    "mimo-v2.5-free":         {"weight": 0.33, "tokens_per_req": 800},
    "minimax-m3-free":        {"weight": 0.33, "tokens_per_req": 750},
    "qwen3.6-plus-free":      {"weight": 0.34, "tokens_per_req": 850}
}

def calculate_model_usage():
    print("="*70)
    print("🔮 TOKEN CALCULATOR - MULTI-MODEL FREE TIER STRATEGY")
    print("="*70)
    
    total_input_tokens = 0
    total_output_tokens = 0
    
    for model_name, config in MODEL_SPLITS.items():
        requests_daily = int(DAILY_REQUESTS * config["weight"])
        tokens_per_request = config["tokens_per_req"]
        
        input_tokens = requests_daily * 100  # Average prompt tokens
        output_tokens = requests_daily * tokens_per_request
        
        total_input_tokens += input_tokens
        total_output_tokens += output_tokens
        
        print(f"\n{model_name.upper()}")
        print("-" * 70)
        print(f"   Daily requests:    {requests_daily:,}")
        print(f"   Input tokens/day:  {input_tokens:,} (~{input_tokens/1e6:.1f}M)")
        print(f"   Output tokens/day: {output_tokens:,} (~{output_tokens/1e6:.1f}M)")
    
    monthly_total = (total_input_tokens + total_output_tokens) * 30
    
    print(f"\n{'='*70}")
    print("💰 COST BREAKDOWN (If Paid Separately)")
    print("="*70)
    
    # Estimate costs based on typical API pricing
    mimo_cost = total_input_tokens * 30 * 0.0000005  # ~$0.50/M input
    minimax_cost = total_input_tokens * 30 * 0.0000006  # ~$0.60/M input
    qwen_cost = total_input_tokens * 30 * 0.0000007   # ~$0.70/M input
    
    estimated_monthly = (total_output_tokens * 30 * 0.000001) * 2  # Average output rate
    
    print(f"Mimo monthly value:    ${mimo_cost:,.0f}")
    print(f"Minimax monthly value: ${minimax_cost:,.0f}")
    print(f"Qwen monthly value:    ${qwen_cost:,.0f}")
    print(f"\nTOTAL MONTHLY VALUE:   ${estimated_monthly:,.0f}")
    print(f"ACTUAL COST YOU PAY:   $0.00/month - FREE FOREVER!")
    
    return total_output_tokens

if __name__ == "__main__":
    calculate_model_usage()
