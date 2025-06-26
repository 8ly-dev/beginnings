"""
Mixed Web Application Example - Demonstrates HTML + API in one app.

This example shows how to build a web application that serves both
HTML pages for users and API endpoints for programmatic access,
sharing the same data and configuration.
"""

from __future__ import annotations

import time
from datetime import datetime
from typing import Any

from fastapi import HTTPException, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel

from beginnings import App


# Data models
class Task(BaseModel):
    """Task data model."""
    id: int
    title: str
    description: str
    completed: bool = False
    created_at: datetime
    priority: str = "medium"  # low, medium, high


class TaskCreate(BaseModel):
    """Task creation request model."""
    title: str
    description: str
    priority: str = "medium"


# Mock database
TASKS: dict[int, Task] = {
    1: Task(
        id=1,
        title="Set up project",
        description="Initialize the new project with proper structure",
        completed=True,
        created_at=datetime(2024, 1, 1, 9, 0, 0),
        priority="high"
    ),
    2: Task(
        id=2,
        title="Write documentation",
        description="Create comprehensive documentation for the API",
        completed=False,
        created_at=datetime(2024, 1, 2, 10, 0, 0),
        priority="medium"
    ),
    3: Task(
        id=3,
        title="Add tests",
        description="Write unit tests for all endpoints",
        completed=False,
        created_at=datetime(2024, 1, 3, 11, 0, 0),
        priority="high"
    ),
}
NEXT_TASK_ID = 4


