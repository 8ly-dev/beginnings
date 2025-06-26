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
    app = App(config_dir="config", environment="development")
    
    # Create HTML router for browser-facing pages
    html_router = app.create_html_router(prefix="/blog")
    
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
                    <article>
                        <h2><a href="/blog/posts/{post.id}">{post.title}</a></h2>
                        <p>By {post.author} on {post.created_at.strftime('%B %d, %Y')}</p>
                        <p>{post.content[:100]}...</p>
                    </article>
                    <hr>
                """
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>My Blog</title>
            <style>
                body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
                article {{ margin-bottom: 20px; }}
                a {{ color: #007bff; text-decoration: none; }}
                a:hover {{ text-decoration: underline; }}
            </style>
        </head>
        <body>
            <header>
                <h1>My Blog</h1>
                <nav>
                    <a href="/blog/">Home</a> | 
                    <a href="/blog/about">About</a> |
                    <a href="/api/v1/posts">API</a>
                </nav>
            </header>
            <main>
                {posts_html}
            </main>
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
        <html>
        <head>
            <title>{post.title} - My Blog</title>
            <style>
                body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
                .meta {{ color: #666; font-style: italic; }}
                a {{ color: #007bff; text-decoration: none; }}
                a:hover {{ text-decoration: underline; }}
            </style>
        </head>
        <body>
            <header>
                <nav><a href="/blog/">&larr; Back to Blog</a></nav>
            </header>
            <main>
                <article>
                    <h1>{post.title}</h1>
                    <p class="meta">By {post.author} on {post.created_at.strftime('%B %d, %Y at %I:%M %p')}</p>
                    <div>{post.content}</div>
                </article>
            </main>
        </body>
        </html>
        """
        return HTMLResponse(content=html_content)
    
    @html_router.get("/about")
    def about_page() -> HTMLResponse:
        """About page."""
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>About - My Blog</title>
            <style>
                body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
                a { color: #007bff; text-decoration: none; }
                a:hover { text-decoration: underline; }
            </style>
        </head>
        <body>
            <header>
                <nav><a href="/blog/">&larr; Back to Blog</a></nav>
            </header>
            <main>
                <h1>About This Blog</h1>
                <p>This is an example blog application built with the Beginnings framework.</p>
                <p>It demonstrates:</p>
                <ul>
                    <li>HTML routes for browser interaction</li>
                    <li>API routes for programmatic access</li>
                    <li>Configuration-driven development</li>
                    <li>Router separation and organization</li>
                </ul>
            </main>
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
    
    # Include routers in the app
    app.include_router(html_router)
    app.include_router(api_router)
    
    return app


# Create the application instance
app = create_blog_app()


if __name__ == "__main__":
    # Run the blog application
    print("Starting Blog Application...")
    print("HTML Interface: http://localhost:8000/blog/")
    print("API Documentation: http://localhost:8000/docs")
    print("API Endpoints: http://localhost:8000/api/v1/posts")
    
    app.run(host="127.0.0.1", port=8000, reload=True)