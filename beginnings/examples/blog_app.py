"""
Blog Application Example - Demonstrates HTML + API endpoints.

This example shows how to build a blog application using the Beginnings framework
with both HTML pages for browsers and API endpoints for programmatic access.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from beginnings import App


# Data models
class BlogPost(BaseModel):
    """Blog post data model."""
    id: int
    title: str
    content: str
    author: str
    created_at: datetime
    published: bool = True


class CreatePostRequest(BaseModel):
    """Request model for creating blog posts."""
    title: str
    content: str
    author: str


# Mock database
BLOG_POSTS: dict[int, BlogPost] = {
    1: BlogPost(
        id=1,
        title="Welcome to Beginnings",
        content="This is our first blog post using the Beginnings framework!",
        author="Admin",
        created_at=datetime(2024, 1, 1, 12, 0, 0)
    ),
    2: BlogPost(
        id=2,
        title="Building Web Apps with Configuration",
        content="Learn how to build web applications using configuration-driven development.",
        author="Developer",
        created_at=datetime(2024, 1, 2, 14, 30, 0)
    ),
}
NEXT_POST_ID = 3


def create_blog_app() -> App:
    """Create and configure the blog application."""
    # Initialize the Beginnings app
    app = App()
    
    # Create HTML router for browser-facing pages
    html_router = app.create_html_router()
    
    # Create API router for programmatic access
    api_router = app.create_api_router(prefix="/api/v1")
    
    # HTML Routes (for browsers)
    @html_router.get("/")
    def blog_home() -> HTMLResponse:
        """Blog home page with list of posts."""
        posts_html = ""
        for post in BLOG_POSTS.values():
            if post.published:
                posts_html += f"""
                    <article class="post-card">
                        <h2><a href="/posts/{post.id}" class="post-title">{post.title}</a></h2>
                        <div class="post-meta">
                            <span class="author">{post.author}</span>
                            <span class="date">{post.created_at.strftime('%B %d, %Y')}</span>
                        </div>
                        <p class="post-excerpt">{post.content[:150]}...</p>
                        <a href="/posts/{post.id}" class="read-more">Read more →</a>
                    </article>
                """
        
        html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Blog Example</title>
            <style>
                * {{
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }}
                
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif;
                    background: #f8f9fa;
                    color: #000000;
                    line-height: 1.6;
                    min-height: 100vh;
                    display: flex;
                    flex-direction: column;
                }}
                
                /* Sticky Navigation */
                .sticky-nav {{
                    position: sticky;
                    top: 0;
                    z-index: 100;
                    padding: 15px 0;
                }}
                
                /* Shared container for consistent alignment */
                .page-container {{
                    width: 100%;
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 0 20px;
                    box-sizing: border-box;
                }}
                
                .nav-container {{
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                }}
                
                .nav-title {{
                    font-size: 1.5rem;
                    font-weight: 900;
                    color: #000000;
                    text-decoration: none;
                    letter-spacing: -0.02em;
                }}
                
                .navigation {{
                    display: flex;
                    gap: 30px;
                    align-items: center;
                }}
                
                .container {{
                    flex: 1;
                    padding-top: 40px;
                }}
                
                .nav-link {{
                    color: #666666;
                    text-decoration: none;
                    font-weight: 600;
                    font-size: 1rem;
                    transition: color 300ms ease;
                }}
                
                .nav-link:hover {{
                    color: #000000;
                }}
                
                .nav-link.active {{
                    color: #000000;
                }}
                
                /* Posts */
                .posts {{
                    display: flex;
                    flex-direction: column;
                    gap: 60px;
                }}
                
                .post-card {{
                    padding-bottom: 60px;
                    border-bottom: 1px solid #e9ecef;
                }}
                
                .post-card:last-child {{
                    border-bottom: none;
                    padding-bottom: 0;
                }}
                
                .post-title {{
                    font-size: clamp(1.5rem, 5vw, 2rem);
                    font-weight: 900;
                    color: #000000;
                    text-decoration: none;
                    line-height: 1.2;
                    margin-bottom: 15px;
                    display: block;
                    transition: color 300ms ease;
                }}
                
                .post-title:hover {{
                    color: #404040;
                }}
                
                .post-meta {{
                    display: flex;
                    gap: 20px;
                    margin-bottom: 20px;
                    font-size: 0.9rem;
                    color: #666666;
                }}
                
                .author {{
                    font-weight: 600;
                }}
                
                .date {{
                    color: #999999;
                }}
                
                .post-excerpt {{
                    font-size: 1.1rem;
                    color: #404040;
                    margin-bottom: 25px;
                    line-height: 1.7;
                }}
                
                .read-more {{
                    color: #000000;
                    text-decoration: none;
                    font-weight: 600;
                    font-size: 0.95rem;
                    display: inline-flex;
                    align-items: center;
                    gap: 5px;
                    transition: all 300ms ease;
                }}
                
                .read-more:hover {{
                    color: #404040;
                    transform: translateX(3px);
                }}
                
                /* Dark mode */
                @media (prefers-color-scheme: dark) {{
                    body {{
                        background: #1a1a1a;
                        color: #ffffff;
                    }}
                    
                    .nav-title {{
                        color: #ffffff;
                    }}
                    
                    .nav-link {{
                        color: #999999;
                    }}
                    
                    .nav-link:hover,
                    .nav-link.active {{
                        color: #ffffff;
                    }}
                    
                    .post-card {{
                        border-bottom-color: #333333;
                    }}
                    
                    .post-title {{
                        color: #ffffff;
                    }}
                    
                    .post-title:hover {{
                        color: #cccccc;
                    }}
                    
                    .post-meta {{
                        color: #999999;
                    }}
                    
                    .date {{
                        color: #666666;
                    }}
                    
                    .post-excerpt {{
                        color: #cccccc;
                    }}
                    
                    .read-more {{
                        color: #ffffff;
                    }}
                    
                    .read-more:hover {{
                        color: #cccccc;
                    }}
                }}
                
                /* Footer */
                .footer {{
                    margin-top: auto;
                    padding: 40px 0;
                    border-top: 1px solid #e9ecef;
                    text-align: left;
                }}
                
                .footer-text {{
                    color: #666666;
                    font-size: 0.9rem;
                    margin-bottom: 15px;
                }}
                
                .docs-link {{
                    color: #000000;
                    text-decoration: none;
                    font-weight: 600;
                    font-size: 0.95rem;
                    transition: color 300ms ease;
                }}
                
                .docs-link:hover {{
                    color: #404040;
                }}
                
                .footer-content {{
                    display: flex;
                    justify-content: space-between;
                    align-items: flex-start;
                    gap: 40px;
                }}
                
                .footer-left {{
                    flex: 1;
                }}
                
                .footer-right {{
                    text-align: right;
                    flex-shrink: 0;
                }}
                
                .copyright {{
                    color: #666666;
                    font-size: 0.85rem;
                    margin-bottom: 15px;
                }}
                
                .license {{
                    color: #666666;
                    font-size: 0.85rem;
                }}
                
                .footer-link {{
                    color: #666666;
                    text-decoration: none;
                    transition: color 300ms ease;
                }}
                
                .footer-link:hover {{
                    color: #000000;
                }}
                
                /* Mobile responsive */
                @media (max-width: 768px) {{
                    .container {{
                        padding: 40px 20px;
                    }}
                    
                    .header {{
                        margin-bottom: 60px;
                    }}
                    
                    .navigation {{
                        gap: 30px;
                        flex-wrap: wrap;
                    }}
                    
                    .posts {{
                        gap: 50px;
                    }}
                    
                    .post-card {{
                        padding-bottom: 50px;
                    }}
                    
                    .footer {{
                        margin-top: 80px;
                        padding-top: 30px;
                    }}
                    
                    .footer-content {{
                        flex-direction: column;
                        gap: 20px;
                        text-align: left;
                    }}
                    
                    .footer-right {{
                        text-align: left;
                    }}
                }}
                
                /* Dark mode */
                @media (prefers-color-scheme: dark) {{
                    body {{
                        background: #1a1a1a;
                        color: #ffffff;
                    }}
                    
                    .nav-title {{
                        color: #ffffff;
                    }}
                    
                    .nav-link {{
                        color: #999999;
                    }}
                    
                    .nav-link:hover,
                    .nav-link.active {{
                        color: #ffffff;
                    }}
                    
                    .post-card {{
                        border-bottom-color: #333333;
                    }}
                    
                    .post-title {{
                        color: #ffffff;
                    }}
                    
                    .post-title:hover {{
                        color: #cccccc;
                    }}
                    
                    .post-meta {{
                        color: #999999;
                    }}
                    
                    .date {{
                        color: #666666;
                    }}
                    
                    .post-excerpt {{
                        color: #cccccc;
                    }}
                    
                    .read-more {{
                        color: #ffffff;
                    }}
                    
                    .read-more:hover {{
                        color: #cccccc;
                    }}
                    
                    .footer {{
                        border-top-color: #333333;
                    }}
                    
                    .footer-text {{
                        color: #999999;
                    }}
                    
                    .docs-link {{
                        color: #ffffff;
                    }}
                    
                    .docs-link:hover {{
                        color: #cccccc;
                    }}
                }}
            </style>
        </head>
        <body>
            <nav class="sticky-nav">
                <div class="page-container nav-container">
                    <a href="/" class="nav-title">Blog Example</a>
                    <div class="navigation">
                        <a href="/" class="nav-link active">Posts</a>
                        <a href="/about" class="nav-link">About</a>
                        <a href="/docs" class="nav-link">API</a>
                    </div>
                </div>
            </nav>
            
            <div class="page-container container">
                <main class="posts">
                    {posts_html}
                </main>
            </div>
            
            <footer class="footer">
                <div class="page-container">
                    <div class="footer-content">
                        <div class="footer-left">
                            <div class="footer-text">Built with the Beginnings framework</div>
                            <a href="https://beginnings.8ly.xyz/docs" class="docs-link" target="_blank">View Documentation</a>
                        </div>
                        <div class="footer-right">
                            <div class="copyright">© 2025 <a href="https://8ly.xyz" class="footer-link" target="_blank">8ly LLC</a></div>
                            <div class="license">Made available under the <a href="https://opensource.org/licenses/MIT" class="footer-link" target="_blank">MIT license</a></div>
                        </div>
                    </div>
                </div>
            </footer>
        </body>
        </html>
        """
        return HTMLResponse(content=html_content)
    
    @html_router.get("/posts/{post_id}")
    def blog_post_page(post_id: int) -> HTMLResponse:
        """Individual blog post page."""
        if post_id not in BLOG_POSTS:
            raise HTTPException(status_code=404, detail="Post not found")
        
        post = BLOG_POSTS[post_id]
        
        html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{post.title}</title>
            <style>
                * {{
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }}
                
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif;
                    background: #f8f9fa;
                    color: #000000;
                    line-height: 1.7;
                    min-height: 100vh;
                    display: flex;
                    flex-direction: column;
                }}
                
                /* Sticky Navigation */
                .sticky-nav {{
                    position: sticky;
                    top: 0;
                    z-index: 100;
                    padding: 15px 0;
                }}
                
                /* Shared container for consistent alignment */
                .page-container {{
                    width: 100%;
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 0 20px;
                    box-sizing: border-box;
                }}
                
                .nav-container {{
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                }}
                
                .nav-title {{
                    font-size: 1.5rem;
                    font-weight: 900;
                    color: #000000;
                    text-decoration: none;
                    letter-spacing: -0.02em;
                }}
                
                .navigation {{
                    display: flex;
                    gap: 30px;
                    align-items: center;
                }}
                
                .container {{
                    flex: 1;
                    padding-top: 40px;
                }}
                
                .nav-link {{
                    color: #666666;
                    text-decoration: none;
                    font-weight: 600;
                    font-size: 1rem;
                    transition: color 300ms ease;
                }}
                
                .nav-link:hover {{
                    color: #000000;
                }}
                
                .nav-link.active {{
                    color: #000000;
                }}
                
                .back-link {{
                    display: inline-flex;
                    align-items: center;
                    gap: 8px;
                    color: #666666;
                    text-decoration: none;
                    font-weight: 600;
                    margin-bottom: 60px;
                    transition: all 300ms ease;
                }}
                
                .back-link:hover {{
                    color: #000000;
                    transform: translateX(-3px);
                }}
                
                .back-link .arrow {{
                    transition: transform 300ms ease;
                }}
                
                .back-link:hover .arrow {{
                    transform: translateX(-2px);
                }}
                
                .article-header {{
                    margin-bottom: 60px;
                    padding-bottom: 40px;
                    border-bottom: 1px solid #e9ecef;
                }}
                
                .article-title {{
                    font-size: clamp(2rem, 6vw, 3rem);
                    font-weight: 900;
                    color: #000000;
                    line-height: 1.2;
                    margin-bottom: 20px;
                    letter-spacing: -0.02em;
                }}
                
                .article-meta {{
                    display: flex;
                    gap: 20px;
                    color: #666666;
                    font-size: 0.95rem;
                }}
                
                .author {{
                    font-weight: 600;
                    color: #000000;
                }}
                
                .date {{
                    color: #999999;
                }}
                
                .article-content {{
                    font-size: 1.2rem;
                    color: #404040;
                    line-height: 1.8;
                }}
                
                .article-content p {{
                    margin-bottom: 1.5em;
                }}
                
                .article-content p:last-child {{
                    margin-bottom: 0;
                }}
                
                /* Footer */
                .footer {{
                    margin-top: auto;
                    padding: 40px 0;
                    border-top: 1px solid #e9ecef;
                    text-align: left;
                }}
                
                .footer-text {{
                    color: #666666;
                    font-size: 0.9rem;
                    margin-bottom: 15px;
                }}
                
                .docs-link {{
                    color: #000000;
                    text-decoration: none;
                    font-weight: 600;
                    font-size: 0.95rem;
                    transition: color 300ms ease;
                }}
                
                .docs-link:hover {{
                    color: #404040;
                }}
                
                .footer-content {{
                    display: flex;
                    justify-content: space-between;
                    align-items: flex-start;
                    gap: 40px;
                }}
                
                .footer-left {{
                    flex: 1;
                }}
                
                .footer-right {{
                    text-align: right;
                    flex-shrink: 0;
                }}
                
                .copyright {{
                    color: #666666;
                    font-size: 0.85rem;
                    margin-bottom: 15px;
                }}
                
                .license {{
                    color: #666666;
                    font-size: 0.85rem;
                }}
                
                .footer-link {{
                    color: #666666;
                    text-decoration: none;
                    transition: color 300ms ease;
                }}
                
                .footer-link:hover {{
                    color: #000000;
                }}
                
                /* Dark mode */
                @media (prefers-color-scheme: dark) {{
                    body {{
                        background: #1a1a1a;
                        color: #ffffff;
                    }}
                    
                    .nav-title {{
                        color: #ffffff;
                    }}
                    
                    .nav-link {{
                        color: #999999;
                    }}
                    
                    .nav-link:hover,
                    .nav-link.active {{
                        color: #ffffff;
                    }}
                    
                    .back-link {{
                        color: #999999;
                    }}
                    
                    .back-link:hover {{
                        color: #ffffff;
                    }}
                    
                    .article-header {{
                        border-bottom-color: #333333;
                    }}
                    
                    .article-title {{
                        color: #ffffff;
                    }}
                    
                    .article-meta {{
                        color: #999999;
                    }}
                    
                    .author {{
                        color: #ffffff;
                    }}
                    
                    .date {{
                        color: #666666;
                    }}
                    
                    .article-content {{
                        color: #cccccc;
                    }}
                    
                    .footer {{
                        border-top-color: #333333;
                    }}
                    
                    .footer-text {{
                        color: #999999;
                    }}
                    
                    .docs-link {{
                        color: #ffffff;
                    }}
                    
                    .docs-link:hover {{
                        color: #cccccc;
                    }}
                    
                    .copyright {{
                        color: #999999;
                    }}
                    
                    .license {{
                        color: #999999;
                    }}
                    
                    .footer-link {{
                        color: #999999;
                    }}
                    
                    .footer-link:hover {{
                        color: #ffffff;
                    }}
                }}
                
                /* Mobile responsive */
                @media (max-width: 768px) {{
                    .container {{
                        padding: 40px 20px;
                    }}
                    
                    .back-link {{
                        margin-bottom: 40px;
                    }}
                    
                    .article-header {{
                        margin-bottom: 40px;
                        padding-bottom: 30px;
                    }}
                    
                    .article-meta {{
                        flex-direction: column;
                        gap: 5px;
                    }}
                    
                    .footer {{
                        margin-top: 80px;
                        padding-top: 30px;
                    }}
                    
                    .footer-content {{
                        flex-direction: column;
                        gap: 20px;
                        text-align: left;
                    }}
                    
                    .footer-right {{
                        text-align: left;
                    }}
                }}
            </style>
        </head>
        <body>
            <nav class="sticky-nav">
                <div class="page-container nav-container">
                    <a href="/" class="nav-title">Blog Example</a>
                    <div class="navigation">
                        <a href="/" class="nav-link">Posts</a>
                        <a href="/about" class="nav-link">About</a>
                        <a href="/docs" class="nav-link">API</a>
                    </div>
                </div>
            </nav>
            
            <div class="page-container container">
                <a href="/" class="back-link">
                    <span class="arrow">←</span>
                    <span>Back to Posts</span>
                </a>
                
                <article>
                    <header class="article-header">
                        <h1 class="article-title">{post.title}</h1>
                        <div class="article-meta">
                            <span class="author">{post.author}</span>
                            <span class="date">{post.created_at.strftime('%B %d, %Y')}</span>
                        </div>
                    </header>
                    
                    <div class="article-content">
                        <p>{post.content}</p>
                    </div>
                </article>
            </div>
            
            <footer class="footer">
                <div class="page-container">
                    <div class="footer-content">
                        <div class="footer-left">
                            <div class="footer-text">Built with the Beginnings framework</div>
                            <a href="https://beginnings.8ly.xyz/docs" class="docs-link" target="_blank">View Documentation</a>
                        </div>
                        <div class="footer-right">
                            <div class="copyright">© 2025 <a href="https://8ly.xyz" class="footer-link" target="_blank">8ly LLC</a></div>
                            <div class="license">Made available under the <a href="https://opensource.org/licenses/MIT" class="footer-link" target="_blank">MIT license</a></div>
                        </div>
                    </div>
                </div>
            </footer>
        </body>
        </html>
        """
        return HTMLResponse(content=html_content)
    
    @html_router.get("/about")
    def about_page() -> HTMLResponse:
        """About page."""
        html_content = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>About</title>
            <style>
                * {
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }
                
                body {
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif;
                    background: #f8f9fa;
                    color: #000000;
                    line-height: 1.7;
                    min-height: 100vh;
                    display: flex;
                    flex-direction: column;
                }
                
                /* Sticky Navigation */
                .sticky-nav {
                    position: sticky;
                    top: 0;
                    z-index: 100;
                    padding: 15px 0;
                }
                
                /* Shared container for consistent alignment */
                .page-container {
                    width: 100%;
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 0 20px;
                    box-sizing: border-box;
                }
                
                .nav-container {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                }
                
                .nav-title {
                    font-size: 1.5rem;
                    font-weight: 900;
                    color: #000000;
                    text-decoration: none;
                    letter-spacing: -0.02em;
                }
                
                .navigation {
                    display: flex;
                    gap: 30px;
                    align-items: center;
                }
                
                .container {
                    flex: 1;
                    padding-top: 40px;
                }
                
                .nav-link {
                    color: #666666;
                    text-decoration: none;
                    font-weight: 600;
                    font-size: 1rem;
                    transition: color 300ms ease;
                }
                
                .nav-link:hover {
                    color: #000000;
                }
                
                .nav-link.active {
                    color: #000000;
                }
                
                .back-link {
                    display: inline-flex;
                    align-items: center;
                    gap: 8px;
                    color: #666666;
                    text-decoration: none;
                    font-weight: 600;
                    margin-bottom: 60px;
                    transition: all 300ms ease;
                }
                
                .back-link:hover {
                    color: #000000;
                    transform: translateX(-3px);
                }
                
                .back-link .arrow {
                    transition: transform 300ms ease;
                }
                
                .back-link:hover .arrow {
                    transform: translateX(-2px);
                }
                
                .page-header {
                    margin-bottom: 60px;
                    padding-bottom: 40px;
                    border-bottom: 1px solid #e9ecef;
                }
                
                .page-title {
                    font-size: clamp(2rem, 6vw, 3rem);
                    font-weight: 900;
                    color: #000000;
                    line-height: 1.2;
                    letter-spacing: -0.02em;
                }
                
                .content {
                    font-size: 1.2rem;
                    color: #404040;
                    line-height: 1.8;
                }
                
                .content p {
                    margin-bottom: 1.5em;
                }
                
                .content ul {
                    margin: 2em 0;
                    padding-left: 0;
                    list-style: none;
                }
                
                .content li {
                    margin-bottom: 0.8em;
                    padding-left: 1.5em;
                    position: relative;
                }
                
                .content li::before {
                    content: "→";
                    position: absolute;
                    left: 0;
                    color: #000000;
                    font-weight: 600;
                }
                
                /* Footer */
                .footer {
                    margin-top: auto;
                    padding: 40px 0;
                    border-top: 1px solid #e9ecef;
                    text-align: left;
                }
                
                
                .footer-text {
                    color: #666666;
                    font-size: 0.9rem;
                    margin-bottom: 15px;
                }
                
                .docs-link {
                    color: #000000;
                    text-decoration: none;
                    font-weight: 600;
                    font-size: 0.95rem;
                    transition: color 300ms ease;
                }
                
                .docs-link:hover {
                    color: #404040;
                }
                
                .footer-content {
                    display: flex;
                    justify-content: space-between;
                    align-items: flex-start;
                    gap: 40px;
                }
                
                .footer-left {
                    flex: 1;
                }
                
                .footer-right {
                    text-align: right;
                    flex-shrink: 0;
                }
                
                .copyright {
                    color: #666666;
                    font-size: 0.85rem;
                    margin-bottom: 15px;
                }
                
                .license {
                    color: #666666;
                    font-size: 0.85rem;
                }
                
                .footer-link {
                    color: #666666;
                    text-decoration: none;
                    transition: color 300ms ease;
                }
                
                .footer-link:hover {
                    color: #000000;
                }
                
                /* Dark mode */
                @media (prefers-color-scheme: dark) {
                    body {
                        background: #1a1a1a;
                        color: #ffffff;
                    }
                    
                    .nav-title {
                        color: #ffffff;
                    }
                    
                    .nav-link {
                        color: #999999;
                    }
                    
                    .nav-link:hover,
                    .nav-link.active {
                        color: #ffffff;
                    }
                    
                    .back-link {
                        color: #999999;
                    }
                    
                    .back-link:hover {
                        color: #ffffff;
                    }
                    
                    .page-header {
                        border-bottom-color: #333333;
                    }
                    
                    .page-title {
                        color: #ffffff;
                    }
                    
                    .content {
                        color: #cccccc;
                    }
                    
                    .content li::before {
                        color: #ffffff;
                    }
                    
                    .footer {
                        border-top-color: #333333;
                        background: #1a1a1a;
                    }
                    
                    .footer-text {
                        color: #999999;
                    }
                    
                    .docs-link {
                        color: #ffffff;
                    }
                    
                    .docs-link:hover {
                        color: #cccccc;
                    }
                    
                    .copyright {
                        color: #999999;
                    }
                    
                    .license {
                        color: #999999;
                    }
                    
                    .footer-link {
                        color: #999999;
                    }
                    
                    .footer-link:hover {
                        color: #ffffff;
                    }
                }
                
                /* Mobile responsive */
                @media (max-width: 768px) {
                    .container {
                        padding: 40px 20px;
                    }
                    
                    .back-link {
                        margin-bottom: 40px;
                    }
                    
                    .page-header {
                        margin-bottom: 40px;
                        padding-bottom: 30px;
                    }
                    
                    .footer {
                        margin-top: 80px;
                        padding-top: 30px;
                    }
                    
                    .footer-content {
                        flex-direction: column;
                        gap: 20px;
                        text-align: left;
                    }
                    
                    .footer-right {
                        text-align: left;
                    }
                }
            </style>
        </head>
        <body>
            <nav class="sticky-nav">
                <div class="page-container nav-container">
                    <a href="/" class="nav-title">Blog Example</a>
                    <div class="navigation">
                        <a href="/" class="nav-link">Posts</a>
                        <a href="/about" class="nav-link active">About</a>
                        <a href="/docs" class="nav-link">API</a>
                    </div>
                </div>
            </nav>
            
            <div class="page-container container">
                <a href="/" class="back-link">
                    <span class="arrow">←</span>
                    <span>Back to Posts</span>
                </a>
                
                <header class="page-header">
                    <h1 class="page-title">About</h1>
                </header>
                
                <main class="content">
                    <p>This is an example blog application built with the Beginnings framework, showcasing modern web development patterns and thoughtful design.</p>
                    
                    <p>The application demonstrates several key concepts:</p>
                    
                    <ul>
                        <li>HTML routes for beautiful browser experiences</li>
                        <li>API routes for programmatic access and integrations</li>
                        <li>Configuration-driven development patterns</li>
                        <li>Clean separation of concerns with router organization</li>
                        <li>Automatic dark/light theme detection</li>
                        <li>Responsive design for all screen sizes</li>
                    </ul>
                    
                    <p>Built with a focus on typography, whitespace, and user experience — proving that technical frameworks can produce genuinely beautiful interfaces.</p>
                </main>
            </div>
            
            <footer class="footer">
                <div class="page-container">
                    <div class="footer-content">
                        <div class="footer-left">
                            <div class="footer-text">Built with the Beginnings framework</div>
                            <a href="https://beginnings.8ly.xyz/docs" class="docs-link" target="_blank">View Documentation</a>
                        </div>
                        <div class="footer-right">
                            <div class="copyright">© 2025 <a href="https://8ly.xyz" class="footer-link" target="_blank">8ly LLC</a></div>
                            <div class="license">Made available under the <a href="https://opensource.org/licenses/MIT" class="footer-link" target="_blank">MIT license</a></div>
                        </div>
                    </div>
                </div>
            </footer>
        </body>
        </html>
        """
        return HTMLResponse(content=html_content)
    
    # API Routes (for programmatic access)
    @api_router.get("/posts")
    def list_posts() -> list[BlogPost]:
        """Get all published blog posts."""
        return [post for post in BLOG_POSTS.values() if post.published]
    
    @api_router.get("/posts/{post_id}")
    def get_post(post_id: int) -> BlogPost:
        """Get a specific blog post."""
        if post_id not in BLOG_POSTS:
            raise HTTPException(status_code=404, detail="Post not found")
        return BLOG_POSTS[post_id]
    
    @api_router.post("/posts")
    def create_post(post_data: CreatePostRequest) -> BlogPost:
        """Create a new blog post."""
        global NEXT_POST_ID
        
        new_post = BlogPost(
            id=NEXT_POST_ID,
            title=post_data.title,
            content=post_data.content,
            author=post_data.author,
            created_at=datetime.now()
        )
        
        BLOG_POSTS[NEXT_POST_ID] = new_post
        NEXT_POST_ID += 1
        
        return new_post
    
    @api_router.put("/posts/{post_id}")
    def update_post(post_id: int, post_data: CreatePostRequest) -> BlogPost:
        """Update an existing blog post."""
        if post_id not in BLOG_POSTS:
            raise HTTPException(status_code=404, detail="Post not found")
        
        post = BLOG_POSTS[post_id]
        post.title = post_data.title
        post.content = post_data.content
        post.author = post_data.author
        
        return post
    
    @api_router.delete("/posts/{post_id}")
    def delete_post(post_id: int) -> dict[str, str]:
        """Delete a blog post."""
        if post_id not in BLOG_POSTS:
            raise HTTPException(status_code=404, detail="Post not found")
        
        del BLOG_POSTS[post_id]
        return {"message": "Post deleted successfully"}

    # Test route to demonstrate error handling
    @html_router.get("/test-error")
    def test_error() -> None:
        """Test route that throws an error."""
        raise HTTPException(status_code=404, detail="This is a test error page")

    @api_router.get("/test-error")
    def test_api_error() -> None:
        """Test API route that throws an error."""
        raise HTTPException(status_code=404, detail="This is a test API error")

    @html_router.get("/test-500")
    def test_500_error() -> None:
        """Test route that throws a 500 error."""
        raise HTTPException(status_code=500, detail="This is a test 500 error")
    
    @html_router.get("/test-runtime-error")
    def test_runtime_error() -> None:
        """Test route that throws a RuntimeError."""
        raise RuntimeError("This is a test RuntimeError")
    
    # Include routers in the app
    app.include_router(html_router)
    app.include_router(api_router)
    
    return app


# Create the application instance
app = create_blog_app()


if __name__ == "__main__":
    # Run the blog application
    print("Starting Blog Application...")
    print("HTML Interface: http://localhost:8000/")
    print("API Documentation: http://localhost:8000/docs")
    print("API Endpoints: http://localhost:8000/api/v1/posts")
    
    app.run(host="127.0.0.1", port=8888, reload=False)