def create_mixed_app() -> App:
    """Create and configure the mixed web application."""
    # Initialize the Beginnings app
    app = App(config_dir="config", environment="development")
    
    # Create HTML router for web interface
    html_router = app.create_html_router()
    
    # Create API router for programmatic access
    api_router = app.create_api_router(prefix="/api")
    
    # Shared template function
    def render_page_template(title: str, content: str) -> str:
        """Render a page with common template."""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{title} - Task Manager</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 20px;
                    background-color: #f5f5f5;
                }}
                .container {{
                    background: white;
                    padding: 20px;
                    border-radius: 8px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
                nav {{
                    margin-bottom: 20px;
                    padding-bottom: 10px;
                    border-bottom: 1px solid #eee;
                }}
                nav a {{
                    color: #007bff;
                    text-decoration: none;
                    margin-right: 15px;
                }}
                nav a:hover {{ text-decoration: underline; }}
                .task {{
                    background: #f8f9fa;
                    border: 1px solid #dee2e6;
                    border-radius: 4px;
                    padding: 15px;
                    margin-bottom: 10px;
                }}
                .task.completed {{ background: #d4edda; border-color: #c3e6cb; }}
                .priority-high {{ border-left: 4px solid #dc3545; }}
                .priority-medium {{ border-left: 4px solid #ffc107; }}
                .priority-low {{ border-left: 4px solid #28a745; }}
                .form-group {{
                    margin-bottom: 15px;
                }}
                label {{
                    display: block;
                    margin-bottom: 5px;
                    font-weight: bold;
                }}
                input, textarea, select {{
                    width: 100%;
                    padding: 8px;
                    border: 1px solid #ddd;
                    border-radius: 4px;
                    box-sizing: border-box;
                }}
                button {{
                    background: #007bff;
                    color: white;
                    border: none;
                    padding: 10px 20px;
                    border-radius: 4px;
                    cursor: pointer;
                }}
                button:hover {{ background: #0056b3; }}
                .btn-small {{
                    padding: 5px 10px;
                    font-size: 12px;
                    margin-left: 5px;
                }}
                .btn-danger {{ background: #dc3545; }}
                .btn-danger:hover {{ background: #c82333; }}
                .btn-success {{ background: #28a745; }}
                .btn-success:hover {{ background: #218838; }}
            </style>
        </head>
        <body>
            <div class="container">
                <header>
                    <h1>Task Manager</h1>
                    <nav>
                        <a href="/">Home</a>
                        <a href="/add">Add Task</a>
                        <a href="/api-info">API Info</a>
                        <a href="/docs" target="_blank">API Docs</a>
                    </nav>
                </header>
                <main>
                    {content}
                </main>
            </div>
        </body>
        </html>
        """
    
    # HTML Routes (Web Interface)
    @html_router.get("/")
    def home_page() -> HTMLResponse:
        """Task list home page."""
        tasks_html = ""
        completed_count = 0
        total_count = len(TASKS)
        
        for task in sorted(TASKS.values(), key=lambda t: t.created_at, reverse=True):
            if task.completed:
                completed_count += 1
            
            status_text = "✓ Completed" if task.completed else "Pending"
            status_action = f"""
                <form method="post" action="/tasks/{task.id}/toggle" style="display: inline;">
                    <button type="submit" class="btn-small {'btn-success' if not task.completed else 'btn-danger'}">
                        {'Mark Complete' if not task.completed else 'Mark Pending'}
                    </button>
                </form>
            """ if not task.completed else ""
            
            tasks_html += f"""
                <div class="task {'completed' if task.completed else ''} priority-{task.priority}">
                    <h3>{task.title}</h3>
                    <p>{task.description}</p>
                    <small>
                        Priority: {task.priority.title()} | 
                        Created: {task.created_at.strftime('%B %d, %Y')} | 
                        Status: {status_text}
                    </small>
                    <div style="margin-top: 10px;">
                        {status_action}
                        <form method="post" action="/tasks/{task.id}/delete" style="display: inline;">
                            <button type="submit" class="btn-small btn-danger" 
                                    onclick="return confirm('Delete this task?')">Delete</button>
                        </form>
                    </div>
                </div>
            """
        
        if not tasks_html:
            tasks_html = "<p>No tasks yet. <a href='/add'>Add your first task!</a></p>"
        
        content = f"""
            <div style="background: #e9ecef; padding: 15px; border-radius: 4px; margin-bottom: 20px;">
                <h2>Dashboard</h2>
                <p>Total Tasks: {total_count} | Completed: {completed_count} | Pending: {total_count - completed_count}</p>
            </div>
            
            <h2>Your Tasks</h2>
            {tasks_html}
        """
        
        return HTMLResponse(content=render_page_template("Dashboard", content))
    
    @html_router.get("/add")
    def add_task_page() -> HTMLResponse:
        """Add new task page."""
        content = """
            <h2>Add New Task</h2>
            <form method="post" action="/tasks">
                <div class="form-group">
                    <label for="title">Title:</label>
                    <input type="text" id="title" name="title" required>
                </div>
                
                <div class="form-group">
                    <label for="description">Description:</label>
                    <textarea id="description" name="description" rows="4" required></textarea>
                </div>
                
                <div class="form-group">
                    <label for="priority">Priority:</label>
                    <select id="priority" name="priority">
                        <option value="low">Low</option>
                        <option value="medium" selected>Medium</option>
                        <option value="high">High</option>
                    </select>
                </div>
                
                <button type="submit">Add Task</button>
                <a href="/" style="margin-left: 10px;">Cancel</a>
            </form>
        """
        
        return HTMLResponse(content=render_page_template("Add Task", content))
    
    @html_router.post("/tasks")
    def create_task_form(
        title: str = Form(...),
        description: str = Form(...),
        priority: str = Form("medium")
    ) -> RedirectResponse:
        """Handle task creation from form."""
        global NEXT_TASK_ID
        
        new_task = Task(
            id=NEXT_TASK_ID,
            title=title,
            description=description,
            priority=priority,
            created_at=datetime.now()
        )
        
        TASKS[NEXT_TASK_ID] = new_task
        NEXT_TASK_ID += 1
        
        return RedirectResponse(url="/", status_code=303)
    
    @html_router.post("/tasks/{task_id}/toggle")
    def toggle_task_form(task_id: int) -> RedirectResponse:
        """Toggle task completion status."""
        if task_id in TASKS:
            TASKS[task_id].completed = not TASKS[task_id].completed
        return RedirectResponse(url="/", status_code=303)
    
    @html_router.post("/tasks/{task_id}/delete")
    def delete_task_form(task_id: int) -> RedirectResponse:
        """Delete task from form."""
        if task_id in TASKS:
            del TASKS[task_id]
        return RedirectResponse(url="/", status_code=303)
    
    @html_router.get("/api-info")
    def api_info_page() -> HTMLResponse:
        """API information page."""
        content = """
            <h2>API Information</h2>
            <p>This application provides both a web interface and a REST API.</p>
            
            <h3>API Endpoints</h3>
            <ul>
                <li><strong>GET /api/tasks</strong> - Get all tasks</li>
                <li><strong>GET /api/tasks/{id}</strong> - Get specific task</li>
                <li><strong>POST /api/tasks</strong> - Create new task</li>
                <li><strong>PUT /api/tasks/{id}</strong> - Update task</li>
                <li><strong>DELETE /api/tasks/{id}</strong> - Delete task</li>
                <li><strong>POST /api/tasks/{id}/toggle</strong> - Toggle completion</li>
            </ul>
            
            <h3>Example API Usage</h3>
            <pre style="background: #f8f9fa; padding: 15px; border-radius: 4px; overflow-x: auto;">
# Get all tasks
curl http://localhost:8002/api/tasks

# Create a new task
curl -X POST http://localhost:8002/api/tasks \\
  -H "Content-Type: application/json" \\
  -d '{"title": "New Task", "description": "Task description", "priority": "high"}'

# Toggle task completion
curl -X POST http://localhost:8002/api/tasks/1/toggle</pre>
            
            <p><a href="/docs" target="_blank">View Interactive API Documentation</a></p>
        """
        
        return HTMLResponse(content=render_page_template("API Info", content))
    
    # API Routes (Programmatic Access)
    @api_router.get("/tasks")
    def list_tasks_api() -> list[Task]:
        """Get all tasks via API."""
        return list(TASKS.values())
    
    @api_router.get("/tasks/{task_id}")
    def get_task_api(task_id: int) -> Task:
        """Get specific task via API."""
        if task_id not in TASKS:
            raise HTTPException(status_code=404, detail="Task not found")
        return TASKS[task_id]
    
    @api_router.post("/tasks")
    def create_task_api(task_data: TaskCreate) -> Task:
        """Create new task via API."""
        global NEXT_TASK_ID
        
        new_task = Task(
            id=NEXT_TASK_ID,
            title=task_data.title,
            description=task_data.description,
            priority=task_data.priority,
            created_at=datetime.now()
        )
        
        TASKS[NEXT_TASK_ID] = new_task
        NEXT_TASK_ID += 1
        
        return new_task
    
    @api_router.put("/tasks/{task_id}")
    def update_task_api(task_id: int, task_data: TaskCreate) -> Task:
        """Update task via API."""
        if task_id not in TASKS:
            raise HTTPException(status_code=404, detail="Task not found")
        
        task = TASKS[task_id]
        task.title = task_data.title
        task.description = task_data.description
        task.priority = task_data.priority
        
        return task
    
    @api_router.delete("/tasks/{task_id}")
    def delete_task_api(task_id: int) -> dict[str, str]:
        """Delete task via API."""
        if task_id not in TASKS:
            raise HTTPException(status_code=404, detail="Task not found")
        
        del TASKS[task_id]
        return {"message": "Task deleted successfully"}
    
    @api_router.post("/tasks/{task_id}/toggle")
    def toggle_task_api(task_id: int) -> Task:
        """Toggle task completion via API."""
        if task_id not in TASKS:
            raise HTTPException(status_code=404, detail="Task not found")
        
        task = TASKS[task_id]
        task.completed = not task.completed
        return task
    
    @api_router.get("/stats")
    def get_stats_api() -> dict[str, Any]:
        """Get task statistics via API."""
        total = len(TASKS)
        completed = sum(1 for task in TASKS.values() if task.completed)
        by_priority = {"high": 0, "medium": 0, "low": 0}
        
        for task in TASKS.values():
            by_priority[task.priority] += 1
        
        return {
            "total_tasks": total,
            "completed_tasks": completed,
            "pending_tasks": total - completed,
            "completion_rate": round((completed / total * 100) if total > 0 else 0, 2),
            "tasks_by_priority": by_priority
        }
    
    # Include routers
    app.include_router(html_router)
    app.include_router(api_router)
    
    return app


# Create the application instance
app = create_mixed_app()


if __name__ == "__main__":
    # Run the mixed web application
    print("Starting Mixed Web Application...")
    print("Web Interface: http://localhost:8002/")
    print("API Documentation: http://localhost:8002/docs")
    print("API Endpoints: http://localhost:8002/api/tasks")
    print("API Stats: http://localhost:8002/api/stats")
    
    app.run(host="127.0.0.1", port=8002, reload=True)