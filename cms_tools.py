"""
CMS Tools - 内容管理系统工具集
适用于 GEO Agent 的 WordPress.com 内容管理工具

工具列表：
- create_article      新建内容（草稿）
- update_article      更新已有内容
- publish_article     上线（发布）
- unpublish_article   下线（转为草稿）
- get_article_metrics 获取表现（浏览量、点赞等）
- list_articles_by_topic 资产盘点（按主题/分类列出）
"""

import requests
import json
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import sys
import os

# 配置
WP_ACCESS_TOKEN = os.getenv("WP_ACCESS_TOKEN", "your-wordpress-access-token")
WP_SITE_ID = os.getenv("WP_SITE_ID", "251193948")
WP_API_BASE = "https://public-api.wordpress.com/rest/v1.1"


# ============================================================
# Tool Schemas (OpenAI Function Calling 格式)
# ============================================================

CREATE_ARTICLE_TOOL = {
    "type": "function",
    "function": {
        "name": "create_article",
        "description": "新建文章内容。默认保存为草稿状态，可选择直接发布。返回文章ID和编辑链接。",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "文章标题"
                },
                "content": {
                    "type": "string",
                    "description": "文章内容，支持 HTML 格式（推荐使用 <h2>, <p>, <ul> 等标签）"
                },
                "excerpt": {
                    "type": "string",
                    "description": "文章摘要（可选，用于 SEO 和列表展示）"
                },
                "categories": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "分类列表（如 ['技术', 'AI']）"
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "标签列表（如 ['Python', '教程']）"
                },
                "status": {
                    "type": "string",
                    "enum": ["draft", "publish", "private"],
                    "description": "初始状态：draft=草稿（默认），publish=直接发布，private=私密",
                    "default": "draft"
                },
                "slug": {
                    "type": "string",
                    "description": "URL 别名（可选，如 'my-first-post'）"
                },
                "featured_image": {
                    "type": "string",
                    "description": "特色图片 URL（可选）"
                }
            },
            "required": ["title", "content"]
        }
    }
}

UPDATE_ARTICLE_TOOL = {
    "type": "function",
    "function": {
        "name": "update_article",
        "description": "更新已有文章的内容。可以更新标题、内容、分类、标签等任意字段。",
        "parameters": {
            "type": "object",
            "properties": {
                "post_id": {
                    "type": "integer",
                    "description": "要更新的文章 ID"
                },
                "title": {
                    "type": "string",
                    "description": "新标题（可选）"
                },
                "content": {
                    "type": "string",
                    "description": "新内容（可选）"
                },
                "excerpt": {
                    "type": "string",
                    "description": "新摘要（可选）"
                },
                "categories": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "新分类列表（可选，会覆盖原有分类）"
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "新标签列表（可选，会覆盖原有标签）"
                },
                "slug": {
                    "type": "string",
                    "description": "新 URL 别名（可选）"
                }
            },
            "required": ["post_id"]
        }
    }
}

PUBLISH_ARTICLE_TOOL = {
    "type": "function",
    "function": {
        "name": "publish_article",
        "description": "将文章上线（发布）。可以将草稿或私密文章变为公开发布状态。支持定时发布。",
        "parameters": {
            "type": "object",
            "properties": {
                "post_id": {
                    "type": "integer",
                    "description": "要发布的文章 ID"
                },
                "schedule_time": {
                    "type": "string",
                    "description": "定时发布时间（可选，ISO 8601 格式，如 '2024-12-25T10:00:00'）。不填则立即发布。"
                }
            },
            "required": ["post_id"]
        }
    }
}

UNPUBLISH_ARTICLE_TOOL = {
    "type": "function",
    "function": {
        "name": "unpublish_article",
        "description": "将文章下线。可以将已发布的文章转为草稿或私密状态。",
        "parameters": {
            "type": "object",
            "properties": {
                "post_id": {
                    "type": "integer",
                    "description": "要下线的文章 ID"
                },
                "target_status": {
                    "type": "string",
                    "enum": ["draft", "private", "trash"],
                    "description": "目标状态：draft=转为草稿（默认），private=转为私密，trash=移至回收站",
                    "default": "draft"
                }
            },
            "required": ["post_id"]
        }
    }
}

