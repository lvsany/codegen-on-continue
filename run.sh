#!/bin/bash

# python版本为3.9，请在执行之前先确保版本正确
# 检查并切换 Node.js 版本20.19.0

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_ROOT"



# 设置端口
PORT=5002

# 更新 projectgen-server/.env 中的 PORT
sed -i '' "s/^PORT=.*/PORT=$PORT/" "$PROJECT_ROOT/projectgen-server/.env"

# 更新 projectgen.ts 中的 SERVER_URL
TS_FILE="$PROJECT_ROOT/continue/core/commands/slash/built-in-legacy/projectgen.ts"
sed -i '' "s|const SERVER_URL = \"http://localhost:[0-9]*\"|const SERVER_URL = \"http://localhost:$PORT\"|g" "$TS_FILE"

# 先启动后端
cd "$PROJECT_ROOT/projectgen-server"

pip install -r requirements.txt

echo "[DEBUG] start projectgen-server!!!"

python main.py &
SERVER_PID=$! # 在后台执行

sleep 3

# 检查服务器是否运行
if kill -0 $SERVER_PID 2>/dev/null; then
    echo ""
    echo "[DEBUG] starting server successful (PID: $SERVER_PID)"
else
    echo ""
    echo "[DEBUG] Failed 2 start server"
    exit 1
fi

# 提示启动 Continue
echo ""
echo "启动步骤 2/2: 启动 Continue 扩展"
echo "--------------------------------------"
echo ""
echo "请在 VS Code 中完成以下步骤："
echo ""
echo "1. 打开 continue 文件夹"
echo "   cd $PROJECT_ROOT/continue"
echo "   code ."
echo ""
echo "2. 如果是首次运行，需要先安装依赖："
echo "./scripts/install-dependencies.sh"
echo ""
echo "3. 按 F5 启动调试"
echo ""
echo "4. 在新窗口中打开工作区"
echo ""
echo "5. 使用命令："
echo "   /projectgen repo=bplustree"
echo "   /projectgen project=datasets"
echo ""
echo "======================================"
echo ""
echo "按 Ctrl+C 停止服务器"
echo ""

# 等待用户中断
trap "echo ''; echo '正在停止服务器...'; kill $SERVER_PID 2>/dev/null; echo '服务器已停止'; exit 0" INT

# 保持脚本运行
wait $SERVER_PID
