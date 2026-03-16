from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import sqlite3

app = FastAPI()
# initialize SQLite
conn = sqlite3.connect("tasks.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    completed BOOLEAN NOT NULL DEFAULT 0,
    due_date TEXT
)
""")
conn.commit()

class Task(BaseModel):
    id: Optional[int]
    title: str
    completed: Optional[bool] = False
    due_date: Optional[datetime] = None

@app.get("/tasks", response_model=List[Task])
def read_tasks():
    cursor.execute("SELECT id, title, completed, due_date FROM tasks")
    rows = cursor.fetchall()
    tasks = []
    for id, title, completed, due_date in rows:
        tasks.append(Task(id=id, title=title, completed=bool(completed), due_date=due_date))
    return tasks

@app.post("/tasks", response_model=Task)
def create_task(task: Task):
    cursor.execute(
        "INSERT INTO tasks (title, completed, due_date) VALUES (?, ?, ?)",
        (task.title, int(task.completed), task.due_date.isoformat() if task.due_date else None)
    )
    conn.commit()
    task.id = cursor.lastrowid
    return task

@app.patch("/tasks/{task_id}", response_model=Task)
def update_task(task_id: int, task: Task):
    cursor.execute("SELECT id FROM tasks WHERE id=?", (task_id,))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="Task not found")
    cursor.execute(
        "UPDATE tasks SET title=?, completed=?, due_date=? WHERE id=?",
        (task.title, int(task.completed), task.due_date.isoformat() if task.due_date else None, task_id)
    )
    conn.commit()
    task.id = task_id
    return task

@app.delete("/tasks/{task_id}")
def delete_task(task_id: int):
    cursor.execute("DELETE FROM tasks WHERE id=?", (task_id,))
    conn.commit()
    return {"ok": True}

