import sqlite3
import os
from werkzeug.security import generate_password_hash


def connect():
    base_path = os.path.dirname(os.path.abspath(__file__))
    db_path   = os.path.join(base_path, "sysarch.db")
    conn      = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_database():
    conn = connect()
    cur  = conn.cursor()

    cur.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            idno              VARCHAR(20)  UNIQUE NOT NULL,
            lastname          VARCHAR(50)  NOT NULL,
            firstname         VARCHAR(50)  NOT NULL,
            middlename        VARCHAR(50),
            course            VARCHAR(20)  NOT NULL,
            level             VARCHAR(5)   NOT NULL,
            email             VARCHAR(100) UNIQUE NOT NULL,
            address           TEXT,
            password          VARCHAR(255) NOT NULL,
            profile_image     VARCHAR(255),
            remaining_session INTEGER DEFAULT 30,
            created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

    cur.execute('''
        CREATE TABLE IF NOT EXISTS sit_in (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            idno       VARCHAR(20) NOT NULL,
            purpose    VARCHAR(100) NOT NULL,
            lab        VARCHAR(20)  NOT NULL,
            login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status     VARCHAR(20) DEFAULT 'active',
            FOREIGN KEY (idno) REFERENCES students(idno)
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS sit_in_records (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            idno        VARCHAR(20) NOT NULL,
            purpose     VARCHAR(100) NOT NULL,
            lab         VARCHAR(20)  NOT NULL,
            login_time  TIMESTAMP NOT NULL,
            logout_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (idno) REFERENCES students(idno)
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS announcements (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            content    TEXT NOT NULL,
            posted_by  VARCHAR(100) DEFAULT 'CCS Admin',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS feedback (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            idno       VARCHAR(20) NOT NULL,
            message    TEXT NOT NULL,
            rating     INTEGER DEFAULT 5,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (idno) REFERENCES students(idno)
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS reservations (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            idno       VARCHAR(20)  NOT NULL,
            lab        VARCHAR(20)  NOT NULL,
            date       DATE         NOT NULL,
            time_slot  VARCHAR(50)  NOT NULL,
            purpose    VARCHAR(100) NOT NULL,
            status     VARCHAR(20)  DEFAULT 'pending',
            created_at TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (idno) REFERENCES students(idno)
        )
    ''')

    # Migrations — add columns if missing
    migrations = [
        "ALTER TABLE students ADD COLUMN profile_image VARCHAR(255)",
        "ALTER TABLE students ADD COLUMN remaining_session INTEGER DEFAULT 30",
    ]
    for sql in migrations:
        try:
            cur.execute(sql)
            conn.commit()
        except Exception:
            pass

    # Default admin
    cur.execute("SELECT COUNT(*) FROM users WHERE email = ?", ("admin@ccs.edu",))
    if cur.fetchone()[0] == 0:
        cur.execute(
            "INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
            ("Administrator", "admin@ccs.edu", generate_password_hash("admin123!"))
        )
        print("[INIT] Default admin → email: admin@ccs.edu | password: admin123!")

    conn.commit()
    conn.close()


# ── Generic CRUD ──────────────────────────────────────────

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
    except Exception:
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
    except Exception:
        return False
    finally:
        conn.close()


# ── Students ──────────────────────────────────────────────

def get_student_by_idno(idno):
    return getone('students', idno=idno)


def get_all_students():
    conn = connect()
    cur  = conn.cursor()
    cur.execute("SELECT * FROM students ORDER BY lastname, firstname")
    rows = cur.fetchall()
    conn.close()
    return rows


def search_students(query):
    conn = connect()
    cur  = conn.cursor()
    like = f"%{query}%"
    cur.execute(
        "SELECT * FROM students WHERE idno LIKE ? OR firstname LIKE ? OR lastname LIKE ? ORDER BY lastname",
        (like, like, like)
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def reset_all_sessions():
    conn = connect()
    cur  = conn.cursor()
    cur.execute("UPDATE students SET remaining_session = 30")
    conn.commit()
    conn.close()


# ── Users (admin) ─────────────────────────────────────────

def get_user_by_email(email):
    return getone('users', email=email)


# ── Sit-in ────────────────────────────────────────────────

def is_student_sitting_in(idno):
    conn = connect()
    cur  = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM sit_in WHERE idno = ? AND status = 'active'", (idno,))
    result = cur.fetchone()[0] > 0
    conn.close()
    return result


def sitin_student(idno, purpose, lab):
    conn = connect()
    cur  = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO sit_in (idno, purpose, lab) VALUES (?, ?, ?)",
            (idno, purpose, lab)
        )
        cur.execute(
            "UPDATE students SET remaining_session = remaining_session - 1 WHERE idno = ?",
            (idno,)
        )
        conn.commit()
        return True
    except Exception as e:
        print("sitin_student error:", e)
        conn.rollback()
        return False
    finally:
        conn.close()


