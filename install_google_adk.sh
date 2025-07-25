#!/bin/bash
# install_google_adk.sh
# Installation script for Google ADK and dependencies

echo "🚀 Installing Google ADK for City Pulse Agent"
echo "=============================================="

# Check Python version
python_version=$(python3 --version 2>&1 | grep -Po '(?<=Python )\d+\.\d+')
required_version="3.9"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" = "$required_version" ]; then
    echo "✅ Python version $python_version is compatible (>= 3.9)"
else
    echo "❌ Python version $python_version is not compatible. Requires >= 3.9"
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source .venv/bin/activate

# Upgrade pip
echo "⬆️ Upgrading pip..."
pip install --upgrade pip

# Install Google ADK
echo "🤖 Installing Google ADK..."
pip install google-adk

# Install additional dependencies
echo "📚 Installing additional dependencies..."
pip install litellm
pip install httpx

# Install requirements
if [ -f "requirements_adk.txt" ]; then
    echo "📋 Installing requirements from requirements_adk.txt..."
    pip install -r requirements_adk.txt
elif [ -f "requirements.txt" ]; then
    echo "📋 Installing requirements from requirements.txt..."
    pip install -r requirements.txt
fi

# Verify installation
echo "🔍 Verifying installation..."
python3 -c "
try:
    import google.adk.agents
    print('✅ Google ADK successfully installed')
except ImportError as e:
    print(f'❌ Google ADK installation failed: {e}')
    exit(1)

try:
    import litellm
    print('✅ LiteLLM successfully installed')
except ImportError as e:
    print(f'❌ LiteLLM installation failed: {e}')

try:
    from google.adk.agents import Agent
    print('✅ ADK Agent class available')
except ImportError as e:
    print(f'❌ ADK Agent import failed: {e}')
"

# Check environment variables
echo "🔑 Checking environment variables..."
if [ -f ".env" ]; then
    if grep -q "GEMINI_API_KEY" .env; then
        echo "✅ GEMINI_API_KEY found in .env"
    else
        echo "⚠️  GEMINI_API_KEY not found in .env file"
        echo "Please add your Gemini API key to the .env file:"
        echo "GEMINI_API_KEY=your_api_key_here"
    fi
else
    echo "⚠️  .env file not found"
    echo "Please create a .env file with your API keys"
fi

echo ""
echo "🎉 Installation completed!"
echo ""
echo "Next steps:"
echo "1. Ensure your .env file has GEMINI_API_KEY set"
echo "2. Start the server: python3 main.py"
echo "3. Test ADK functionality: python3 test_google_adk_agent.py"
echo ""
echo "ADK endpoints will be available at:"
echo "- http://localhost:8000/adk/test/status - Check ADK status"
echo "- http://localhost:8000/adk/chat - ADK chat endpoint"
echo "- http://localhost:8000/adk/dashboard - ADK dashboard endpoint"
echo "- http://localhost:8000/docs - API documentation"
