#!/bin/bash
# 监控画像构建进度

echo "=========================================="
echo "ZotWatcher 画像构建监控"
echo "=========================================="
echo ""

# 检查进程是否在运行
if ps aux | grep -v grep | grep "src.cli profile" > /dev/null; then
    echo "✓ 构建进程正在运行"
    echo ""
else
    echo "✗ 构建进程未运行"
    echo ""
fi

# 显示日志最后几行
if [ -f "profile_build.log" ]; then
    echo "最新日志:"
    echo "------------------------------------------"
    tail -15 profile_build.log
    echo "------------------------------------------"
fi

# 检查生成的文件
echo ""
echo "画像文件状态:"
echo "------------------------------------------"
for file in data/profile.sqlite data/faiss.index data/profile.json; do
    if [ -f "$file" ]; then
        size=$(ls -lh "$file" | awk '{print $5}')
        echo "✓ $file ($size)"
    else
        echo "✗ $file (未生成)"
    fi
done

# 检查模型缓存
echo ""
echo "模型缓存:"
if [ -d "$HOME/.cache/huggingface" ]; then
    cache_size=$(du -sh "$HOME/.cache/huggingface" 2>/dev/null | awk '{print $1}')
    echo "✓ HuggingFace 缓存: $cache_size"
else
    echo "✗ HuggingFace 缓存目录不存在"
fi
