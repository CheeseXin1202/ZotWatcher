# Zotero RSS 订阅配置指南

## 方案 1: GitHub Pages 公开订阅（推荐）

### 第一步：启用 GitHub Pages

1. 访问你的仓库设置页面：
   ```
   https://github.com/yuzuan/ZotWatcher/settings/pages
   ```

2. 在 "Source" 下选择：
   - Source: **GitHub Actions**

3. 保存后，等待 GitHub Actions 运行完成

### 第二步：获取 RSS 订阅链接

你的 RSS feed 地址将是：
```
https://yuzuan.github.io/ZotWatcher/feed.xml
```

HTML 报告地址：
```
https://yuzuan.github.io/ZotWatcher/index.html
```

### 第三步：在 Zotero 中添加订阅

**方法 A：通过 Zotero Standalone（桌面版）**

1. 打开 Zotero 桌面应用
2. 右键点击左侧的 **"My Library"** 或任意文件夹
3. 选择 **"New Feed..."** (新建订阅源)
4. 粘贴 RSS URL：
   ```
   https://yuzuan.github.io/ZotWatcher/feed.xml
   ```
5. 点击 "Add" (添加)

**方法 B：通过 Zotero Web Library**

1. 访问 https://www.zotero.org/
2. 登录账号
3. 点击右上角的齿轮图标 → Settings
4. 选择 "Feeds" 标签
5. 点击 "Add Feed"
6. 输入 URL 和名称（如 "ZotWatcher Recommendations"）

### 第四步：配置订阅更新频率

**在 Zotero 桌面版中：**
1. 右键点击刚添加的订阅源
2. 选择 "Feed Settings..." (订阅设置)
3. 设置更新频率（建议每天一次，因为 GitHub Actions 每日 UTC 06:00 运行）

---

## 方案 2: 本地文件订阅（仅本机可用）

如果你想在本地测试 RSS 订阅：

1. **生成带有真实推荐的 feed**：
   ```bash
   # 修改 arXiv 分类和时间窗以获取更多候选
   # 编辑 config/sources.yaml，将 window_days 改为 30
   
   python -m src.cli watch --rss --report --top 50
   ```

2. **在 Zotero 中添加本地文件订阅**：
   - URL 格式：`file:///Users/yuzuan/ZotWatcher/reports/feed.xml`
   - 注意：本地订阅仅在你自己的电脑上有效

---

## 方案 3: 私有订阅（带认证）

如果你希望 RSS 订阅保持私密，可以：

### 选项 A：使用 GitHub Gist（私有）

1. **修改工作流，推送到私有 Gist**：
   
   在 `.github/workflows/daily_watch.yml` 末尾添加：
   ```yaml
   - name: Update Gist
     env:
       GIST_TOKEN: ${{ secrets.GIST_TOKEN }}
       GIST_ID: ${{ secrets.GIST_ID }}
     run: |
       curl -X PATCH \
         -H "Authorization: token $GIST_TOKEN" \
         -H "Content-Type: application/json" \
         -d "{\"files\":{\"feed.xml\":{\"content\":\"$(cat reports/feed.xml | jq -sR .)\"}}}" \
         "https://api.github.com/gists/$GIST_ID"
   ```

2. **创建 GitHub Secrets**：
   - `GIST_TOKEN`: Personal Access Token (带 gist 权限)
   - `GIST_ID`: 你创建的 Gist ID

3. **订阅 URL**：
   ```
   https://gist.githubusercontent.com/yuzuan/{GIST_ID}/raw/feed.xml
   ```

### 选项 B：使用第三方 RSS 托管服务