GET_ARTICLE_METRICS_TOOL = {
    "type": "function",
    "function": {
        "name": "get_article_metrics",
        "description": "获取文章的表现指标，包括浏览量、访客数、点赞数、评论数等。可查看历史趋势。",
        "parameters": {
            "type": "object",
            "properties": {
                "post_id": {
                    "type": "integer",
                    "description": "文章 ID"
                },
                "days": {
                    "type": "integer",
                    "description": "查看最近 N 天的数据（默认 30 天，最多 365 天）",
                    "default": 30
                },
                "include_daily_breakdown": {
                    "type": "boolean",
                    "description": "是否包含每日明细数据",
                    "default": False
                }
            },
            "required": ["post_id"]
        }
    }
}

LIST_ARTICLES_BY_TOPIC_TOOL = {
    "type": "function",
    "function": {
        "name": "list_articles_by_topic",
        "description": "资产盘点 - 按主题/分类/标签列出文章。支持多种筛选条件，返回文章列表及基础指标（浏览量、点赞、评论）。",
        "parameters": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "按分类筛选（如 '技术'）"
                },
                "tag": {
                    "type": "string",
                    "description": "按标签筛选（如 'Python'）"
                },
                "status": {
                    "type": "string",
                    "enum": ["publish", "draft", "private", "any"],
                    "description": "按状态筛选：publish=已发布，draft=草稿，private=私密，any=全部",
                    "default": "any"
                },
                "search": {
                    "type": "string",
                    "description": "搜索关键词（在标题和内容中搜索）"
                },
                "order_by": {
                    "type": "string",
                    "enum": ["date", "modified", "title", "comment_count", "views"],
                    "description": "排序字段：date=发布日期，modified=修改日期，title=标题，comment_count=评论数，views=浏览量",
                    "default": "date"
                },
                "order": {
                    "type": "string",
                    "enum": ["DESC", "ASC"],
                    "description": "排序方向：DESC=降序（默认），ASC=升序",
                    "default": "DESC"
                },
                "number": {
                    "type": "integer",
                    "description": "返回数量（默认 20，最多 100）",
                    "default": 20
                },
                "page": {
                    "type": "integer",
                    "description": "页码（从 1 开始，用于分页）",
                    "default": 1
                },
                "include_views": {
                    "type": "boolean",
                    "description": "是否包含浏览量数据（默认 true，会额外调用 stats API）",
                    "default": True
                }
            }
        }
    }
}


# ============================================================
# Tool 实现函数
# ============================================================

