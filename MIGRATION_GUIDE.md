# 从 Yorks0n/ZotWatch 迁移改进方案

## 概览

参考仓库使用了更模块化的架构,主要改进包括:
1. **更好的代码组织**: 分离关注点(ingest, fetch, score, dedupe, report)
2. **Pydantic 数据模型**: 类型安全和验证
3. **更健壮的 API 客户端**: 分页和错误处理
4. **缓存机制**: 12小时候选缓存
5. **更多数据源**: bioRxiv/medRxiv 实现完整
6. **去重引擎**: 使用 rapidfuzz 进行标题模糊匹配
7. **期刊质量评分**: SJR 指标支持
8. **预印本比例控制**: 防止推荐列表被预印本淹没

## 迁移策略(渐进式)

### 阶段 1: 保持现有功能,修复当前问题

**立即行动(最小改动)**:
1. 使用虚拟环境运行命令
2. 修复 arXiv 分页问题
3. 确保 GitHub Actions 正常工作

**命令**:
```bash
# 激活虚拟环境
source .venv/bin/activate

# 或创建新的虚拟环境
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 运行
python -m src.cli profile --full
python -m src.cli watch --rss --report --top 50
```

### 阶段 2: 采用参考架构的改进

**推荐改进点**:

#### 2.1 使用 Pydantic 模型(参考: models.py)
- 类型安全
- 自动验证
- 更好的 IDE 支持

#### 2.2 分离 ingest 和 profile(参考: ingest_zotero_api.py, build_profile.py)
- `ingest`: 只负责从 Zotero 同步
- `profile`: 只负责向量化和 FAISS 构建
- 增量更新更可靠

#### 2.3 候选缓存(参考: fetch_new.py)
- 12小时缓存避免频繁 API 调用
- 加速本地测试

#### 2.4 去重引擎(参考: dedupe.py)
- 使用 rapidfuzz 进行模糊标题匹配
- 避免重复推荐

#### 2.5 bioRxiv/medRxiv 实现(参考: fetch_new.py:_fetch_biorxiv)
- 完整的 API 集成
- RSS feed 解析

### 阶段 3: 完整迁移(可选)

如果你想要完全采用参考架构,可以:

1. **备份现有项目**:
```bash
cd /Users/yuzuan
cp -r ZotWatcher ZotWatcher.backup
```

2. **克隆参考仓库**:
```bash
git clone https://github.com/Yorks0n/ZotWatch.git ZotWatch-ref
cd ZotWatch-ref
```

3. **复制你的配置和数据**:
```bash
# 复制配置
cp ../ZotWatcher/.env .
cp ../ZotWatcher/config/*.yaml config/

# 复制数据(如果需要)
cp -r ../ZotWatcher/data/* data/
```

4. **安装依赖**:
```bash
pip install -r requirements.txt
```

5. **运行**:
```bash
python -m src.cli profile --full
python -m src.cli watch --rss --report --top 50
```

## 快速修复当前问题

### 问题: ModuleNotFoundError: No module named 'arxiv'

**原因**: 使用了 base conda 环境而不是项目虚拟环境

**解决方案 1**: 激活虚拟环境
```bash
cd /Users/yuzuan/ZotWatcher
source .venv/bin/activate
python -m src.cli watch --rss --report --top 50
```

**解决方案 2**: 在 base 环境安装依赖
```bash
pip install -r requirements.txt
python -m src.cli watch --rss --report --top 50
```

**解决方案 3**: 使用完整路径
```bash
/Users/yuzuan/ZotWatcher/.venv/bin/python -m src.cli watch --rss --report --top 50
```

## 推荐的最小迁移方案

### 文件级改进(优先级排序)

#### 优先级 1: 修复 arXiv 抓取
参考 `fetch_new.py:_fetch_arxiv()`:
- 使用 feedparser 而不是 arxiv 库
- 避免分页问题
- 更稳定的 API 调用

#### 优先级 2: 添加候选缓存
参考 `fetch_new.py`:
```python
def _load_cache(self):
    if self.cache_file.exists():
        data = json.loads(self.cache_file.read_text())
        if (datetime.now(timezone.utc) - iso_to_datetime(data.get("timestamp"))).seconds < 12 * 3600:
            return [CandidateWork(**item) for item in data.get("candidates", [])]
    return None
```

#### 优先级 3: 改进去重
参考 `dedupe.py`:
- 使用 rapidfuzz 进行模糊匹配
- 检查标题、DOI、URL
- 与 Zotero 库比对

#### 优先级 4: bioRxiv/medRxiv 支持
参考 `fetch_new.py:_fetch_biorxiv()`:
- RSS feed 解析
- 日期过滤
- 完整元数据

## 配置文件兼容性

你的 `config/sources.yaml` 需要调整以匹配参考架构:

**当前**:
```yaml
window_days: 7
arxiv:
  enabled: true
  categories: ["q-bio.GN", "cs.LG"]
```

**参考架构**:
```yaml
window_days: 30
arxiv:
  enabled: true
  categories: ["cs.LG", "cs.AI"]
biorxiv:
  enabled: true
  from_days_ago: 30
```

## 下一步行动

### 立即(今天)
1. ✅ 使用虚拟环境运行命令
2. ✅ 生成有候选的报告
3. ✅ 确认 GitHub Actions 工作

### 短期(本周)
1. 添加候选缓存机制
2. 改进 arXiv 抓取(使用 feedparser)
3. 实现 bioRxiv/medRxiv

### 中期(本月)
1. 采用 Pydantic 模型
2. 分离 ingest 和 profile
3. 添加去重引擎

### 长期(可选)
- 完全迁移到参考架构
- 添加期刊质量评分
- 实现预印本比例控制

## 需要帮助?

我可以帮你:
1. 创建 shell 脚本自动激活虚拟环境
2. 逐步迁移关键改进
3. 测试和验证功能
4. 更新文档

你想从哪里开始?
