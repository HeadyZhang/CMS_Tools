# CMS Tools for GEO Agent

WordPress.com 内容管理系统工具集，适用于 GEO (Generative Engine Optimization) Agent 的自动化内容发布。

## 功能列表

| 工具 | 功能 | 说明 |
|------|------|------|
| `create_article` | 创建文章 | 支持标题、内容、分类、标签，默认保存为草稿 |
| `update_article` | 更新文章 | 更新已有文章的标题、内容、分类等 |
| `publish_article` | 发布文章 | 将草稿发布上线，支持定时发布 |
| `unpublish_article` | 下线文章 | 将文章转为草稿/私密/回收站 |
| `list_articles` | 列出文章 | 按分类/标签/状态筛选，包含浏览量数据 |
| `get_article_metrics` | 获取指标 | 浏览量、点赞、评论等表现数据 |
| `get_site_stats` | 站点统计 | 整体流量、热门文章排行 |

## 文件结构

```
CMS_Tools/
├── cms_tools.py              # 核心工具实现
├── wordpress_tool.py         # WordPress API 封装
├── test_cms_tools.py         # 功能测试
├── geo_chatbot_adapter/      # GEO Chatbot 适配层
│   ├── __init__.py
│   └── wordpress.py          # Tool 注册封装
├── requirements.txt
└── README.md
```

## 安装

```bash
pip install -r requirements.txt
```

## 配置

设置以下环境变量：

```bash
# WordPress.com OAuth Token
export WP_ACCESS_TOKEN="your-access-token"

# WordPress Site ID
export WP_SITE_ID="your-site-id"
```

### 获取 Access Token

```bash
curl -X POST https://public-api.wordpress.com/oauth2/token \
  -d "client_id=YOUR_CLIENT_ID" \
  -d "client_secret=YOUR_CLIENT_SECRET" \
  -d "grant_type=password" \
  -d "username=YOUR_USERNAME" \
  -d "password=YOUR_PASSWORD"
```

## 使用示例

### 直接调用

```python
from cms_tools import create_article, publish_article, list_articles

# 创建草稿
result = create_article(
    title="我的第一篇文章",
    content="<h2>Hello World</h2><p>这是文章内容。</p>",
    categories=["技术"],
    tags=["Python", "教程"]
)

if result["success"]:
    post_id = result["data"]["post_id"]
    print(f"文章已创建: {post_id}")
    
    # 发布文章
    publish_article(post_id)

# 列出所有文章
articles = list_articles(status="publish", number=10)
```

### 通过 GEO Chatbot 调用

```python
from tools import execute_tool

# 创建并发布文章
result = execute_tool('create_article', {
    'title': 'GEO优化指南',
    'content': '<p>文章内容...</p>',
    'status': 'publish'
})
```

## API 参考

### create_article

```python
create_article(
    title: str,              # 文章标题 (必填)
    content: str,            # 文章内容 HTML (必填)
    excerpt: str = None,     # 摘要
    categories: List = None, # 分类列表
    tags: List = None,       # 标签列表
    status: str = "draft",   # 状态: draft/publish/private
    slug: str = None,        # URL 别名
    featured_image: str = None  # 特色图片 URL
) -> dict
```

### publish_article

```python
publish_article(
    post_id: int,            # 文章 ID (必填)
    schedule_time: str = None  # 定时发布 (ISO 8601 格式)
) -> dict
```

### list_articles

```python
list_articles(
    category: str = None,    # 按分类筛选
    tag: str = None,         # 按标签筛选
    status: str = "any",     # 状态: publish/draft/private/any
    search: str = None,      # 搜索关键词
    order_by: str = "date",  # 排序: date/modified/title/views
    order: str = "DESC",     # 方向: DESC/ASC
    number: int = 20,        # 返回数量 (最多100)
    include_views: bool = True  # 包含浏览量
) -> dict
```

## 测试

```bash
# 运行功能测试
python test_cms_tools.py
```

## 许可证

MIT License

## 作者

GEO Agent Team
