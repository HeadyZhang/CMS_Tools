#!/usr/bin/env python3
"""
CMS Tools 测试脚本
请先配置环境变量或直接修改下方的 TOKEN

使用方法：
    export WP_ACCESS_TOKEN="your-token"
    python test_cms_tools.py
"""

import os
import json
import sys

# ============== 配置 ==============
# 方式1: 环境变量（推荐）
# export WP_ACCESS_TOKEN="your-token"

# 方式2: 直接配置（测试用）
WP_ACCESS_TOKEN = os.getenv("WP_ACCESS_TOKEN", "your-wordpress-access-token")
WP_SITE_ID = os.getenv("WP_SITE_ID", "251193948")

# 设置环境变量供 cms_tools 使用
os.environ["WP_ACCESS_TOKEN"] = WP_ACCESS_TOKEN
os.environ["WP_SITE_ID"] = WP_SITE_ID

# 导入 Tools
from tools.cms_tools import (
    create_article,
    update_article,
    publish_article,
    unpublish_article,
    get_article_metrics,
    list_articles_by_topic,
    get_site_stats,
)


def print_result(name: str, result: dict):
    """格式化打印结果"""
    print(f"\n{'='*60}")
    print(f"📋 {name}")
    print('='*60)
    
    if result.get("success"):
        print("✅ 成功")
        print(json.dumps(result["data"], indent=2, ensure_ascii=False))
    else:
        print("❌ 失败")
        print(f"错误: {result.get('error', 'Unknown error')}")
    
    print()


def test_get_site_stats():
    """测试: 获取站点统计"""
    print("\n" + "🔹"*30)
    print("测试 1: get_site_stats - 获取站点统计")
    print("🔹"*30)
    
    result = get_site_stats(days=7)
    print_result("站点统计 (最近7天)", result)
    return result


def test_list_articles():
    """测试: 列出文章"""
    print("\n" + "🔹"*30)
    print("测试 2: list_articles_by_topic - 资产盘点")
    print("🔹"*30)
    
    # 2.1 列出所有文章
    result = list_articles_by_topic(number=10, status="any", include_views=True)
    print_result("所有文章 (前10篇)", result)
    
    # 2.2 只看已发布的
    result = list_articles_by_topic(number=5, status="publish")
    print_result("已发布文章 (前5篇)", result)
    
    # 2.3 只看草稿
    result = list_articles_by_topic(number=5, status="draft")
    print_result("草稿文章", result)
    
    return result


def test_get_article_metrics(post_id: int):
    """测试: 获取文章表现"""
    print("\n" + "🔹"*30)
    print(f"测试 3: get_article_metrics - 获取文章 {post_id} 的表现")
    print("🔹"*30)
    
    # 3.1 基础指标
    result = get_article_metrics(post_id=post_id, days=30)
    print_result(f"文章 {post_id} 指标 (30天)", result)
    
    # 3.2 包含每日明细
    result = get_article_metrics(post_id=post_id, days=7, include_daily_breakdown=True)
    print_result(f"文章 {post_id} 每日明细 (7天)", result)
    
    return result


