# 快速解决方案

## 当前问题

你遇到了 `ModuleNotFoundError: No module named 'arxiv'` 错误。

**原因**: 你在 **base conda 环境**中运行,而依赖包安装在**项目虚拟环境** `.venv` 中。

## 解决方法

### 方法 1: 使用运行脚本(推荐)

```bash
cd /Users/yuzuan/ZotWatcher
./run.sh
```

这个脚本会自动:
- 激活虚拟环境
- 检查并安装依赖
- 提供交互式菜单

### 方法 2: 手动激活虚拟环境

```bash
cd /Users/yuzuan/ZotWatcher
source .venv/bin/activate

# 现在可以运行任何命令
python -m src.cli profile --full
python -m src.cli watch --rss --report --top 50
python diagnose.py
```

### 方法 3: 使用完整路径

```bash
cd /Users/yuzuan/ZotWatcher
/Users/yuzuan/ZotWatcher/.venv/bin/python -m src.cli watch --rss --report --top 50
```

## 常用命令

激活虚拟环境后:

```bash
# 构建画像
python -m src.cli profile --full

# 监测新文献
python -m src.cli watch --rss --report --top 50

# 诊断系统
python diagnose.py

# 监控画像构建进度
./monitor.sh

# 退出虚拟环境
deactivate
```

## GitHub Actions

GitHub Actions 会自动使用正确的环境,不受影响。只需:

1. 确保 GitHub Secrets 已配置:
   - `ZOTERO_API_KEY`
   - `ZOTERO_USER_ID`

2. 启用 GitHub Pages:
   - Settings → Pages → Source: **GitHub Actions**

3. 推送代码:
   ```bash
   git add .
   git commit -m "Add migration guide and run script"
   git push
   ```

## RSS 订阅地址

部署完成后:
```
https://yuzuan.github.io/ZotWatcher/feed.xml
```

## 迁移到参考架构

如果你想采用 Yorks0n/ZotWatch 的改进,请参考:
- **MIGRATION_GUIDE.md** - 详细迁移方案
- **ZOTERO_RSS_SETUP.md** - RSS 订阅配置

## 需要帮助?

1. 运行诊断: `./run.sh` 选择 3
2. 查看日志: `cat profile_build.log`
3. 检查虚拟环境: `which python` (激活后应显示 `.venv/bin/python`)