def _make_request(method: str, endpoint: str, data: dict = None, params: dict = None) -> dict:
    """
    统一的 API 请求函数
    """
    url = f"{WP_API_BASE}{endpoint}"
    headers = {
        "Authorization": f"Bearer {WP_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    
    try:
        if method.upper() == "GET":
            response = requests.get(url, headers=headers, params=params, timeout=30)
        elif method.upper() == "POST":
            response = requests.post(url, headers=headers, json=data, timeout=30)
        elif method.upper() == "DELETE":
            response = requests.delete(url, headers=headers, timeout=30)
        else:
            return {"success": False, "error": f"Unsupported method: {method}"}
        
        result = response.json()
        
        if response.status_code in [200, 201]:
            return {"success": True, "data": result}
        else:
            error_msg = result.get("message", result.get("error", str(result)))
            return {"success": False, "error": error_msg, "status_code": response.status_code}
            
    except requests.exceptions.Timeout:
        return {"success": False, "error": "请求超时"}
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": f"网络错误: {str(e)}"}
    except json.JSONDecodeError:
        return {"success": False, "error": "响应解析失败"}


def create_article(
    title: str,
    content: str,
    excerpt: str = None,
    categories: List[str] = None,
    tags: List[str] = None,
    status: str = "draft",
    slug: str = None,
    featured_image: str = None
) -> dict:
    """
    新建文章
    
    Returns:
        {
            "success": True,
            "data": {
                "post_id": 123,
                "title": "...",
                "status": "draft",
                "url": "...",
                "edit_url": "...",
                "created_at": "..."
            }
        }
    """
    payload = {
        "title": title,
        "content": content,
        "status": status
    }
    
    if excerpt:
        payload["excerpt"] = excerpt
    if categories:
        payload["categories"] = ",".join(categories)
    if tags:
        payload["tags"] = ",".join(tags)
    if slug:
        payload["slug"] = slug
    if featured_image:
        payload["featured_image"] = featured_image
    
    result = _make_request("POST", f"/sites/{WP_SITE_ID}/posts/new", data=payload)
    
    if result["success"]:
        post = result["data"]
        return {
            "success": True,
            "data": {
                "post_id": post["ID"],
                "title": post["title"],
                "status": post["status"],
                "url": post["URL"],
                "short_url": post.get("short_URL", ""),
                "edit_url": f"https://wordpress.com/post/{WP_SITE_ID}/{post['ID']}",
                "created_at": post["date"],
                "author": post.get("author", {}).get("name", ""),
                "categories": list(post.get("categories", {}).keys()),
                "tags": list(post.get("tags", {}).keys())
            }
        }
    
    return result


def update_article(
    post_id: int,
    title: str = None,
    content: str = None,
    excerpt: str = None,
    categories: List[str] = None,
    tags: List[str] = None,
    slug: str = None
) -> dict:
    """
    更新文章
    """
    payload = {}
    
    if title is not None:
        payload["title"] = title
    if content is not None:
        payload["content"] = content
    if excerpt is not None:
        payload["excerpt"] = excerpt
    if categories is not None:
        payload["categories"] = ",".join(categories)
    if tags is not None:
        payload["tags"] = ",".join(tags)
    if slug is not None:
        payload["slug"] = slug
    
    if not payload:
        return {"success": False, "error": "没有提供要更新的字段"}
    
    result = _make_request("POST", f"/sites/{WP_SITE_ID}/posts/{post_id}", data=payload)
    
    if result["success"]:
        post = result["data"]
        return {
            "success": True,
            "data": {
                "post_id": post["ID"],
                "title": post["title"],
                "status": post["status"],
                "url": post["URL"],
                "modified_at": post["modified"],
                "message": "文章更新成功"
            }
        }
    
    return result


def publish_article(
    post_id: int,
    schedule_time: str = None
) -> dict:
    """
    发布文章（上线）
    
    Args:
        post_id: 文章 ID
        schedule_time: 定时发布时间（ISO 8601 格式）
    """
    payload = {}
    
    if schedule_time:
        # 定时发布
        payload["status"] = "future"
        payload["date"] = schedule_time
        action = "scheduled"
    else:
        # 立即发布
        payload["status"] = "publish"
        action = "published"
    
    result = _make_request("POST", f"/sites/{WP_SITE_ID}/posts/{post_id}", data=payload)
    
    if result["success"]:
        post = result["data"]
        return {
            "success": True,
            "data": {
                "post_id": post["ID"],
                "title": post["title"],
                "status": post["status"],
                "url": post["URL"],
                "short_url": post.get("short_URL", ""),
                "published_at": post["date"],
                "action": action,
                "message": f"文章已{'定时发布' if schedule_time else '发布'}"
            }
        }
    
    return result


def unpublish_article(
    post_id: int,
    target_status: str = "draft"
) -> dict:
    """
    下线文章
    
    Args:
        post_id: 文章 ID
        target_status: 目标状态 (draft/private/trash)
    """
    payload = {"status": target_status}
    
    result = _make_request("POST", f"/sites/{WP_SITE_ID}/posts/{post_id}", data=payload)
    
    if result["success"]:
        post = result["data"]
        status_names = {
            "draft": "草稿",
            "private": "私密",
            "trash": "回收站"
        }
        return {
            "success": True,
            "data": {
                "post_id": post["ID"],
                "title": post["title"],
                "previous_status": "publish",
                "current_status": post["status"],
                "message": f"文章已下线，当前状态：{status_names.get(target_status, target_status)}"
            }
        }
    
    return result


def get_article_metrics(
    post_id: int,
    days: int = 30,
    include_daily_breakdown: bool = False
) -> dict:
    """
    获取文章表现指标
    
    使用多个 API 端点综合获取数据：
    1. /posts/{id} - 文章基本信息（likes, comments）
    2. /stats/top-posts - 热门文章浏览量
    3. /stats/summary - 站点汇总统计
    """
    # 限制天数范围
    days = min(max(1, days), 365)
    
    # 1. 获取文章基本信息
    post_result = _make_request("GET", f"/sites/{WP_SITE_ID}/posts/{post_id}")
    
    if not post_result["success"]:
        return post_result
    
    post = post_result["data"]
    
    # 2. 尝试从 top-posts 获取浏览量
    total_views = 0
    views_source = "unavailable"
    daily_views = []
    
    # 方法 A: 从 top-posts 端点查找
    top_posts_params = {
        "num": days,
        "max": 100  # 获取更多文章以增加找到目标文章的概率
    }
    
    top_posts_result = _make_request(
        "GET",
        f"/sites/{WP_SITE_ID}/stats/top-posts",
        params=top_posts_params
    )
    
    if top_posts_result["success"]:
        # 在 top-posts 结果中查找目标文章
        top_posts_data = top_posts_result["data"]
        
        # 从 summary.postviews 中查找
        if "summary" in top_posts_data and "postviews" in top_posts_data["summary"]:
            for p in top_posts_data["summary"]["postviews"]:
                if isinstance(p, dict) and p.get("id") == post_id:
                    total_views = p.get("views", 0)
                    views_source = "top-posts-summary"
                    break
        
        # 从 days 中累加（days 是一个 dict，key 是日期字符串）
        if "days" in top_posts_data and isinstance(top_posts_data["days"], dict):
            for day_date, day_info in top_posts_data["days"].items():
                if isinstance(day_info, dict) and "postviews" in day_info:
                    for p in day_info["postviews"]:
                        if isinstance(p, dict) and p.get("id") == post_id:
                            views = p.get("views", 0)
                            total_views += views
                            if include_daily_breakdown:
                                daily_views.append({"date": day_date, "views": views})
            
            if total_views > 0:
                views_source = "top-posts"
    
    # 方法 B: 如果 top-posts 没找到，尝试 stats/post/{id}（某些站点可用）
    if total_views == 0:
        post_stats_result = _make_request(
            "GET",
            f"/sites/{WP_SITE_ID}/stats/post/{post_id}"
        )
        
        if post_stats_result["success"]:
            stats_data = post_stats_result["data"]
            total_views = stats_data.get("views", 0)
            views_source = "post-stats"
            
            # 获取每日数据
            if include_daily_breakdown and "data" in stats_data:
                for date_str, view_count in stats_data["data"].items():
                    daily_views.append({"date": date_str, "views": view_count})
    
    # 3. 获取站点整体统计作为参考
    site_stats = {}
    summary_result = _make_request("GET", f"/sites/{WP_SITE_ID}/stats/summary")
    if summary_result["success"]:
        site_stats = {
            "site_views_today": summary_result["data"].get("views", 0),
            "site_visitors_today": summary_result["data"].get("visitors", 0),
            "site_followers": summary_result["data"].get("followers", 0)
        }
    
    # 4. 构建返回数据
    metrics = {
        "success": True,
        "data": {
            "post_id": post["ID"],
            "title": post["title"],
            "status": post["status"],
            "url": post["URL"],
            
            # 基础指标
            "metrics": {
                "views": total_views,
                "likes": post.get("like_count", 0),
                "comments": post.get("comment_count", 0),
                "word_count": post.get("word_count", 0),
                "views_source": views_source
            },
            
            # 时间信息
            "dates": {
                "published": post.get("date"),
                "modified": post.get("modified"),
                "stats_period": f"最近 {days} 天"
            },
            
            # 分类和标签
            "taxonomy": {
                "categories": list(post.get("categories", {}).keys()),
                "tags": list(post.get("tags", {}).keys())
            },
            
            # 站点整体统计（参考）
            "site_context": site_stats
        }
    }
    
    # 添加每日明细
    if include_daily_breakdown and daily_views:
        metrics["data"]["daily_breakdown"] = sorted(daily_views, key=lambda x: x["date"], reverse=True)
    
    # 计算平均值
    if days > 0 and total_views > 0:
        metrics["data"]["metrics"]["avg_daily_views"] = round(total_views / days, 2)
    
    # 如果无法获取浏览量，添加说明
    if total_views == 0:
        metrics["data"]["metrics"]["note"] = "浏览量数据暂不可用（文章可能太新或尚无访问）"
    
    return metrics


def list_articles_by_topic(
    category: str = None,
    tag: str = None,
    status: str = "any",
    search: str = None,
    order_by: str = "date",
    order: str = "DESC",
    number: int = 20,
    page: int = 1,
    include_views: bool = True
) -> dict:
    """
    资产盘点 - 按条件列出文章
    
    Args:
        include_views: 是否包含浏览量数据（从 top-posts 获取）
    """
    # 限制返回数量
    number = min(max(1, number), 100)
    
    # 构建查询参数
    params = {
        "number": number,
        "page": page,
        "order_by": order_by,
        "order": order
    }
    
    if status and status != "any":
        params["status"] = status
    else:
        params["status"] = "any"
    
    if category:
        params["category"] = category
    if tag:
        params["tag"] = tag
    if search:
        params["search"] = search
    
    result = _make_request("GET", f"/sites/{WP_SITE_ID}/posts/", params=params)
    
    if not result["success"]:
        return result
    
    posts_data = result["data"]
    posts = posts_data.get("posts", [])
    
    # 获取浏览量数据
    views_map = {}
    if include_views:
        top_posts_result = _make_request(
            "GET",
            f"/sites/{WP_SITE_ID}/stats/top-posts",
            params={"num": 30, "max": 100}
        )
        
        if top_posts_result["success"]:
            top_data = top_posts_result["data"]
            # 从 summary 中提取
            if "summary" in top_data and "postviews" in top_data["summary"]:
                for p in top_data["summary"]["postviews"]:
                    views_map[p.get("id")] = p.get("views", 0)
            # 从 days 中累加
            if "days" in top_data and isinstance(top_data["days"], dict):
                for date_str, day_info in top_data["days"].items():
                    if isinstance(day_info, dict) and "postviews" in day_info:
                        for p in day_info["postviews"]:
                            if isinstance(p, dict):
                                    pid = p.get("id")
                                    views = p.get("views", 0)
                                    if pid:
                                        views_map[pid] = views_map.get(pid, 0) + views
                
    # 处理文章列表
    articles = []
    status_counts = {"publish": 0, "draft": 0, "private": 0, "future": 0}
    total_views = 0
    total_likes = 0
    total_comments = 0
    
    for post in posts:
        post_status = post.get("status", "unknown")
        if post_status in status_counts:
            status_counts[post_status] += 1
        
        like_count = post.get("like_count", 0)
        comment_count = post.get("comment_count", 0)
        post_views = views_map.get(post["ID"], 0)
        
        total_views += post_views
        total_likes += like_count
        total_comments += comment_count
        
        articles.append({
            "id": post["ID"],
            "title": post["title"],
            "status": post_status,
            "url": post["URL"],
            "date": post.get("date"),
            "modified": post.get("modified"),
            "excerpt": post.get("excerpt", "")[:150] + "..." if post.get("excerpt") else "",
            "metrics": {
                "views": post_views,
                "likes": like_count,
                "comments": comment_count,
                "word_count": post.get("word_count", 0)
            },
            "categories": list(post.get("categories", {}).keys()),
            "tags": list(post.get("tags", {}).keys())
        })
    
    # 按浏览量排序（如果请求了浏览量数据）
    if include_views and order_by == "views":
        articles = sorted(articles, key=lambda x: x["metrics"]["views"], reverse=(order == "DESC"))
    
    # 构建汇总信息
    return {
        "success": True,
        "data": {
            # 筛选条件
            "filters": {
                "category": category,
                "tag": tag,
                "status": status,
                "search": search
            },
            
            # 分页信息
            "pagination": {
                "total": posts_data.get("found", len(articles)),
                "page": page,
                "per_page": number,
                "total_pages": (posts_data.get("found", 0) + number - 1) // number if number > 0 else 0
            },
            
            # 汇总统计
            "summary": {
                "total_articles": len(articles),
                "status_breakdown": status_counts,
                "total_views": total_views,
                "total_likes": total_likes,
                "total_comments": total_comments
            },
            
            # 文章列表
            "articles": articles
        }
    }


def get_site_stats(days: int = 7) -> dict:
    """
    获取站点整体统计数据
    
    Args:
        days: 统计天数
    
    Returns:
        站点浏览量、访客数、热门文章等数据
    """
    days = min(max(1, days), 365)
    
    # 1. 获取站点汇总
    summary_result = _make_request("GET", f"/sites/{WP_SITE_ID}/stats/summary")
    
    # 2. 获取热门文章
    top_posts_result = _make_request(
        "GET",
        f"/sites/{WP_SITE_ID}/stats/top-posts",
        params={"num": days, "max": 10}
    )
    
    # 3. 获取站点基本信息
    site_result = _make_request("GET", f"/sites/{WP_SITE_ID}")
    
    # 构建返回数据
    data = {
        "period": f"最近 {days} 天",
        "today": {},
        "top_posts": [],
        "site_info": {}
    }
    
    if summary_result["success"]:
        s = summary_result["data"]
        data["today"] = {
            "views": s.get("views", 0),
            "visitors": s.get("visitors", 0),
            "likes": s.get("likes", 0),
            "comments": s.get("comments", 0),
            "followers": s.get("followers", 0)
        }
    
    if top_posts_result["success"]:
        top_data = top_posts_result["data"]
        if "summary" in top_data and "postviews" in top_data["summary"]:
            for p in top_data["summary"]["postviews"][:10]:
                data["top_posts"].append({
                    "id": p.get("id"),
                    "title": p.get("title", ""),
                    "views": p.get("views", 0),
                    "url": p.get("href", "")
                })
    
    if site_result["success"]:
        s = site_result["data"]
        data["site_info"] = {
            "name": s.get("name", ""),
            "description": s.get("description", ""),
            "url": s.get("URL", ""),
            "post_count": s.get("post_count", 0)
        }
    
    return {
        "success": True,
        "data": data
    }


# 添加 get_site_stats 的 Tool Schema
GET_SITE_STATS_TOOL = {
    "type": "function",
    "function": {
        "name": "get_site_stats",
        "description": "获取站点整体统计数据，包括今日浏览量、访客数、热门文章排行等。",
        "parameters": {
            "type": "object",
            "properties": {
                "days": {
                    "type": "integer",
                    "description": "统计天数（默认 7 天）",
                    "default": 7
                }
            }
        }
    }
}


# ============================================================
# Tool 注册表
# ============================================================

CMS_TOOLS_SCHEMA = [
    CREATE_ARTICLE_TOOL,
    UPDATE_ARTICLE_TOOL,
    PUBLISH_ARTICLE_TOOL,
    UNPUBLISH_ARTICLE_TOOL,
    GET_ARTICLE_METRICS_TOOL,
    LIST_ARTICLES_BY_TOPIC_TOOL,
    GET_SITE_STATS_TOOL,
]

CMS_TOOLS_FUNCTIONS = {
    "create_article": create_article,
    "update_article": update_article,
    "publish_article": publish_article,
    "unpublish_article": unpublish_article,
    "get_article_metrics": get_article_metrics,
    "list_articles_by_topic": list_articles_by_topic,
    "get_site_stats": get_site_stats,
}


# ============================================================
# 便捷函数
# ============================================================

def execute_cms_tool(tool_name: str, arguments: dict) -> dict:
    """
    执行 CMS Tool
    """
    if tool_name not in CMS_TOOLS_FUNCTIONS:
        return {"success": False, "error": f"Unknown tool: {tool_name}"}
    
    try:
        func = CMS_TOOLS_FUNCTIONS[tool_name]
        return func(**arguments)
    except TypeError as e:
        return {"success": False, "error": f"参数错误: {str(e)}"}
    except Exception as e:
        return {"success": False, "error": f"执行错误: {str(e)}"}


def get_cms_tool_names() -> List[str]:
    """获取所有 CMS Tool 名称"""
    return list(CMS_TOOLS_FUNCTIONS.keys())


# ============================================================
# 测试
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("CMS Tools 测试")
    print("=" * 60)
    
    # 测试站点统计
    print("\n📊 测试 get_site_stats:")
    result = get_site_stats(days=7)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    # 测试列出文章
    print("\n📋 测试 list_articles_by_topic:")
    result = list_articles_by_topic(number=5, status="any", include_views=True)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    # 如果有文章，测试获取指标
    if result["success"] and result["data"]["articles"]:
        first_post_id = result["data"]["articles"][0]["id"]
        print(f"\n📈 测试 get_article_metrics (post_id={first_post_id}):")
        metrics = get_article_metrics(first_post_id, days=7)
        print(json.dumps(metrics, indent=2, ensure_ascii=False))
