#!/bin/bash
# Echo V3 Test Script

echo "🧪 Echo V3 Tests"
echo "================"

# Activate venv
source echo_env/bin/activate

# Test imports
echo ""
echo "1️⃣ Testing imports..."
python -c "
import sys
ok = True

for mod in ['starlette', 'uvicorn', 'httpx', 'mlx', 'mlx_lm', 'faster_whisper']:
    try:
        __import__(mod.replace('_', '-') if '-' in mod else mod)
        print(f'   ✅ {mod}')
    except ImportError:
        try:
            __import__(mod)
            print(f'   ✅ {mod}')
        except:
            print(f'   ❌ {mod}')
            ok = False

sys.exit(0 if ok else 1)
"

if [ $? -ne 0 ]; then
    echo "❌ Missing packages. Run: ./setup.sh"
    exit 1
fi

# Test syntax
echo ""
echo "2️⃣ Testing Python files..."
python -m py_compile web_server.py && echo "   ✅ web_server.py" || exit 1
python -m py_compile mlx_server.py && echo "   ✅ mlx_server.py" || exit 1  
python -m py_compile llm_client.py && echo "   ✅ llm_client.py" || exit 1
python -m py_compile database.py && echo "   ✅ database.py" || exit 1

# Test database
echo ""
echo "3️⃣ Testing database..."
python -c "import database; database.init_db(); print('   ✅ Database OK')"

echo ""
echo "================"
echo "✅ All tests passed! Run: ./run.sh"
