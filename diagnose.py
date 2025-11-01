#!/usr/bin/env python3
"""快速诊断脚本 - 检查画像构建的各个步骤"""
import os
import sys
from pathlib import Path
from pyzotero import zotero
from dotenv import load_dotenv

load_dotenv()

print("=" * 60)
print("ZotWatcher 画像诊断工具")
print("=" * 60)

# 1. 检查环境变量
print("\n[1] 检查环境变量...")
api_key = os.getenv('ZOTERO_API_KEY')
user_id = os.getenv('ZOTERO_USER_ID')

if not api_key or not user_id:
    print("✗ 环境变量缺失")
    sys.exit(1)
print(f"✓ API Key: {api_key[:10]}...")
print(f"✓ User ID: {user_id}")

# 2. 检查 Zotero 连接
print("\n[2] 检查 Zotero 连接...")
try:
    zot = zotero.Zotero(user_id, 'user', api_key)
    items = zot.items(limit=100)
    
    # 过滤掉附件和笔记
    filtered_items = []
    for item in items:
        data = item.get('data', {})
        item_type = data.get('itemType', '')
        if item_type not in ['attachment', 'note']:
            filtered_items.append(item)
    
    print(f"✓ 成功获取 {len(items)} 个条目")
    print(f"✓ 过滤后有效文献: {len(filtered_items)} 篇")
    
    if len(filtered_items) == 0:
        print("\n⚠️  警告: 没有有效的文献条目!")
        print("   您的 Zotero 库中只有附件和笔记,没有实际的文献。")
        print("   请在 Zotero 中添加一些学术文献。")
        sys.exit(0)
        
except Exception as e:
    print(f"✗ 连接失败: {e}")
    sys.exit(1)

# 3. 检查数据目录
print("\n[3] 检查数据目录...")
data_dir = Path("data")
if not data_dir.exists():
    print("✗ data/ 目录不存在")
    data_dir.mkdir(parents=True, exist_ok=True)
    print("✓ 已创建 data/ 目录")
else:
    print("✓ data/ 目录存在")

# 4. 检查画像文件
print("\n[4] 检查画像文件...")
profile_files = {
    'profile.sqlite': data_dir / 'profile.sqlite',
    'faiss.index': data_dir / 'faiss.index',
    'profile.json': data_dir / 'profile.json'
}

existing_files = []
missing_files = []

for name, path in profile_files.items():
    if path.exists():
        size = path.stat().st_size
        print(f"✓ {name} 存在 ({size} bytes)")
        existing_files.append(name)
    else:
        print(f"✗ {name} 不存在")
        missing_files.append(name)

# 5. 诊断结论
print("\n" + "=" * 60)
print("诊断结论:")
print("=" * 60)

if missing_files:
    print(f"\n您的画像文件缺失: {', '.join(missing_files)}")
    print("\n这就是为什么显示'画像为 0'!")
    print("\n解决方案:")
    print("1. 运行以下命令构建画像:")
    print(f"   python -m src.cli profile --full")
    print("\n2. 或者等待模型下载完成后再运行")
    print(f"   (sentence-transformers 模型约 90MB)")
else:
    print("\n✓ 所有画像文件都存在!")
    print(f"✓ 您的画像包含 {len(filtered_items)} 篇文献")
    print("\n如果推荐结果为 0,可能是:")
    print("- 没有找到符合条件的新文献")
    print("- 数据源(arXiv)最近没有相关更新")
    print("- 评分阈值过高")
