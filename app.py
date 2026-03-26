from flask import Flask, render_template, redirect, url_for, request, session, flash, jsonify
from dbhelper import (
    init_database, addrecord, recordexists, recordexists_exclude,
    get_student_by_idno, get_user_by_email,
    get_all_students, search_students, updaterecord, deleterecord, reset_all_sessions,
    get_active_sitin, is_student_sitting_in, sitin_student, logout_student,
    get_sitin_records, get_sitin_stats,
    get_all_announcements, add_announcement, delete_announcement,
    get_all_feedback, add_feedback,
    get_all_reservations, get_student_reservations, update_reservation_status,
    addrecord
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "ccs-sitin-secret-change-this")

UPLOAD_FOLDER = os.path.join('static', 'images', 'profiles')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}

init_database()


# ── Helpers ───────────────────────────────────────────────

def is_logged_in():
    return 'student_id' in session

def is_admin():
    return session.get('role') == 'admin'

def admin_required():
    if not is_logged_in() or not is_admin():
        flash('Admin access required.', 'error')
        return redirect(url_for('login'))

def login_required():
    if not is_logged_in():
        return redirect(url_for('login'))


# ── Auth routes ───────────────────────────────────────────

@app.route('/')
def index():
    if is_logged_in():
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if is_logged_in():
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        idno     = request.form.get('idno', '').strip()
        password = request.form.get('password', '').strip()

        if not idno or not password:
            flash('Please fill in all fields.', 'error')
            return redirect(url_for('login'))

        admin = get_user_by_email(idno)
        if admin and check_password_hash(admin['password'], password):
            session['student_id']        = admin['email']
            session['student_firstname'] = admin['name']
            session['student_lastname']  = ''
            session['role']              = 'admin'
            return redirect(url_for('dashboard'))

        student = get_student_by_idno(idno)
        if student and check_password_hash(student['password'], password):
            session['student_id']        = student['idno']
            session['student_firstname'] = student['firstname']
            session['student_lastname']  = student['lastname']
            session['student_course']    = student['course']
            session['student_level']     = student['level']
            session['role']              = 'student'
            return redirect(url_for('dashboard'))

        flash('Invalid ID number or password.', 'error')
        return redirect(url_for('login'))

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if is_logged_in():
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        idno       = request.form.get('idno', '').strip()
        lastname   = request.form.get('lastname', '').strip()
        firstname  = request.form.get('firstname', '').strip()
        middlename = request.form.get('middlename', '').strip()
        level      = request.form.get('level', '').strip()
        password   = request.form.get('password', '').strip()
        confirm    = request.form.get('confirm_password', '').strip()
        email      = request.form.get('email', '').strip()
        course     = request.form.get('course', '').strip()
        address    = request.form.get('address', '').strip()

        if not all([idno, lastname, firstname, level, password, confirm, email, course]):
            flash('Please fill in all required fields.', 'error')
            return redirect(url_for('register'))

        if password != confirm:
            flash('Passwords do not match.', 'error')
            return redirect(url_for('register'))

        if recordexists('students', idno=idno):
            flash('A student with this ID number already exists.', 'error')
            return redirect(url_for('register'))

        if recordexists('students', email=email):
            flash('A student with this email already exists.', 'error')
            return redirect(url_for('register'))

        if addrecord('students',
                     idno=idno, lastname=lastname, firstname=firstname,
                     middlename=middlename, course=course, level=level,
                     email=email, address=address,
                     password=generate_password_hash(password)):
            flash('Registration successful! You can now log in.', 'success')
            return redirect(url_for('login'))

        flash('Registration failed. Please try again.', 'error')
        return redirect(url_for('register'))

    return render_template('register.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


# ── Dashboard ─────────────────────────────────────────────

@app.route('/dashboard')
def dashboard():
    if not is_logged_in():
        return redirect(url_for('login'))

    if is_admin():
        stats         = get_sitin_stats()
        announcements = get_all_announcements()
        return render_template('admin_dashboard.html',
                               stats=stats,
                               announcements=announcements)

    # Student dashboard
    student = get_student_by_idno(session['student_id'])
    announcements = get_all_announcements()
    reservations  = get_student_reservations(session['student_id'])
    return render_template('student_profile.html',
                           student=student,
                           announcements=announcements,
                           reservations=reservations)


# ── Admin: Announcements ──────────────────────────────────

@app.route('/admin/announcement/add', methods=['POST'])
def add_announcement_route():
    r = admin_required()
    if r: return r
    content = request.form.get('content', '').strip()
    if content:
        add_announcement(content)
    return redirect(url_for('dashboard'))


@app.route('/admin/announcement/delete/<int:ann_id>')
def delete_announcement_route(ann_id):
    r = admin_required()
    if r: return r
    delete_announcement(ann_id)
    return redirect(url_for('dashboard'))


# ── Admin: Search student (AJAX) ──────────────────────────

@app.route('/admin/search_student')
def search_student():
    r = admin_required()
    if r: return r
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify([])
    students = search_students(query)
    result = []
    for s in students:
        result.append({
            'idno': s['idno'],
            'name': f"{s['firstname']} {s['lastname']}",
            'course': s['course'],
            'level': s['level'],
            'remaining_session': s['remaining_session'],
            'already_in': is_student_sitting_in(s['idno'])
        })
    return jsonify(result)


# ── Admin: Sit-in ─────────────────────────────────────────

@app.route('/admin/sitin', methods=['POST'])
def admin_sitin():
    r = admin_required()
    if r: return r
    idno    = request.form.get('idno', '').strip()
    purpose = request.form.get('purpose', '').strip()
    lab     = request.form.get('lab', '').strip()

    if not all([idno, purpose, lab]):
        flash('All fields are required.', 'error')
        return redirect(url_for('dashboard'))

    student = get_student_by_idno(idno)
    if not student:
        flash('Student not found.', 'error')
        return redirect(url_for('dashboard'))

    if student['remaining_session'] <= 0:
        flash('Student has no remaining sessions.', 'error')
        return redirect(url_for('dashboard'))

    if is_student_sitting_in(idno):
        flash('Student is already sitting in.', 'error')
        return redirect(url_for('dashboard'))

    if sitin_student(idno, purpose, lab):
        flash(f'{student["firstname"]} {student["lastname"]} has been logged in.', 'success')
    else:
        flash('Failed to log student in.', 'error')

    return redirect(url_for('current_sitin'))


# ── Admin: Current Sit-in ─────────────────────────────────

@app.route('/admin/current_sitin')
def current_sitin():
    r = admin_required()
    if r: return r
    rows = get_active_sitin()
    return render_template('current_sitin.html', sitins=rows)


@app.route('/admin/logout_student/<int:sit_id>')
def admin_logout_student(sit_id):
    r = admin_required()
    if r: return r
    if logout_student(sit_id):
        flash('Student logged out successfully.', 'success')
    else:
        flash('Failed to log out student.', 'error')
    return redirect(url_for('current_sitin'))


# ── Admin: Students list ──────────────────────────────────

@app.route('/admin/students')
def students_list():
    r = admin_required()
    if r: return r
    students = get_all_students()
    return render_template('students_list.html', students=students)


@app.route('/admin/students/add', methods=['POST'])
def add_student():
    r = admin_required()
    if r: return r
    idno      = request.form.get('idno', '').strip()
    lastname  = request.form.get('lastname', '').strip()
    firstname = request.form.get('firstname', '').strip()
    course    = request.form.get('course', '').strip()
    level     = request.form.get('level', '').strip()
    email     = request.form.get('email', '').strip()

    if not all([idno, lastname, firstname, course, level, email]):
        flash('All fields are required.', 'error')
        return redirect(url_for('students_list'))

    if recordexists('students', idno=idno):
        flash('Student ID already exists.', 'error')
        return redirect(url_for('students_list'))

    if addrecord('students', idno=idno, lastname=lastname, firstname=firstname,
                 middlename='', course=course, level=level,
                 email=email, address='',
                 password=generate_password_hash('student123')):
        flash('Student added successfully.', 'success')
    else:
        flash('Failed to add student.', 'error')
    return redirect(url_for('students_list'))


@app.route('/admin/students/edit/<idno>', methods=['POST'])
def edit_student(idno):
    r = admin_required()
    if r: return r
    lastname  = request.form.get('lastname', '').strip()
    firstname = request.form.get('firstname', '').strip()
    course    = request.form.get('course', '').strip()
    level     = request.form.get('level', '').strip()
    email     = request.form.get('email', '').strip()
    remaining = request.form.get('remaining_session', '30').strip()

    updaterecord('students', 'idno', idno,
                 lastname=lastname, firstname=firstname,
                 course=course, level=level, email=email,
                 remaining_session=int(remaining))
    flash('Student updated.', 'success')
    return redirect(url_for('students_list'))


@app.route('/admin/students/delete/<idno>')
def delete_student(idno):
    r = admin_required()
    if r: return r
    deleterecord('students', idno=idno)
    flash('Student deleted.', 'success')
    return redirect(url_for('students_list'))


@app.route('/admin/students/reset_sessions')
def reset_sessions():
    r = admin_required()
    if r: return r
    reset_all_sessions()
    flash('All student sessions have been reset to 30.', 'success')
    return redirect(url_for('students_list'))


# ── Admin: Sit-in records ─────────────────────────────────

@app.route('/admin/sitin_records')
def sitin_records():
    r = admin_required()
    if r: return r
    records = get_sitin_records()
    return render_template('sitin_records.html', records=records)


# ── Admin: Sit-in reports ─────────────────────────────────

@app.route('/admin/sitin_reports')
def sitin_reports():
    r = admin_required()
    if r: return r
    stats = get_sitin_stats()
    return render_template('sitin_reports.html', stats=stats)


# ── Admin: Feedback reports ───────────────────────────────

@app.route('/admin/feedback_reports')
def feedback_reports():
    r = admin_required()
    if r: return r
    feedbacks = get_all_feedback()
    return render_template('feedback_reports.html', feedbacks=feedbacks)


# ── Admin: Reservations ───────────────────────────────────

@app.route('/admin/reservations')
def admin_reservations():
    r = admin_required()
    if r: return r
    reservations = get_all_reservations()
    return render_template('admin_reservations.html', reservations=reservations)


@app.route('/admin/reservations/update/<int:res_id>/<status>')
def update_reservation(res_id, status):
    r = admin_required()
    if r: return r
    if status in ('approved', 'rejected'):
        update_reservation_status(res_id, status)
        flash(f'Reservation {status}.', 'success')
    return redirect(url_for('admin_reservations'))


# ── Student: Update Profile ───────────────────────────────

@app.route('/student/update_profile', methods=['POST'])
def update_profile():
    rr = login_required()
    if rr: return rr

    idno       = session['student_id']
    firstname  = request.form.get('firstname', '').strip()
    lastname   = request.form.get('lastname', '').strip()
    middlename = request.form.get('middlename', '').strip()
    email      = request.form.get('email', '').strip()
    address    = request.form.get('address', '').strip()
    course     = request.form.get('course', '').strip()
    level      = request.form.get('level', '').strip()
    new_pw     = request.form.get('new_password', '').strip()
    confirm_pw = request.form.get('confirm_password', '').strip()
    remove_photo = request.form.get('remove_photo', '0')

    # Check email uniqueness (exclude current student)
    if recordexists_exclude('students', 'email', email, 'idno', idno):
        flash('That email is already used by another account.', 'error')
        return redirect(url_for('dashboard'))

    # Build update fields
    update_fields = dict(
        firstname=firstname, lastname=lastname, middlename=middlename,
        email=email, address=address, course=course, level=level
    )

    # Password change
    if new_pw:
        if new_pw != confirm_pw:
            flash('Passwords do not match.', 'error')
            return redirect(url_for('dashboard'))
        update_fields['password'] = generate_password_hash(new_pw)

    # Handle photo upload
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    file = request.files.get('profile_image')
    if remove_photo == '1':
        update_fields['profile_image'] = None
    elif file and file.filename and allowed_file(file.filename):
        filename = secure_filename(f"{idno}_{file.filename}")
        file.save(os.path.join(UPLOAD_FOLDER, filename))
        update_fields['profile_image'] = filename

    updaterecord('students', 'idno', idno, **update_fields)

    # Update session
    session['student_firstname'] = firstname
    session['student_lastname']  = lastname
    session['student_course']    = course
    session['student_level']     = level

    flash('Profile updated successfully!', 'success')
    return redirect(url_for('dashboard'))


# ── Student: Feedback ─────────────────────────────────────

@app.route('/student/feedback', methods=['POST'])
def submit_feedback():
    rr = login_required()
    if rr: return rr
    message = request.form.get('message', '').strip()
    rating  = request.form.get('rating', '5').strip()
    if message:
        add_feedback(session['student_id'], message, int(rating))
        flash('Feedback submitted. Thank you!', 'success')
    return redirect(url_for('dashboard'))


# ── Student: Reservation ──────────────────────────────────

@app.route('/student/reserve', methods=['POST'])
def student_reserve():
    rr = login_required()
    if rr: return rr
    lab       = request.form.get('lab', '').strip()
    date      = request.form.get('date', '').strip()
    time_slot = request.form.get('time_slot', '').strip()
    purpose   = request.form.get('purpose', '').strip()

    if not all([lab, date, time_slot, purpose]):
        flash('All fields are required.', 'error')
        return redirect(url_for('dashboard'))

    if addrecord('reservations',
                 idno=session['student_id'], lab=lab,
                 date=date, time_slot=time_slot, purpose=purpose):
        flash('Reservation submitted for approval.', 'success')
    else:
        flash('Failed to submit reservation.', 'error')
    return redirect(url_for('dashboard'))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)