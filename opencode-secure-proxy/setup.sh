#!/bin/bash
# Setup Script - Install & Configure Opencode Secure Proxy Pool System

set -e

echo "🔧 Setting up Opencode Secure Proxy Pool System..."
echo ""

# Create directory structure
mkdir -p config proxies blacklist logs data

echo "✅ Created directory structure"

# Check Python and requirements
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 not found!"
    exit 1
fi

echo "Python version: $(python3 --version)"

# Install dependencies
echo ""
echo "📦 Installing Python dependencies..."
pip install aiohttp python-dotenv geoip2 pycryptodome

# Create sample .env file if not exists
if [ ! -f ".env" ]; then
    echo ""
    echo "⚠️ No .env file found!"
    echo ""
    cat > .env << EOF
OPENCODE_API_KEY=your_actual_api_key_here
ENVIRONMENT=production
LOG_LEVEL=WARNING
EOF
    
    echo "Created .env file"
    echo "Please edit it and add your real API key:"
    echo "  nano .env"
    echo ""
else
    echo "✅ Found existing .env file"
fi

# Download sample proxy lists for testing
echo ""
echo "📥 Downloading sample proxy lists..."

mkdir -p proxies

if [ ! -f "./proxies/thespeedx_raw.txt" ]; then
    curl -sL "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt" > ./proxies/thespeedx_raw.txt
    echo "✅ Downloaded TheSpeedX proxies"
else
    echo "✅ Already have TheSpeedX list"
fi

# Make scripts executable
chmod +x *.py 2>/dev/null || true
chmod +x *.sh 2>/dev/null || true

# Print summary
echo ""
echo "============================================================"
echo "✅ SETUP COMPLETE!"
echo "============================================================"
echo ""
echo "Next steps:"
echo "1. Edit .env file with your OpenCode API key"
echo "2. Run validator to get valid proxies:"
echo "   python3 validator_enhanced.py"
echo "3. Or run the main client directly:"
echo "   python3 main_client.py"
echo ""
echo "For more help, see README.md or QUICKSTART.md"
echo ""
