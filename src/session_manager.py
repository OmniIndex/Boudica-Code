"""
Session Manager - Persistent storage of projects and conversation history using SQLite
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional


class SessionManager:
    """Manages project sessions and conversation history using SQLite"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Sessions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    stack TEXT NOT NULL,
                    project_path TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    description TEXT
                )
            """)
            
            # Conversation history table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversation_history (
                    history_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    turn_type TEXT NOT NULL,
                    prompt TEXT,
                    response TEXT,
                    file_path TEXT,
                    action TEXT,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
                )
            """)
            
            # File backups index
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS file_backups (
                    backup_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    file_path TEXT NOT NULL,
                    backup_path TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    change_description TEXT,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
                )
            """)
            
            conn.commit()
    
    def create_session(self, name: str, stack: str, description: str = None) -> Dict:
        """Create a new project session"""
        project_path = str(Path.home() / "boudica_code" / "projects" / name)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO sessions (name, stack, project_path, description)
                    VALUES (?, ?, ?, ?)
                """, (name, stack, project_path, description))
                conn.commit()
                
                session_id = cursor.lastrowid
                return {
                    'session_id': session_id,
                    'name': name,
                    'stack': stack,
                    'project_path': project_path,
                    'created_at': datetime.now().isoformat(),
                    'description': description
                }
            except sqlite3.IntegrityError:
                return None
    
    def get_session(self, name: str) -> Optional[Dict]:
        """Get session by name"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM sessions WHERE name = ?", (name,))
            row = cursor.fetchone()
            
            if row:
                cursor.execute(
                    "UPDATE sessions SET last_accessed = CURRENT_TIMESTAMP WHERE name = ?",
                    (name,)
                )
                conn.commit()
                return dict(row)
            return None
    
    def session_exists(self, name: str) -> bool:
        """Check if session exists"""
        return self.get_session(name) is not None
    
    def list_sessions(self) -> List[Dict]:
        """List all sessions"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM sessions
                ORDER BY last_accessed DESC
            """)
            return [dict(row) for row in cursor.fetchall()]
    
    def add_history(self, session_name: str, action: str, prompt: str = None, 
                   response: str = None, file_path: str = None):
        """Add entry to conversation history"""
        
        session = self.get_session(session_name)
        if not session:
            return
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO conversation_history
                (session_id, turn_type, prompt, response, file_path, action)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (session['session_id'], 'user_action', prompt, response, file_path, action))
            conn.commit()
    
    def get_history(self, session_name: str, limit: int = 50) -> List[Dict]:
        """Get conversation history for a session"""
        
        session = self.get_session(session_name)
        if not session:
            return []
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM conversation_history
                WHERE session_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (session['session_id'], limit))
            return [dict(row) for row in cursor.fetchall()]
    
    def add_backup(self, session_name: str, file_path: str, backup_path: str, 
                   change_description: str = None):
        """Log a file backup"""
        
        session = self.get_session(session_name)
        if not session:
            return
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO file_backups
                (session_id, file_path, backup_path, change_description)
                VALUES (?, ?, ?, ?)
            """, (session['session_id'], file_path, backup_path, change_description))
            conn.commit()
    
    def get_backups(self, session_name: str, file_path: str = None) -> List[Dict]:
        """Get backups for a session or specific file"""
        
        session = self.get_session(session_name)
        if not session:
            return []
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            if file_path:
                cursor.execute("""
                    SELECT * FROM file_backups
                    WHERE session_id = ? AND file_path = ?
                    ORDER BY timestamp DESC
                """, (session['session_id'], file_path))
            else:
                cursor.execute("""
                    SELECT * FROM file_backups
                    WHERE session_id = ?
                    ORDER BY timestamp DESC
                """, (session['session_id'],))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def delete_session(self, name: str) -> bool:
        """Delete a session and all associated data"""
        
        session = self.get_session(name)
        if not session:
            return False
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Delete associated records
            cursor.execute("DELETE FROM conversation_history WHERE session_id = ?", 
                          (session['session_id'],))
            cursor.execute("DELETE FROM file_backups WHERE session_id = ?", 
                          (session['session_id'],))
            cursor.execute("DELETE FROM sessions WHERE session_id = ?", 
                          (session['session_id'],))
            
            conn.commit()
            return True
