import sqlite3
import os
from werkzeug.security import generate_password_hash

# ─────────────────────────────────────────────
#  CONNECTION
# ─────────────────────────────────────────────

def connect():
    base_path = os.path.dirname(os.path.abspath(__file__))
    db_path   = os.path.join(base_path, "sysarch.db")
    conn      = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


# ─────────────────────────────────────────────
#  INIT TABLES
# ─────────────────────────────────────────────

def init_database():
    conn = connect()
    cur  = conn.cursor()

    cur.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            idno           VARCHAR(20)  UNIQUE NOT NULL,
            lastname       VARCHAR(50)  NOT NULL,
            firstname      VARCHAR(50)  NOT NULL,
            middlename     VARCHAR(50),
            course         VARCHAR(20)  NOT NULL,
            level          VARCHAR(5)   NOT NULL,
            email          VARCHAR(100) UNIQUE NOT NULL,
            address        TEXT,
            password       VARCHAR(255) NOT NULL,
            image_filename VARCHAR(255),
            created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       VARCHAR(100) NOT NULL,
            email      VARCHAR(100) UNIQUE NOT NULL,
            password   VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')


    # ── Default admin account (only inserted once) ──
    cur.execute("SELECT COUNT(*) FROM users WHERE email = ?", ("admin@ccs.edu",))
    if cur.fetchone()[0] == 0:
        cur.execute(
            "INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
            ("Administrator", "admin@ccs.edu", generate_password_hash("admin123"))
        )
        print("[INIT] Default admin account created → email: admin@ccs.edu | password: admin123")

    conn.commit()
    conn.close()


# ─────────────────────────────────────────────
#  GENERIC CRUD
# ─────────────────────────────────────────────

def getall(table):
    conn = connect()
    cur  = conn.cursor()
    cur.execute(f"SELECT * FROM {table}")
    rows = cur.fetchall()
    conn.close()
    return rows


def getone(table, **kwargs):
    conn  = connect()
    cur   = conn.cursor()
    field = list(kwargs.keys())[0]
    value = kwargs[field]
    try:
        cur.execute(f"SELECT * FROM {table} WHERE {field} = ?", (value,))
        return cur.fetchone()
    except Exception as e:
        print("getone error:", e)
        return None
    finally:
        conn.close()


def addrecord(table, **kwargs):
    conn         = connect()
    cur          = conn.cursor()
    fields       = ", ".join(kwargs.keys())
    placeholders = ", ".join(["?"] * len(kwargs))
    values       = tuple(kwargs.values())
    try:
        cur.execute(f"INSERT INTO {table} ({fields}) VALUES ({placeholders})", values)
        conn.commit()
        return True
    except Exception as e:
        print("addrecord error:", e)
        conn.rollback()
        return False
    finally:
        conn.close()


def updaterecord(table, idfield, idvalue, **kwargs):
    conn       = connect()
    cur        = conn.cursor()
    set_clause = ", ".join([f"{k} = ?" for k in kwargs.keys()])
    values     = tuple(kwargs.values()) + (idvalue,)
    try:
        cur.execute(f"UPDATE {table} SET {set_clause} WHERE {idfield} = ?", values)
        conn.commit()
        return cur.rowcount > 0
    except Exception as e:
        print("updaterecord error:", e)
        conn.rollback()
        return False
    finally:
        conn.close()


def deleterecord(table, **kwargs):
    conn  = connect()
    cur   = conn.cursor()
    field = list(kwargs.keys())[0]
    value = kwargs[field]
    try:
        cur.execute(f"DELETE FROM {table} WHERE {field} = ?", (value,))
        conn.commit()
        return cur.rowcount > 0
    except Exception as e:
        print("deleterecord error:", e)
        conn.rollback()
        return False
    finally:
        conn.close()


def recordexists(table, **kwargs):
    conn  = connect()
    cur   = conn.cursor()
    field = list(kwargs.keys())[0]
    value = kwargs[field]
    try:
        cur.execute(f"SELECT COUNT(*) FROM {table} WHERE {field} = ?", (value,))
        return cur.fetchone()[0] > 0
    except:
        return False
    finally:
        conn.close()


def recordexists_exclude(table, field, value, exclude_field, exclude_value):
    conn = connect()
    cur  = conn.cursor()
    try:
        cur.execute(
            f"SELECT COUNT(*) FROM {table} WHERE {field} = ? AND {exclude_field} != ?",
            (value, exclude_value)
        )
        return cur.fetchone()[0] > 0
    except:
        return False
    finally:
        conn.close()


# ─────────────────────────────────────────────
#  STUDENT FUNCTIONS
# ─────────────────────────────────────────────

def get_student_by_idno(idno):
    return getone('students', idno=idno)


# ─────────────────────────────────────────────
#  USER (ADMIN) FUNCTIONS
# ─────────────────────────────────────────────

def get_user_by_email(email):
    return getone('users', email=email)


def get_all_users():
    return getall('users')


def delete_user(user_id):
    return deleterecord('users', id=user_id)