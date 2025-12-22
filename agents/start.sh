#!/bin/bash

# Claude Qualification Agent Startup Script

echo "======================================================================"
echo "  Claude Qualification Agent"
echo "======================================================================"

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
    echo "✅ Loaded environment variables from .env"
else
    echo "⚠️  No .env file found. Using system environment variables."
fi

# Check prerequisites
echo ""
echo "Checking prerequisites..."

# Check Python
if ! command -v python &> /dev/null; then
    echo "❌ Python not found. Please install Python 3.11+"
    exit 1
fi
echo "✅ Python: $(python --version)"

# Check ANTHROPIC_API_KEY
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "❌ ANTHROPIC_API_KEY not set"
    echo "   Please set it in .env or export it:"
    echo "   export ANTHROPIC_API_KEY=sk-ant-api03-..."
    exit 1
fi
echo "✅ Anthropic API key configured"

# Check MCP server
echo ""
echo "Checking MCP server..."
if curl -s --fail http://localhost:8000/health > /dev/null; then
    echo "✅ MCP server is running"
else
    echo "⚠️  MCP server not responding at http://localhost:8000"
    echo "   Start it with: cd ../mcp_server && python server.py"
    echo ""
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check Supabase
if [ -n "$SUPABASE_URL" ]; then
    echo "✅ Supabase URL configured: $SUPABASE_URL"
else
    echo "⚠️  SUPABASE_URL not set (optional)"
fi

# Install dependencies if needed
if [ ! -d "venv" ]; then
    echo ""
    echo "Creating virtual environment..."
    python -m venv venv
    source venv/bin/activate
    echo "Installing dependencies..."
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# Start server
echo ""
echo "======================================================================"
echo "  Starting Claude Qualification Agent API"
echo "======================================================================"
echo ""
echo "  Server: http://localhost:${PORT:-8080}"
echo "  Docs:   http://localhost:${PORT:-8080}/docs"
echo "  Health: http://localhost:${PORT:-8080}/health"
echo ""
echo "======================================================================"
echo ""

python api_server.py
