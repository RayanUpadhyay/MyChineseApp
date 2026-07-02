import sqlite3
import bcrypt
import pandas as pd
from pathlib import Path
from datetime import datetime

# Database path
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "radicals_app.db"
USERS_CSV = BASE_DIR / "users.csv"


def get_connection():
    """Get database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Access columns by name
    return conn


def init_db():
    """Initialize database and create tables."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            xp INTEGER DEFAULT 0,
            level INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()


def migrate_from_csv():
    """Migrate existing users from CSV to SQLite (one-time operation)."""
    if not USERS_CSV.exists():
        return
    
    try:
        df = pd.read_csv(USERS_CSV)
        
        # Check if migration already done
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        existing_count = cursor.fetchone()[0]
        
        if existing_count > 0:
            conn.close()
            return
        
        # Migrate users
        migrated = 0
        for _, row in df.iterrows():
            username = row.get('username', '')
            email = row.get('email', f"{username}@example.com")  # Default email if missing
            password = row.get('password', '')
            xp = int(row.get('xp', 0))
            level = int(row.get('level', 1))
            
            if username and password:
                # Hash the existing password
                password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                
                try:
                    cursor.execute("""
                        INSERT INTO users (username, email, password_hash, xp, level)
                        VALUES (?, ?, ?, ?, ?)
                    """, (username, email, password_hash, xp, level))
                    migrated += 1
                except sqlite3.IntegrityError:
                    pass  # User already exists, skip
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        pass  # Silent fail in production


def create_user(username, email, password):
    """
    Create a new user account.
    Returns: (success: bool, message: str)
    """
    if not username or not email or not password:
        return False, "All fields are required"
    
    if len(password) < 4:
        return False, "Password must be at least 4 characters"
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Hash password
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        cursor.execute("""
            INSERT INTO users (username, email, password_hash, xp, level)
            VALUES (?, ?, ?, 0, 1)
        """, (username, email, password_hash))
        
        conn.commit()
        conn.close()
        return True, "Account created successfully!"
        
    except sqlite3.IntegrityError as e:
        if "username" in str(e):
            return False, "Username already exists"
        elif "email" in str(e):
            return False, "Email already exists"
        else:
            return False, "User already exists"
    except Exception as e:
        return False, f"Error creating account: {e}"


def authenticate_user(username, password):
    """
    Authenticate user login.
    Returns: (success: bool, message: str)
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT password_hash FROM users WHERE username = ?", (username,))
        result = cursor.fetchone()
        conn.close()
        
        if result is None:
            return False, "Invalid username or password"
        
        password_hash = result['password_hash']
        
        # Verify password
        if bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8')):
            return True, "Login successful"
        else:
            return False, "Invalid username or password"
            
    except Exception as e:
        return False, f"Login error: {e}"


def get_user(username):
    """
    Get user data by username.
    Returns: dict with user data or None
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, username, email, xp, level, created_at
            FROM users WHERE username = ?
        """, (username,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return dict(result)
        return None
        
    except Exception as e:
        print(f"Error getting user: {e}")
        return None


def update_xp(username, amount):
    """
    Update user XP and recalculate level.
    Level = (XP // 100) + 1
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Get current XP
        cursor.execute("SELECT xp FROM users WHERE username = ?", (username,))
        result = cursor.fetchone()
        
        if result is None:
            conn.close()
            return False
        
        new_xp = result['xp'] + amount
        new_level = (new_xp // 100) + 1
        
        cursor.execute("""
            UPDATE users SET xp = ?, level = ?
            WHERE username = ?
        """, (new_xp, new_level, username))
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        print(f"Error updating XP: {e}")
        return False


def get_leaderboard():
    """
    Get all users sorted by XP (descending).
    Returns: list of dicts
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT username, level, xp
            FROM users
            ORDER BY xp DESC
        """)
        
        results = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in results]
        
    except Exception as e:
        print(f"Error getting leaderboard: {e}")
        return []


# Initialize database on import
if __name__ == "__main__":
    init_db()
    migrate_from_csv()
