"""
GEO Chatbot - CMS Tools (WordPress)
内容管理系统工具集

使用 geo_agent/tools/cms_tools.py 作为后端实现
"""

import sys
import os
import importlib.util
from typing import List, Dict, Any, Optional
from pathlib import Path

from tools.base import (
    BaseTool, ToolDefinition, ToolParameter, ToolCategory,
    register_tool, registry
)

# 从 geo_agent 导入 CMS 工具函数（使用 importlib 避免命名冲突）
_cms_tools_path = Path(__file__).resolve().parent.parent.parent.parent / "geo_agent" / "tools" / "cms_tools.py"
_spec = importlib.util.spec_from_file_location("geo_agent_cms_tools", _cms_tools_path)
_cms_tools = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_cms_tools)

_create_article = _cms_tools.create_article
_update_article = _cms_tools.update_article
_publish_article = _cms_tools.publish_article
_unpublish_article = _cms_tools.unpublish_article
_get_article_metrics = _cms_tools.get_article_metrics
_list_articles_by_topic = _cms_tools.list_articles_by_topic
_get_site_stats = _cms_tools.get_site_stats


# ============== CMS Tools ==============

@register_tool
class CreateArticleTool(BaseTool):
    """创建文章工具"""
    
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="create_article",
            description="在 WordPress 中创建新文章。默认保存为草稿，可选择直接发布。",
            category=ToolCategory.CMS,
            parameters=[
                ToolParameter("title", "string", "文章标题", required=True),
                ToolParameter("content", "string", "文章内容 (HTML 格式)", required=True),
                ToolParameter("excerpt", "string", "文章摘要（可选，用于 SEO 和列表展示）"),
                ToolParameter("status", "string", "状态: draft/publish/private", 
                            default="draft", enum=["draft", "publish", "private"]),
                ToolParameter("categories", "array", "分类列表（如 ['技术', 'AI']）"),
                ToolParameter("tags", "array", "标签列表（如 ['Python', '教程']）"),
                ToolParameter("slug", "string", "URL 别名（可选，如 'my-first-post'）"),
                ToolParameter("featured_image", "string", "特色图片 URL（可选）"),
            ]
        )
    
    def execute(self, **kwargs) -> Dict[str, Any]:
        return _create_article(
            title=kwargs.get("title"),
            content=kwargs.get("content"),
            excerpt=kwargs.get("excerpt"),
            categories=kwargs.get("categories"),
            tags=kwargs.get("tags"),
            status=kwargs.get("status", "draft"),
            slug=kwargs.get("slug"),
            featured_image=kwargs.get("featured_image")
        )


@register_tool
class UpdateArticleTool(BaseTool):
    """更新文章工具"""
    
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="update_article",
            description="更新已有文章的内容、标题、分类等。",
            category=ToolCategory.CMS,
            parameters=[
                ToolParameter("post_id", "integer", "文章 ID", required=True),
                ToolParameter("title", "string", "新标题"),
                ToolParameter("content", "string", "新内容 (HTML)"),
                ToolParameter("excerpt", "string", "新摘要"),
                ToolParameter("categories", "array", "新分类列表（会覆盖原有分类）"),
                ToolParameter("tags", "array", "新标签列表（会覆盖原有标签）"),
                ToolParameter("slug", "string", "新 URL 别名"),
            ]
        )
    
    def execute(self, **kwargs) -> Dict[str, Any]:
        return _update_article(
            post_id=kwargs.get("post_id"),
            title=kwargs.get("title"),
            content=kwargs.get("content"),
            excerpt=kwargs.get("excerpt"),
            categories=kwargs.get("categories"),
            tags=kwargs.get("tags"),
            slug=kwargs.get("slug")
        )


@register_tool
class PublishArticleTool(BaseTool):
    """发布文章工具"""
    
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="publish_article",
            description="将草稿文章发布上线。支持定时发布。",
            category=ToolCategory.CMS,
            parameters=[
                ToolParameter("post_id", "integer", "文章 ID", required=True),
                ToolParameter("schedule_time", "string", "定时发布时间（ISO 8601 格式，如 '2024-12-25T10:00:00'）"),
            ]
        )
    
    def execute(self, **kwargs) -> Dict[str, Any]:
        return _publish_article(
            post_id=kwargs.get("post_id"),
            schedule_time=kwargs.get("schedule_time")
        )


