from functools import wraps
from flask import redirect, url_for, session, flash
import sqlite3

def get_db():
    db = sqlite3.connect('prek_billing.db')
    db.row_factory = sqlite3.Row
    return db

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        
        db = get_db()
        user = db.execute('SELECT username FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        db.close()
        
        # Store the username in the session or pass it to the view function
        return f(user=user, *args, **kwargs)
    
    return decorated_function

def get_student_info(student_id):
    db = get_db()
    student = db.execute('SELECT * FROM Students WHERE StudentID = ?', (student_id,)).fetchone()

    # Handle case where student is not found
    if student is None:
        flash('Student not found.', 'error')
        return redirect(url_for('index'))

    # Access the ParentID using dictionary-style access
    parent = db.execute('SELECT * FROM Parents WHERE ParentID = ?', (student['ParentID'],)).fetchone()
    return student, parent