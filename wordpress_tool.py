"""
WordPress 发布 Tool
封装为 OpenAI Function Calling 格式
"""

import requests
import json
from typing import Optional
import sys
sys.path.append('..')
from config import WP_ACCESS_TOKEN, WP_SITE_ID, WP_API_BASE


# ============== Tool Schema (OpenAI Function Calling 格式) ==============
WORDPRESS_PUBLISH_TOOL = {
    "type": "function",
    "function": {
        "name": "wordpress_publish",
        "description": "发布文章到 WordPress.com 博客。可以发布新文章或保存为草稿。支持 HTML 格式内容。",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "文章标题"
                },
                "content": {
                    "type": "string", 
                    "description": "文章内容，支持 HTML 格式（如 <h2>, <p>, <ul> 等标签）"
                },
                "status": {
                    "type": "string",
                    "enum": ["publish", "draft", "private"],
                    "description": "发布状态：publish=立即发布, draft=保存草稿, private=私密文章",
                    "default": "publish"
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "文章标签列表"
                },
                "categories": {
                    "type": "array", 
                    "items": {"type": "string"},
                    "description": "文章分类列表"
                },
                "excerpt": {
                    "type": "string",
                    "description": "文章摘要（可选）"
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

WORDPRESS_GET_POSTS_TOOL = {
    "type": "function", 
    "function": {
        "name": "wordpress_get_posts",
        "description": "获取 WordPress 博客的文章列表，可用于查看已发布的内容",
        "parameters": {
            "type": "object",
            "properties": {
                "number": {
                    "type": "integer",
                    "description": "获取文章数量，默认 10",
                    "default": 10
                },
                "status": {
                    "type": "string",
                    "enum": ["publish", "draft", "private", "any"],
                    "description": "文章状态筛选",
                    "default": "publish"
                },
                "search": {
                    "type": "string",
                    "description": "搜索关键词（可选）"
                }
            }
        }
    }
}

WORDPRESS_UPDATE_POST_TOOL = {
    "type": "function",
    "function": {
        "name": "wordpress_update_post", 
        "description": "更新已存在的 WordPress 文章",
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
                "status": {
                    "type": "string",
                    "enum": ["publish", "draft", "private"],
                    "description": "新状态（可选）"
                }
            },
            "required": ["post_id"]
        }
    }
}

WORDPRESS_DELETE_POST_TOOL = {
    "type": "function",
    "function": {
        "name": "wordpress_delete_post",
        "description": "删除 WordPress 文章",
        "parameters": {
            "type": "object",
            "properties": {
                "post_id": {
                    "type": "integer",
                    "description": "要删除的文章 ID"
                }
            },
            "required": ["post_id"]
        }
    }
}


# ============== Tool 实现函数 ==============

def wordpress_publish(
    title: str,
    content: str,
    status: str = "publish",
    tags: list = None,
    categories: list = None,
    excerpt: str = None,
    featured_image: str = None
) -> dict:
    """
    发布文章到 WordPress.com
    
    Returns:
        dict: {"success": bool, "data": {...} or "error": "..."}
    """
    url = f"{WP_API_BASE}/sites/{WP_SITE_ID}/posts/new"
    
    headers = {
        "Authorization": f"Bearer {WP_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "title": title,
        "content": content,
        "status": status,
    }
    
    if tags:
        payload["tags"] = ",".join(tags)
    if categories:
        payload["categories"] = ",".join(categories)
    if excerpt:
        payload["excerpt"] = excerpt
    if featured_image:
        payload["featured_image"] = featured_image
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        
        if response.status_code in [200, 201]:
            result = response.json()
            return {
                "success": True,
                "data": {
                    "post_id": result["ID"],
                    "title": result["title"],
                    "url": result["URL"],
                    "short_url": result.get("short_URL", ""),
                    "status": result["status"],
                    "date": result["date"],
                    "author": result.get("author", {}).get("name", "")
                }
            }
        else:
            error_data = response.json()
            return {
                "success": False,
                "error": f"{error_data.get('error', 'Unknown')}: {error_data.get('message', response.text)}"
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def wordpress_get_posts(
    number: int = 10,
    status: str = "publish",
    search: str = None
) -> dict:
    """
    获取文章列表
    """
    url = f"{WP_API_BASE}/sites/{WP_SITE_ID}/posts/"
    
    headers = {
        "Authorization": f"Bearer {WP_ACCESS_TOKEN}"
    }
    
    params = {
        "number": number,
        "status": status
    }
    
    if search:
        params["search"] = search
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            posts = []
            for post in result.get("posts", []):
                posts.append({
                    "id": post["ID"],
                    "title": post["title"],
                    "url": post["URL"],
                    "status": post["status"],
                    "date": post["date"],
                    "excerpt": post.get("excerpt", "")[:200]
                })
            return {
                "success": True,
                "data": {
                    "total": result.get("found", len(posts)),
                    "posts": posts
                }
            }
        else:
            return {
                "success": False,
                "error": response.text
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def wordpress_update_post(
    post_id: int,
    title: str = None,
    content: str = None,
    status: str = None
) -> dict:
    """
    更新文章
    """
    url = f"{WP_API_BASE}/sites/{WP_SITE_ID}/posts/{post_id}"
    
    headers = {
        "Authorization": f"Bearer {WP_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    
    payload = {}
    if title:
        payload["title"] = title
    if content:
        payload["content"] = content
    if status:
        payload["status"] = status
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            return {
                "success": True,
                "data": {
                    "post_id": result["ID"],
                    "title": result["title"],
                    "url": result["URL"],
                    "status": result["status"]
                }
            }
        else:
            return {
                "success": False,
                "error": response.text
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def wordpress_delete_post(post_id: int) -> dict:
    """
    删除文章
    """
    url = f"{WP_API_BASE}/sites/{WP_SITE_ID}/posts/{post_id}/delete"
    
    headers = {
        "Authorization": f"Bearer {WP_ACCESS_TOKEN}"
    }
    
    try:
        response = requests.post(url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            return {
                "success": True,
                "data": {"message": f"文章 {post_id} 已删除"}
            }
        else:
            return {
                "success": False,
                "error": response.text
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


# ============== Tool 注册表 ==============

# Schema 列表（传给 OpenAI API）
WORDPRESS_TOOLS_SCHEMA = [
    WORDPRESS_PUBLISH_TOOL,
    WORDPRESS_GET_POSTS_TOOL,
    WORDPRESS_UPDATE_POST_TOOL,
    WORDPRESS_DELETE_POST_TOOL,
]

# 函数映射（用于执行）
WORDPRESS_TOOLS_FUNCTIONS = {
    "wordpress_publish": wordpress_publish,
    "wordpress_get_posts": wordpress_get_posts,
    "wordpress_update_post": wordpress_update_post,
    "wordpress_delete_post": wordpress_delete_post,
}


# ============== 测试 ==============
if __name__ == "__main__":
    # 测试获取文章列表
    print("测试获取文章列表...")
    result = wordpress_get_posts(number=5)
    print(json.dumps(result, indent=2, ensure_ascii=False))
