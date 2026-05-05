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
            points            INTEGER DEFAULT 0,
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
            pc_number  VARCHAR(10)  DEFAULT NULL,
            date       DATE         NOT NULL,
            time_slot  VARCHAR(50)  NOT NULL,
            purpose    VARCHAR(100) NOT NULL,
            status     VARCHAR(20)  DEFAULT 'pending',
            created_at TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (idno) REFERENCES students(idno)
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key   VARCHAR(50) PRIMARY KEY,
            value TEXT NOT NULL
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS software (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        VARCHAR(100) NOT NULL,
            description TEXT,
            filename    VARCHAR(255),
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS notifications (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            idno       VARCHAR(20)  NOT NULL,
            type       VARCHAR(20)  NOT NULL DEFAULT 'info',
            title      VARCHAR(100) NOT NULL,
            message    TEXT         NOT NULL,
            is_read    INTEGER      DEFAULT 0,
            created_at TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (idno) REFERENCES students(idno)
        )
    ''')

    # ── Migrations — add columns if missing ──────────────────────────────────
    migrations = [
        "ALTER TABLE students ADD COLUMN profile_image VARCHAR(255)",
        "ALTER TABLE students ADD COLUMN remaining_session INTEGER DEFAULT 30",
        "ALTER TABLE students ADD COLUMN points INTEGER DEFAULT 0",
        "ALTER TABLE reservations ADD COLUMN pc_number VARCHAR(10) DEFAULT NULL",
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


# ── Generic CRUD ──────────────────────────────────────────────────────────────

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


# ── Students ──────────────────────────────────────────────────────────────────

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


def get_leaderboard():
    """Returns top students ordered by points descending."""
    conn = connect()
    cur  = conn.cursor()
    cur.execute('''
        SELECT idno, firstname, lastname, course, level, points,
               remaining_session
        FROM students
        ORDER BY points DESC, lastname ASC
        LIMIT 20
    ''')
    rows = cur.fetchall()
    conn.close()
    return rows


def add_points(idno, pts):
    """Add pts to a student's points total."""
    conn = connect()
    cur  = conn.cursor()
    try:
        cur.execute(
            "UPDATE students SET points = points + ? WHERE idno = ?",
            (pts, idno)
        )
        conn.commit()
        return cur.rowcount > 0
    except Exception as e:
        print("add_points error:", e)
        conn.rollback()
        return False
    finally:
        conn.close()


def set_points(idno, pts):
    """Set a student's points to an exact value."""
    return updaterecord('students', 'idno', idno, points=pts)


# ── Users (admin) ─────────────────────────────────────────────────────────────

def get_user_by_email(email):
    return getone('users', email=email)


# ── Sit-in ────────────────────────────────────────────────────────────────────

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
        cur.execute("SELECT * FROM sit_in WHERE id = ?", (sit_id,))
        row = cur.fetchone()
        if not row:
            return False
        cur.execute(
            "INSERT INTO sit_in_records (idno, purpose, lab, login_time) VALUES (?, ?, ?, ?)",
            (row['idno'], row['purpose'], row['lab'], row['login_time'])
        )
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


def get_student_sitin_history(idno):
    """Returns completed sit-in records for a specific student."""
    conn = connect()
    cur  = conn.cursor()
    cur.execute('''
        SELECT r.id, r.purpose, r.lab, r.login_time, r.logout_time
        FROM sit_in_records r
        WHERE r.idno = ?
        ORDER BY r.logout_time DESC
    ''', (idno,))
    rows = cur.fetchall()
    conn.close()
    return rows


def get_sitin_stats():
    conn = connect()
    cur  = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM students")
    total_students = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM sit_in WHERE status = 'active'")
    currently_in = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM sit_in_records")
    total_sitins = cur.fetchone()[0]

    cur.execute('''
        SELECT purpose, COUNT(*) as cnt FROM (
            SELECT purpose FROM sit_in
            UNION ALL
            SELECT purpose FROM sit_in_records
        ) GROUP BY purpose ORDER BY cnt DESC
    ''')
    purpose_counts = [{'purpose': row['purpose'], 'cnt': row['cnt']} for row in cur.fetchall()]

    cur.execute('''
        SELECT lab, COUNT(*) as cnt FROM (
            SELECT lab FROM sit_in
            UNION ALL
            SELECT lab FROM sit_in_records
        ) GROUP BY lab ORDER BY cnt DESC
    ''')
    lab_counts = [{'lab': row['lab'], 'cnt': row['cnt']} for row in cur.fetchall()]

    # Daily sit-in counts for the last 7 days
    cur.execute('''
        SELECT DATE(logout_time) as day, COUNT(*) as cnt
        FROM sit_in_records
        WHERE logout_time >= DATE('now', '-7 days')
        GROUP BY DATE(logout_time)
        ORDER BY day ASC
    ''')
    daily_counts = [{'day': row['day'], 'cnt': row['cnt']} for row in cur.fetchall()]

    conn.close()

    return {
        'total_students': total_students,
        'currently_in':   currently_in,
        'total_sitins':   total_sitins,
        'purpose_counts': purpose_counts,
        'lab_counts':     lab_counts,
        'daily_counts':   daily_counts,
    }




def get_student_sitin_summary(idno):
    """Returns sit-in summary stats for a student."""
    conn = connect()
    cur  = conn.cursor()
    cur.execute("""
        SELECT
            COUNT(*) as total_sessions,
            ROUND(SUM((strftime('%s', logout_time) - strftime('%s', login_time)) / 3600.0), 2) as total_hours,
            ROUND(AVG((strftime('%s', logout_time) - strftime('%s', login_time)) / 60.0), 1) as avg_duration_mins,
            MAX((strftime('%s', logout_time) - strftime('%s', login_time)) / 60.0) as longest_session_mins
        FROM sit_in_records
        WHERE idno = ?
    """, (idno,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else {}


def get_student_sessions_table(idno):
    """Returns detailed session rows for a student with duration."""
    conn = connect()
    cur  = conn.cursor()
    cur.execute("""
        SELECT
            r.id,
            r.lab,
            r.purpose,
            r.login_time,
            r.logout_time,
            ROUND((strftime('%s', r.logout_time) - strftime('%s', r.login_time)) / 60.0, 1) as duration_mins,
            res.pc_number
        FROM sit_in_records r
        LEFT JOIN reservations res
            ON res.idno = r.idno
            AND res.lab  = r.lab
            AND DATE(res.date) = DATE(r.login_time)
            AND res.status = 'approved'
        WHERE r.idno = ?
        ORDER BY r.login_time DESC
    """, (idno,))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_reservation_setting():
    """Get global reservation enabled/disabled setting."""
    conn = connect()
    cur  = conn.cursor()
    try:
        cur.execute("SELECT value FROM settings WHERE key = 'reservation_enabled'")
        row = cur.fetchone()
        return row['value'] == '1' if row else True
    except:
        return True
    finally:
        conn.close()


def set_reservation_setting(enabled: bool):
    """Enable or disable reservations globally."""
    conn = connect()
    cur  = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO settings (key, value) VALUES ('reservation_enabled', ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """, ('1' if enabled else '0',))
        conn.commit()
        return True
    except Exception as e:
        print("set_reservation_setting error:", e)
        return False
    finally:
        conn.close()


def get_all_software():
    """Get all uploaded software entries."""
    conn = connect()
    cur  = conn.cursor()
    cur.execute("SELECT * FROM software ORDER BY created_at DESC")
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_software(name, description, filename):
    return addrecord('software', name=name, description=description, filename=filename)


def delete_software(sw_id):
    return deleterecord('software', id=sw_id)


# ── Announcements ─────────────────────────────────────────────────────────────

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


# ── Feedback ──────────────────────────────────────────────────────────────────

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


# ── Reservations ──────────────────────────────────────────────────────────────

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


def get_reserved_pcs(lab, date):
    """Returns list of pc_numbers that are reserved/pending for a lab on a date."""
    conn = connect()
    cur  = conn.cursor()
    cur.execute('''
        SELECT pc_number FROM reservations
        WHERE lab = ? AND date = ? AND status IN ('pending', 'approved')
        AND pc_number IS NOT NULL
    ''', (lab, date))
    rows = cur.fetchall()
    conn.close()
    return [r['pc_number'] for r in rows]




def get_testimonials(limit=10):
    """Get approved/public feedback as testimonials."""
    conn = connect()
    cur  = conn.cursor()
    cur.execute("""
        SELECT f.*, st.firstname, st.lastname, st.course, st.profile_image
        FROM feedback f
        JOIN students st ON f.idno = st.idno
        WHERE f.rating >= 4
        ORDER BY f.rating DESC, f.created_at DESC
        LIMIT ?
    """, (limit,))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_ai_recommendations(idno):
    """Generate simple rule-based AI recommendations for a student."""
    conn = connect()
    cur  = conn.cursor()
    # Most used lab
    cur.execute("""
        SELECT lab, COUNT(*) as cnt FROM sit_in_records
        WHERE idno = ? GROUP BY lab ORDER BY cnt DESC LIMIT 1
    """, (idno,))
    fav_lab = cur.fetchone()
    # Most used purpose
    cur.execute("""
        SELECT purpose, COUNT(*) as cnt FROM sit_in_records
        WHERE idno = ? GROUP BY purpose ORDER BY cnt DESC LIMIT 1
    """, (idno,))
    fav_purpose = cur.fetchone()
    # Avg session duration
    cur.execute("""
        SELECT ROUND(AVG((strftime('%s',logout_time)-strftime('%s',login_time))/60.0),1) as avg_mins
        FROM sit_in_records WHERE idno = ?
    """, (idno,))
    avg_row = cur.fetchone()
    # Busiest day
    cur.execute("""
        SELECT strftime('%w', login_time) as dow, COUNT(*) as cnt
        FROM sit_in_records WHERE idno = ?
        GROUP BY dow ORDER BY cnt DESC LIMIT 1
    """, (idno,))
    busy_day = cur.fetchone()
    conn.close()

    days = ['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday']
    recs = []

    if fav_lab:
        recs.append({
            'icon': '🏫',
            'title': f'Your preferred lab is Lab {fav_lab["lab"]}',
            'tip': f'You visit Lab {fav_lab["lab"]} most often ({fav_lab["cnt"]} times). Consider reserving your usual seat in advance.'
        })
    if fav_purpose:
        recs.append({
            'icon': '💻',
            'title': f'You mostly work on {fav_purpose["purpose"]}',
            'tip': f'Check the Software page for tools related to {fav_purpose["purpose"]} that the admin has uploaded for download.'
        })
    if avg_row and avg_row['avg_mins']:
        avg = float(avg_row['avg_mins'])
        if avg < 30:
            recs.append({'icon': '⏱', 'title': 'Short sessions detected',
                'tip': 'Your average session is under 30 minutes. Consider booking longer slots to maximize your lab time.'})
        else:
            recs.append({'icon': '⏱', 'title': f'Good session length: {avg} min avg',
                'tip': 'You make good use of your lab time. Keep it up!'})
    if busy_day:
        day_name = days[int(busy_day['dow'])]
        recs.append({'icon': '📅', 'title': f'You are most active on {day_name}s',
            'tip': f'Labs tend to be busier on {day_name}s. Try reserving your PC early to guarantee your spot.'})
    if not recs:
        recs.append({'icon': '💡', 'title': 'Start using the lab!',
            'tip': 'No sit-in data yet. Visit the lab and start logging sessions to get personalized recommendations.'})
    return recs


def get_calendar_reservations(lab, year, month):
    """Get all reservations for a lab in a given month for calendar view."""
    conn = connect()
    cur  = conn.cursor()
    cur.execute("""
        SELECT r.date, r.time_slot, r.pc_number, r.status, r.purpose,
               st.firstname, st.lastname, r.idno
        FROM reservations r
        JOIN students st ON r.idno = st.idno
        WHERE r.lab = ?
          AND strftime('%Y', r.date) = ?
          AND strftime('%m', r.date) = ?
          AND r.status IN ('pending','approved')
        ORDER BY r.date, r.time_slot
    """, (lab, str(year), str(month).zfill(2)))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Notifications ─────────────────────────────────────────────────────────────

def get_student_notifications(idno):
    conn = connect()
    cur  = conn.cursor()
    cur.execute('''
        SELECT * FROM notifications
        WHERE idno = ?
        ORDER BY created_at DESC
        LIMIT 30
    ''', (idno,))
    rows = cur.fetchall()
    conn.close()
    return rows


def get_unread_count(idno):
    conn = connect()
    cur  = conn.cursor()
    cur.execute(
        "SELECT COUNT(*) FROM notifications WHERE idno = ? AND is_read = 0",
        (idno,)
    )
    count = cur.fetchone()[0]
    conn.close()
    return count


def add_notification(idno, title, message, notif_type='info'):
    return addrecord('notifications',
                     idno=idno,
                     type=notif_type,
                     title=title,
                     message=message,
                     is_read=0)


def mark_notification_read(notif_id, idno):
    conn = connect()
    cur  = conn.cursor()
    try:
        cur.execute(
            "UPDATE notifications SET is_read = 1 WHERE id = ? AND idno = ?",
            (notif_id, idno)
        )
        conn.commit()
        return cur.rowcount > 0
    except Exception as e:
        print("mark_notification_read error:", e)
        return False
    finally:
        conn.close()


def mark_all_notifications_read(idno):
    conn = connect()
    cur  = conn.cursor()
    try:
        cur.execute(
            "UPDATE notifications SET is_read = 1 WHERE idno = ?",
            (idno,)
        )
        conn.commit()
        return True
    except Exception as e:
        print("mark_all_notifications_read error:", e)
        return False
    finally:
        conn.close()


def delete_notifications_by_content(message_text):
    """Delete all notifications whose message matches the given text.
    Used when an announcement is deleted — removes it from all student panels."""
    conn = connect()
    cur  = conn.cursor()
    try:
        cur.execute(
            "DELETE FROM notifications WHERE message = ? AND title = 'New Announcement'",
            (message_text,)
        )
        conn.commit()
        return cur.rowcount
    except Exception as e:
        print("delete_notifications_by_content error:", e)
        conn.rollback()
        return 0
    finally:
        conn.close()