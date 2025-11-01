#!/usr/bin/env python3
"""测试 Zotero API 连接"""
from pyzotero import zotero
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv('ZOTERO_API_KEY')
user_id = os.getenv('ZOTERO_USER_ID')

print(f'API Key: {api_key[:10]}...' if api_key else 'API Key: None')
print(f'User ID: {user_id}')
print('-' * 50)

try:
    zot = zotero.Zotero(user_id, 'user', api_key)
    
    # 获取库的基本信息
    print('正在连接 Zotero...')
    items = zot.items(limit=10)
    
    print(f'\n✓ 连接成功!')
    print(f'您的 Zotero 库中前10个条目:')
    print(f'总数: {len(items)} 个条目')
    
    if not items:
        print('\n⚠️  您的 Zotero 库是空的!')
        print('请先在 Zotero 中添加一些文献，然后再构建画像。')
    else:
        print('\n文献列表:')
        for i, item in enumerate(items, 1):
            data = item.get('data', {})
            title = data.get('title', '无标题')
            item_type = data.get('itemType', '未知类型')
            print(f'{i}. [{item_type}] {title[:80]}')
            
except Exception as e:
    print(f'\n✗ 连接失败: {e}')
    print('\n可能的原因:')
    print('1. API Key 或 User ID 不正确')
    print('2. 网络连接问题')
    print('3. Zotero API 服务不可用')
