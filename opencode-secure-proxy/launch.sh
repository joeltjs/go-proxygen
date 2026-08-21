#!/bin/bash
# Quick Launcher untuk Opencode Secure Proxy Pool System
# Jalankan semua yang diperlukan dengan satu command

set -e  # Exit on error

echo "🔧 Starting Opencode Secure Proxy Pool System..."
echo ""

# Check if API key is set
if [ -z "$OPENCODE_API_KEY" ]; then
    echo "⚠️ WARNING: OPENCODE_API_KEY not set!"
    echo ""
    echo "Please set it first:"
    echo "  export OPENCODE_API_KEY='your_api_key_here'"
    echo ""
    echo "Or add to .env file:"
    echo "  OPENCODE_API_KEY=your_api_key_here"
    echo ""
    read -p "Do you want to continue without API key? (y/n): " confirm
    if [ "$confirm" != "y" ]; then
        exit 1
    fi
fi

# Install dependencies if needed
if ! python3 -c "import aiohttp" 2>/dev/null; then
    echo "📦 Installing required dependencies..."
    pip install aiohttp python-dotenv -q
fi

# Change to project directory
cd "$(dirname "$0")"

# Check for proxy files
PROXY_HTTP="./proxies/validated_http.txt"
PROXY_SOCKS="./proxies/validated_socks.txt"

if [ ! -f "$PROXY_HTTP" ] && [ ! -f "$PROXY_SOCKS" ]; then
    echo "⚠️ No validated proxy files found!"
    echo ""
    echo "Would you like to run proxy validator?"
    echo "  Yes  - Run validator and load proxies"
    echo "  No   - Run client without proxy routing"
    echo ""
    read -p "Choose (yes/no): " proxy_choice
    
    if [ "$proxy_choice" = "yes" ] || [ "$proxy_choice" = "y" ]; then
        echo ""
        echo "🔄 Running proxy validator..."
        
        # Try enhanced validator first
        if [ -f "./validator_enhanced.py" ]; then
            python3 validator_enhanced.py
        elif [ -f "./validator_fast.py" ]; then
            python3 validator_fast.py
        else
            echo "❌ No validator found!"
            exit 1
        fi
        
        echo ""
        echo "✅ Validator complete!"
    else
        echo "ℹ️ Continuing without proxy routing..."
    fi
else
    echo "✅ Found validated proxies"
fi

# Run main client
echo ""
echo "🚀 Starting main client..."
echo ""

python3 main_client.py