支持私有 RSS 的服务：
- **Feedbin** (https://feedbin.com/)
- **Feedly** (https://feedly.com/)
- **Inoreader** (https://www.inoreader.com/)

这些服务支持 HTTP 认证或私有链接。

---

## 测试订阅是否生效

### 1. 确认 RSS feed 有内容

访问你的 RSS URL，应该能看到类似这样的 XML：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>ZotWatcher Recommendations</title>
    <description>Personalized academic literature recommendations</description>
    <item>
      <title>文章标题</title>
      <link>文章链接</link>
      <description>摘要内容</description>
      <pubDate>发布日期</pubDate>
    </item>
  </channel>
</rss>
```

### 2. 在 Zotero 中刷新订阅

- 右键点击订阅源
- 选择 "Update Feed" (更新订阅)
- 新推荐的文章会出现在订阅文件夹中

### 3. 查看推荐文章

- Zotero 会自动从 RSS 中提取文章元数据
- 你可以直接添加到个人文库
- 或者右键 → "Add to My Library" 收藏感兴趣的文章

---

## 优化建议

### 增加候选文章数量

编辑 `config/sources.yaml`：

```yaml
window_days: 14  # 从 7 改为 14 天

arxiv:
  enabled: true
  categories: 
    - "q-bio.GN"
    - "cs.LG"
    - "cs.AI"      # 新增
    - "cs.CL"      # 新增
    - "stat.ML"    # 新增
  max_results: 100
```

### 自定义 RSS feed 标题和描述

编辑 `src/watcher.py` 中的 `generate_rss()` 方法，修改：

```python
feed.title = "我的学术推荐 - ZotWatcher"
feed.description = "基于我的研究兴趣自动推荐的最新文献"
feed.link = href="https://yuzuan.github.io/ZotWatcher/"
```

### 调整推荐数量

```bash
# 生成前 100 篇推荐（默认）
python -m src.cli watch --rss --report --top 100

# 生成前 20 篇推荐（精选）
python -m src.cli watch --rss --report --top 20
```

---

## 故障排查

### 问题 1: Zotero 提示 "无法连接到订阅源"

**原因**：GitHub Pages 尚未部署或 URL 错误

**解决**：
1. 检查 GitHub Actions 运行状态：
   ```
   https://github.com/yuzuan/ZotWatcher/actions
   ```
2. 确认 Pages 已启用：
   ```
   https://github.com/yuzuan/ZotWatcher/settings/pages
   ```
3. 等待 5-10 分钟让部署生效

### 问题 2: RSS 订阅是空的（没有文章）

**原因**：没有找到符合条件的新文献

**解决**：
1. 增加时间窗口：`window_days: 30`
2. 增加 arXiv 分类
3. 检查日志：
   ```bash
   cat profile_build.log | grep "获取到"
   ```

### 问题 3: Zotero 不更新订阅

**原因**：更新频率设置过低或手动刷新

**解决**：
1. 右键订阅 → Feed Settings → 设置自动更新
2. 手动刷新：右键 → Update Feed
3. 重启 Zotero

---

## 高级功能：自动导入到 Zotero 库

如果你想让推荐的文章自动添加到你的 Zotero 库（而不只是订阅），可以：

1. **修改 `src/cli.py` 的 watch_command**：
   ```python
   if args.auto_import:
       watcher.push_to_zotero(recommendations[:10])  # 自动导入前10篇
       logger.info("已自动导入前 10 篇推荐到 Zotero")
   ```

2. **添加命令行参数**：
   ```python
   watch_parser.add_argument(
       "--auto-import",
       action="store_true",
       help="自动将推荐文章导入 Zotero 库"
   )
   ```

3. **运行**：
   ```bash
   python -m src.cli watch --rss --report --auto-import
   ```

**注意**：需要在 `src/watcher.py` 中实现 `push_to_zotero()` 方法（当前是占位）。

---

## 总结

**最简单的方式（推荐新手）**：
1. 启用 GitHub Pages
2. 在 Zotero 中添加订阅：`https://yuzuan.github.io/ZotWatcher/feed.xml`
3. 每天自动获取推荐

**更新频率**：
- GitHub Actions: 每天 UTC 06:00 (北京时间 14:00)
- Zotero 订阅：建议每天检查一次

**下一步**：
- 调整 `config/sources.yaml` 获取更多候选
- 查看 HTML 报告了解推荐详情
- 根据反馈调整评分权重

有任何问题欢迎提出！
