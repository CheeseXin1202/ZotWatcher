#!/bin/bash
# ZotWatcher 运行脚本 - 自动激活虚拟环境

set -e  # 遇到错误立即退出

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=====================================${NC}"
echo -e "${GREEN}ZotWatcher 运行脚本${NC}"
echo -e "${GREEN}=====================================${NC}"
echo ""

# 检查虚拟环境
if [ ! -d ".venv" ]; then
    echo -e "${YELLOW}警告: 虚拟环境不存在,创建中...${NC}"
    python3 -m venv .venv
    echo -e "${GREEN}✓ 虚拟环境已创建${NC}"
fi

# 激活虚拟环境
echo -e "${GREEN}激活虚拟环境...${NC}"
source .venv/bin/activate

# 检查依赖
echo -e "${GREEN}检查依赖...${NC}"
if ! python -c "import arxiv" 2>/dev/null; then
    echo -e "${YELLOW}警告: 缺少依赖,安装中...${NC}"
    pip install -r requirements.txt
    echo -e "${GREEN}✓ 依赖已安装${NC}"
else
    echo -e "${GREEN}✓ 依赖已满足${NC}"
fi

echo ""
echo -e "${GREEN}=====================================${NC}"
echo -e "${GREEN}选择操作:${NC}"
echo -e "${GREEN}=====================================${NC}"
echo "1. 构建用户画像 (profile --full)"
echo "2. 监测新文献 (watch --rss --report --top 50)"
echo "3. 诊断系统状态 (diagnose.py)"
echo "4. 进入虚拟环境 shell"
echo "5. 退出"
echo ""

read -p "请选择 (1-5): " choice

case $choice in
    1)
        echo -e "${GREEN}正在构建用户画像...${NC}"
        python -m src.cli profile --full
        ;;
    2)
        echo -e "${GREEN}正在监测新文献...${NC}"
        python -m src.cli watch --rss --report --top 50
        ;;
    3)
        echo -e "${GREEN}正在诊断系统...${NC}"
        python diagnose.py
        ;;
    4)
        echo -e "${GREEN}进入虚拟环境 shell (输入 'exit' 退出)${NC}"
        $SHELL
        ;;
    5)
        echo -e "${GREEN}再见!${NC}"
        exit 0
        ;;
    *)
        echo -e "${RED}无效选择${NC}"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}=====================================${NC}"
echo -e "${GREEN}操作完成!${NC}"
echo -e "${GREEN}=====================================${NC}"