def logout_student(sit_id):
    conn = connect()
    cur  = conn.cursor()
    try:
        # Get the sit-in record first
        cur.execute("SELECT * FROM sit_in WHERE id = ?", (sit_id,))
        row = cur.fetchone()
        if not row:
            return False
        # Copy to sit_in_records
        cur.execute(
            "INSERT INTO sit_in_records (idno, purpose, lab, login_time) VALUES (?, ?, ?, ?)",
            (row['idno'], row['purpose'], row['lab'], row['login_time'])
        )
        # Remove from active sit_in
        cur.execute("DELETE FROM sit_in WHERE id = ?", (sit_id,))
        conn.commit()
        return True
    except Exception as e:
        print("logout_student error:", e)
        conn.rollback()
        return False
    finally:
        conn.close()


def get_active_sitin():
    conn = connect()
    cur  = conn.cursor()
    cur.execute('''
        SELECT s.id, s.idno, st.firstname, st.lastname, st.course, st.level,
               s.purpose, s.lab, s.login_time
        FROM sit_in s
        JOIN students st ON s.idno = st.idno
        WHERE s.status = 'active'
        ORDER BY s.login_time DESC
    ''')
    rows = cur.fetchall()
    conn.close()
    return rows


def get_sitin_records():
    conn = connect()
    cur  = conn.cursor()
    cur.execute('''
        SELECT r.id, r.idno, st.firstname, st.lastname, st.course, st.level,
               r.purpose, r.lab, r.login_time, r.logout_time
        FROM sit_in_records r
        JOIN students st ON r.idno = st.idno
        ORDER BY r.logout_time DESC
    ''')
    rows = cur.fetchall()
    conn.close()
    return rows


def get_sitin_stats():
    """
    Returns a dict with:
      total_students  - int
      currently_in    - int
      total_sitins    - int
      purpose_counts  - list of dicts [{'purpose': ..., 'cnt': ...}, ...]
      lab_counts      - list of dicts [{'lab': ..., 'cnt': ...}, ...]
    """
    conn = connect()
    cur  = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM students")
    total_students = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM sit_in WHERE status = 'active'")
    currently_in = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM sit_in_records")
    total_sitins = cur.fetchone()[0]

    # Purpose breakdown (combine active + records)
    cur.execute('''
        SELECT purpose, COUNT(*) as cnt FROM (
            SELECT purpose FROM sit_in
            UNION ALL
            SELECT purpose FROM sit_in_records
        ) GROUP BY purpose ORDER BY cnt DESC
    ''')
    purpose_counts = [{'purpose': row['purpose'], 'cnt': row['cnt']} for row in cur.fetchall()]

    # Lab breakdown
    cur.execute('''
        SELECT lab, COUNT(*) as cnt FROM (
            SELECT lab FROM sit_in
            UNION ALL
            SELECT lab FROM sit_in_records
        ) GROUP BY lab ORDER BY cnt DESC
    ''')
    lab_counts = [{'lab': row['lab'], 'cnt': row['cnt']} for row in cur.fetchall()]

    conn.close()

    return {
        'total_students': total_students,
        'currently_in':   currently_in,
        'total_sitins':   total_sitins,
        'purpose_counts': purpose_counts,  # always a list, never None/undefined
        'lab_counts':     lab_counts,
    }


# ── Announcements ─────────────────────────────────────────

def get_all_announcements():
    conn = connect()
    cur  = conn.cursor()
    cur.execute("SELECT * FROM announcements ORDER BY created_at DESC")
    rows = cur.fetchall()
    conn.close()
    return rows


def add_announcement(content, posted_by='CCS Admin'):
    return addrecord('announcements', content=content, posted_by=posted_by)


def delete_announcement(ann_id):
    return deleterecord('announcements', id=ann_id)


# ── Feedback ──────────────────────────────────────────────

def get_all_feedback():
    conn = connect()
    cur  = conn.cursor()
    cur.execute('''
        SELECT f.*, st.firstname, st.lastname
        FROM feedback f
        JOIN students st ON f.idno = st.idno
        ORDER BY f.created_at DESC
    ''')
    rows = cur.fetchall()
    conn.close()
    return rows


def add_feedback(idno, message, rating=5):
    return addrecord('feedback', idno=idno, message=message, rating=rating)


# ── Reservations ──────────────────────────────────────────

def get_all_reservations():
    conn = connect()
    cur  = conn.cursor()
    cur.execute('''
        SELECT r.*, st.firstname, st.lastname, st.course
        FROM reservations r
        JOIN students st ON r.idno = st.idno
        ORDER BY r.created_at DESC
    ''')
    rows = cur.fetchall()
    conn.close()
    return rows


def get_student_reservations(idno):
    conn = connect()
    cur  = conn.cursor()
    cur.execute(
        "SELECT * FROM reservations WHERE idno = ? ORDER BY created_at DESC",
        (idno,)
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def update_reservation_status(res_id, status):
    return updaterecord('reservations', 'id', res_id, status=status)