@register_tool
class UnpublishArticleTool(BaseTool):
    """下线文章工具"""
    
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="unpublish_article",
            description="将已发布的文章下线（转为草稿或私密）。",
            category=ToolCategory.CMS,
            parameters=[
                ToolParameter("post_id", "integer", "文章 ID", required=True),
                ToolParameter("target_status", "string", "目标状态: draft/private/trash",
                            default="draft", enum=["draft", "private", "trash"]),
            ]
        )
    
    def execute(self, **kwargs) -> Dict[str, Any]:
        return _unpublish_article(
            post_id=kwargs.get("post_id"),
            target_status=kwargs.get("target_status", "draft")
        )


@register_tool
class ListArticlesTool(BaseTool):
    """列出文章工具（资产盘点）"""
    
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="list_articles",
            description="资产盘点 - 按主题/分类/标签列出文章。支持多种筛选条件，返回文章列表及基础指标（浏览量、点赞、评论）。",
            category=ToolCategory.CMS,
            parameters=[
                ToolParameter("status", "string", "状态筛选: publish/draft/private/any",
                            default="any", enum=["publish", "draft", "private", "any"]),
                ToolParameter("category", "string", "按分类筛选（如 '技术'）"),
                ToolParameter("tag", "string", "按标签筛选（如 'Python'）"),
                ToolParameter("search", "string", "搜索关键词（在标题和内容中搜索）"),
                ToolParameter("order_by", "string", "排序字段: date/modified/title/comment_count/views",
                            default="date", enum=["date", "modified", "title", "comment_count", "views"]),
                ToolParameter("order", "string", "排序方向: DESC/ASC",
                            default="DESC", enum=["DESC", "ASC"]),
                ToolParameter("number", "integer", "返回数量（默认 20，最多 100）", default=20),
                ToolParameter("page", "integer", "页码（从 1 开始，用于分页）", default=1),
                ToolParameter("include_views", "boolean", "是否包含浏览量数据", default=True),
            ]
        )
    
    def execute(self, **kwargs) -> Dict[str, Any]:
        return _list_articles_by_topic(
            category=kwargs.get("category"),
            tag=kwargs.get("tag"),
            status=kwargs.get("status", "any"),
            search=kwargs.get("search"),
            order_by=kwargs.get("order_by", "date"),
            order=kwargs.get("order", "DESC"),
            number=kwargs.get("number", 20),
            page=kwargs.get("page", 1),
            include_views=kwargs.get("include_views", True)
        )


@register_tool
class GetArticleMetricsTool(BaseTool):
    """获取文章指标工具"""
    
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="get_article_metrics",
            description="获取文章的表现指标，包括浏览量、访客数、点赞数、评论数等。可查看历史趋势。",
            category=ToolCategory.CMS,
            parameters=[
                ToolParameter("post_id", "integer", "文章 ID", required=True),
                ToolParameter("days", "integer", "查看最近 N 天的数据（默认 30 天，最多 365 天）", default=30),
                ToolParameter("include_daily_breakdown", "boolean", "是否包含每日明细数据", default=False),
            ]
        )
    
    def execute(self, **kwargs) -> Dict[str, Any]:
        return _get_article_metrics(
            post_id=kwargs.get("post_id"),
            days=kwargs.get("days", 30),
            include_daily_breakdown=kwargs.get("include_daily_breakdown", False)
        )


@register_tool
class GetSiteStatsTool(BaseTool):
    """获取站点统计工具"""
    
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="get_site_stats",
            description="获取站点整体统计数据，包括今日浏览量、访客数、热门文章排行等。",
            category=ToolCategory.CMS,
            parameters=[
                ToolParameter("days", "integer", "统计天数（默认 7 天）", default=7),
            ]
        )
    
    def execute(self, **kwargs) -> Dict[str, Any]:
        return _get_site_stats(
            days=kwargs.get("days", 7)
        )