def test_create_and_manage_article():
    """测试: 创建、更新、发布、下线文章"""
    print("\n" + "🔹"*30)
    print("测试 4: 文章生命周期管理")
    print("🔹"*30)
    
    # 4.1 创建草稿
    print("\n📝 4.1 创建草稿...")
    result = create_article(
        title="[测试] CMS Tools 自动化测试文章",
        content="""
        <h2>测试文章</h2>
        <p>这是一篇由 CMS Tools 自动创建的测试文章。</p>
        <h2>功能测试</h2>
        <ul>
            <li>创建草稿 ✓</li>
            <li>更新内容</li>
            <li>发布上线</li>
            <li>下线处理</li>
        </ul>
        <p>测试时间: """ + __import__('datetime').datetime.now().isoformat() + """</p>
        """,
        excerpt="CMS Tools 自动化测试文章",
        categories=["测试"],
        tags=["CMS", "测试", "自动化"],
        status="draft"
    )
    print_result("创建草稿", result)
    
    if not result.get("success"):
        print("❌ 创建失败，跳过后续测试")
        return None
    
    post_id = result["data"]["post_id"]
    print(f"✅ 创建成功，文章 ID: {post_id}")
    
    # 4.2 更新内容
    print("\n📝 4.2 更新文章...")
    result = update_article(
        post_id=post_id,
        title="[测试] CMS Tools 自动化测试文章 (已更新)",
        content="""
        <h2>测试文章 - 已更新</h2>
        <p>这是一篇由 CMS Tools 自动创建并更新的测试文章。</p>
        <h2>功能测试</h2>
        <ul>
            <li>创建草稿 ✓</li>
            <li>更新内容 ✓</li>
            <li>发布上线</li>
            <li>下线处理</li>
        </ul>
        <p>更新时间: """ + __import__('datetime').datetime.now().isoformat() + """</p>
        """,
        tags=["CMS", "测试", "自动化", "已更新"]
    )
    print_result("更新文章", result)
    
    # 4.3 发布上线
    print("\n📝 4.3 发布文章...")
    result = publish_article(post_id=post_id)
    print_result("发布文章", result)
    
    if result.get("success"):
        print(f"🔗 文章链接: {result['data'].get('url', 'N/A')}")
    
    # 4.4 获取表现
    print("\n📝 4.4 获取表现指标...")
    result = get_article_metrics(post_id=post_id, days=1)
    print_result("文章表现", result)
    
    # 4.5 下线（转为草稿）
    print("\n📝 4.5 下线文章...")
    result = unpublish_article(post_id=post_id, target_status="draft")
    print_result("下线文章", result)
    
    return post_id


def test_search_articles():
    """测试: 搜索文章"""
    print("\n" + "🔹"*30)
    print("测试 5: 搜索文章")
    print("🔹"*30)
    
    # 搜索包含 "API" 的文章
    result = list_articles_by_topic(search="API", number=5)
    print_result("搜索 'API'", result)
    
    return result


def main():
    """主测试流程"""
    print("="*60)
    print("🧪 CMS Tools 完整测试")
    print("="*60)
    print(f"站点 ID: {WP_SITE_ID}")
    print(f"Token: {WP_ACCESS_TOKEN[:20]}..." if len(WP_ACCESS_TOKEN) > 20 else f"Token: {WP_ACCESS_TOKEN}")
    
    if WP_ACCESS_TOKEN == "your-wordpress-access-token":
        print("\n⚠️  警告: 请先配置 WP_ACCESS_TOKEN!")
        print("   export WP_ACCESS_TOKEN='your-actual-token'")
        return
    
    # 测试 1: 站点统计
    test_get_site_stats()
    
    # 测试 2: 列出文章
    articles_result = test_list_articles()
    
    # 测试 3: 获取文章表现（使用第一篇文章）
    if articles_result.get("success") and articles_result["data"]["articles"]:
        first_post_id = articles_result["data"]["articles"][0]["id"]
        test_get_article_metrics(first_post_id)
    else:
        print("\n⚠️ 没有找到文章，跳过 get_article_metrics 测试")
    
    # 测试 4: 文章生命周期（创建→更新→发布→下线）
    print("\n" + "⚠️"*20)
    print("测试 4 将创建一篇测试文章，是否继续？")
    print("⚠️"*20)
    
    user_input = input("输入 'y' 继续，其他键跳过: ").strip().lower()
    if user_input == 'y':
        test_create_and_manage_article()
    else:
        print("跳过文章创建测试")
    
    # 测试 5: 搜索
    test_search_articles()
    
    print("\n" + "="*60)
    print("🎉 测试完成!")
    print("="*60)


if __name__ == "__main__":
    main()
