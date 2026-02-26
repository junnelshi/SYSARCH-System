from flask import Flask, render_template, redirect, url_for, request, session, flash
from dbhelper import init_database, addrecord, recordexists, get_student_by_idno, get_user_by_email
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "ccs-sitin-secret-change-this")

init_database()


# ─────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────

def is_logged_in():
    return 'student_id' in session

def is_admin():
    return session.get('role') == 'admin'


# ─────────────────────────────────────────────
#  ROUTES
# ─────────────────────────────────────────────

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

        # ── Check admin (users table uses email) ──
        admin = get_user_by_email(idno)  # admin types their email in the ID field
        if admin and check_password_hash(admin['password'], password):
            session['student_id']        = admin['email']
            session['student_firstname'] = admin['name']
            session['student_lastname']  = ''
            session['role']              = 'admin'
            return redirect(url_for('dashboard'))

        # ── Check student ──
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


@app.route('/dashboard')
def dashboard():
    if not is_logged_in():
        return redirect(url_for('login'))
    return render_template('dashboard.html')





if __name__ == '__main__':
    app.run(debug=True)