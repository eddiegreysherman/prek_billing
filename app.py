from functools import wraps
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import check_password_hash
from utils import get_db, login_required, get_student_info

app = Flask(__name__)
app.secret_key = 'SECRET'

####################################
##
##        INDEX/ALL STUDENTS
##
#####################################

@app.route('/')
@login_required
def index(user):
    db = get_db()
    students = db.execute('SELECT * FROM Students WHERE EnrollmentStatus = "Active"').fetchall()
    db.close()
    context = {
        'username': user['username'],
        'students': students
    }
    return render_template('students.html', **context)

####################################
##
##        LOGIN ROUTE
##
#####################################

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        user = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        db.close()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            flash('Logged in successfully!', 'success')
            return redirect(url_for('index'))
        flash('Invalid username or password', 'error')
    return render_template('new_login.html')

####################################
##
##        LOGOUT ROUTE
##
#####################################

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('You have been logged out', 'success')
    return redirect(url_for('login'))

#########################################
##
##        REGISTER - NEW STUDENT/PARENT
##
#########################################

@app.route('/register', methods=['GET'])
@login_required
def show_register_form(user):
    return render_template('register.html', username=user['username'])

####################################
##
##        PROCESS NEW STUDENTS
##
#####################################

@app.route('/process_registration', methods=['POST'])
@login_required
def process_registration(user):
    # Extract form data
    parent_data = {
        'FirstName': request.form['parent_first_name'],
        'LastName': request.form['parent_last_name'],
        'Address': request.form['address'],
        'City': request.form['city'],
        'State': request.form['state'],
        'ZipCode': request.form['zipcode'],
        'Email': request.form['email'],
        'Phone': request.form['phone']
    }

    student_data = {
        'FirstName': request.form['student_first_name'],
        'LastName': request.form['student_last_name'],
        'EnrollmentStatus': request.form['enrollment_status']
    }

    # Insert parent data into database
    db = get_db()
    cursor = db.cursor()
    cursor.execute('''
        INSERT INTO Parents (FirstName, LastName, Address, City, State, ZipCode, Email, Phone)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (parent_data['FirstName'], parent_data['LastName'], parent_data['Address'],
          parent_data['City'], parent_data['State'], parent_data['ZipCode'],
          parent_data['Email'], parent_data['Phone']))

    parent_id = cursor.lastrowid

    # Insert student data into database
    cursor.execute('''
        INSERT INTO Students (ParentID, FirstName, LastName, EnrollmentStatus)
        VALUES (?, ?, ?, ?)
    ''', (parent_id, student_data['FirstName'], student_data['LastName'], student_data['EnrollmentStatus']))

    db.commit()
    db.close()

    flash('New Student Added Successfully!', 'success')
    return redirect(url_for('index'))

####################################
##
##        MANAGE STUDENT BY ID
##
#####################################

@app.route('/manage/<int:student_id>')
@login_required
def manage(user, student_id):
    # Fetch student data from the database using the student_id
    db = get_db()
    student = db.execute('SELECT * FROM Students WHERE StudentID = ?', (student_id,)).fetchone()

    # Handle case where student is not found
    if student is None:
        flash('Student not found.', 'error')
        return redirect(url_for('index'))

    # Access the ParentID using dictionary-style access
    parent = db.execute('SELECT * FROM Parents WHERE ParentID = ?', (student['ParentID'],)).fetchone()

    # get all payments entered for this student
    payments = db.execute('SELECT * FROM Payments WHERE StudentID = ?', (student_id,)).fetchall()
    db.close()
    # Set the total for all payments entered
    total = 0;
    for payment in payments:
        total += payment['Amount']

    context = {
        'parent': parent,
        'student': student,
        'payments': payments,
        'total': total
    }

    return render_template('manage.html', username=user['username'], **context, datetime=datetime)

####################################
##
##        PAYMENT ENTRY BY ID
##
#####################################

@app.route('/enter_payment/<int:student_id>')
@login_required
def enter_payment(user, student_id):
    db = get_db()
    student = db.execute('SELECT * FROM Students WHERE StudentID = ?', (student_id,)).fetchone()
    db.close()
    return render_template('enter_payment.html', username=user['username'], student=student)

####################################
##
##        PROCESS PAYMENT BY ID
##
#####################################

@app.route('/process_payment/<int:student_id>', methods=['POST'])
@login_required
def process_payment(user, student_id):
    payment_data = {
        'payment_amount': request.form['payment_amount'],
        'payment_date': request.form['payment_date']
    }

    try:
        payment_data['payment_amount'] = "{:.2f}".format(float(payment_data['payment_amount']))  # Convert to float to handle decimal values
    except ValueError:
        # Handle the case where the input is not a valid number
        flash('Invalid amount entered. Please enter a valid number.', 'error')
        return redirect(url_for('enter_payment', student_id=student_id))
    
    db = get_db()
    db.execute('INSERT INTO Payments (StudentID, Amount, DatePaid) VALUES (?, ?, ?)',(student_id, payment_data['payment_amount'], payment_data['payment_date']))
    db.commit()
    db.close()
    flash('New Payment Added Successfully!', 'success')
    return redirect(url_for('manage', student_id=student_id))

####################################
##
##        DELETE PAYMENT BY ID
##
#####################################

@app.route('/delete_payment/<int:student_id>/<int:payment_id>', methods=['POST'])
@login_required
def delete_payment(user, payment_id, student_id):
    db = get_db()
    db.execute('DELETE FROM Payments WHERE PaymentID = ?', (payment_id,))
    db.commit()
    db.close()
    flash('Payment Deleted Successfully!', 'success')
    return redirect(url_for('manage', student_id=student_id))

####################################
##
##        EDIT PAYMENT BY ID
##
#####################################
@app.route('/edit_payment/<int:student_id>/<int:payment_id>', methods=['GET', 'POST'])
@login_required
def edit_payment(user, payment_id, student_id):
    db = get_db()
    payment = db.execute('SELECT * FROM Payments WHERE PaymentID = ?', (payment_id,)).fetchone()
    student = db.execute('SELECT * FROM Students WHERE StudentID = ?', (student_id,)).fetchone()
    db.close()

    return render_template('edit_payment.html', username=user['username'], student=student, payment=payment)

####################################
##
##        UPDATE PAYMENT BY ID
##
#####################################
@app.route('/update_payment/<int:student_id>/<int:payment_id>', methods=['POST'])
@login_required
def update_payment(user, payment_id, student_id):
    payment_data = {
        'Amount': request.form['payment_amount'],
        'DatePaid': request.form['payment_date']
    }

    try:
        payment_data['Amount'] = "{:.2f}".format(float(payment_data['Amount']))  # Convert to float to handle decimal values
    except ValueError:
        # Handle the case where the input is not a valid number
        flash('Invalid amount entered. Please enter a valid number.', 'error')
        return redirect(url_for('edit_payment', student_id=student_id, payment_id=payment_id))
    
    db = get_db()
    db.execute('UPDATE Payments SET Amount = ?, DatePaid = ? WHERE PaymentID = ?', (payment_data['Amount'], payment_data['DatePaid'], payment_id,))
    db.commit()
    db.close()
    flash('Payment Updated Successfully!', 'success')
    return redirect(url_for('manage', student_id=student_id))

####################################
##
##        Edit Student Info
##
#####################################
@app.route('/edit_student/<int:student_id>')
@login_required
def edit_student(user, student_id):
    # Fetch student data from the database using the student_id
    db = get_db()
    student = db.execute('SELECT * FROM Students WHERE StudentID = ?', (student_id,)).fetchone()

    # Handle case where student is not found
    if student is None:
        flash('Student not found.', 'error')
        return redirect(url_for('index'))

    # Access the ParentID using dictionary-style access
    parent = db.execute('SELECT * FROM Parents WHERE ParentID = ?', (student['ParentID'],)).fetchone()
    db.close()
    context = {
            'parent': parent,
            'student': student
        }

    return render_template('edit_student.html', username=user['username'], **context)



####################################
##
##        UPDATE Student Info
##
#####################################
@app.route('/update_student/<int:student_id>', methods=['POST'])
@login_required
def update_student(user, student_id):
    # Extract form data
    parent_data = {
        'FirstName': request.form['parent_first_name'],
        'LastName': request.form['parent_last_name'],
        'Address': request.form['address'],
        'City': request.form['city'],
        'State': request.form['state'],
        'ZipCode': request.form['zipcode'],
        'Email': request.form['email'],
        'Phone': request.form['phone']
    }

    student_data = {
        'FirstName': request.form['student_first_name'],
        'LastName': request.form['student_last_name'],
        'EnrollmentStatus': request.form['enrollment_status']
    }

    db = get_db()
    student = db.execute('SELECT * FROM Students WHERE StudentID = ?', (student_id,)).fetchone()
    db.execute('''
        UPDATE Parents
        SET FirstName = ?,
            LastName = ?,
            Address = ?,
            City = ?,
            State = ?,
            ZipCode = ?,
            Email = ?,
            Phone = ?
        WHERE ParentID = ?
        ''', (parent_data['FirstName'],
              parent_data['LastName'],
              parent_data['Address'],
              parent_data['City'],
              parent_data['State'],
              parent_data['ZipCode'],
              parent_data['Email'],
              parent_data['Phone'],
              student['ParentID'],))
    db.execute('''
            UPDATE Students
            SET FirstName = ?,
                LastName = ?,
                EnrollmentStatus = ?
            WHERE StudentID = ?
               ''', (student_data['FirstName'], student_data['LastName'], student_data['EnrollmentStatus'], student_id,))
    db.commit()
    db.close()
    flash('Student Information Updated Successfully!', 'success')
    return redirect(url_for('manage', student_id=student_id))

####################################
##
##        Billing/invoicing
##
#####################################

@app.route('/bill_student/<int:student_id>', methods=['GET'])
@login_required
def bill_student(user, student_id):
    db = get_db()
    student = db.execute('SELECT * FROM Students WHERE StudentID = ?', (student_id,)).fetchone()
    return render_template('bill_student.html', student=student)

@app.route('/generate_invoice/<int:student_id>', methods=['POST'])
@login_required
def generate_invoice(user, student_id):
    db = get_db()

    try:
        amount = "{:.2f}".format(float(request.form['bill_amount']))  # Convert to float to handle decimal values
    except ValueError:
        # Handle the case where the input is not a valid number
        flash('Invalid amount entered. Please enter a valid number.', 'error')
        return redirect(url_for('bill_student', student_id=student_id))
    
    due_date = request.form['due_date']
    db.execute('INSERT INTO Invoices(StudentID, AmountBilled, DueDate) VALUES(?, ?, ?)', (student_id, amount, due_date,))
    db.commit()
    invoice = db.execute('SELECT * FROM Invoices ORDER BY InvoiceID DESC LIMIT 1').fetchone()
    student = db.execute('SELECT * FROM Students WHERE StudentID = ?', (student_id,)).fetchone()
    parent = db.execute('SELECT * FROM Parents WHERE ParentID = ?', (student['ParentID'],)).fetchone()

    invoice_data = {
        'invoice_id': invoice['InvoiceID'],  # Generate or fetch the actual invoice ID
        'due_date': due_date,
        'student': dict(student),
        'parent': dict(parent),
        'amount': amount
    }

    session['invoice_data'] = invoice_data

    return redirect(url_for('show_invoice'))

@app.route('/show_invoice')
@login_required
def show_invoice(user):
    invoice_data = session.get('invoice_data')
    if not invoice_data:
        return redirect((url_for('index')))
    return render_template('invoice.html', **invoice_data)

####################################
##
##        STATEMENTS
##
#####################################

@app.route('/generate_statement/<int:student_id>', methods=['GET', 'POST'])
@login_required
def generate_statement(user, student_id):
    db = get_db()
    student = db.execute('SELECT * FROM Students WHERE StudentID = ?', (student_id,)).fetchone()

    # Handle case where student is not found
    if student is None:
        flash('Student not found.', 'error')
        return redirect(url_for('index'))

    # Access the ParentID using dictionary-style access
    parent = db.execute('SELECT * FROM Parents WHERE ParentID = ?', (student['ParentID'],)).fetchone()

    # get all payments entered for this student
    payments = db.execute('SELECT * FROM Payments WHERE StudentID = ?', (student_id,)).fetchall()
    db.close()
    # Set the total for all payments entered
    total = 0;
    for payment in payments:
        total += payment['Amount']

    payments_list = [dict(payment) for payment in payments]

    statement_data = {
        'parent': dict(parent),
        'student': dict(student),
        'payments': payments_list,
        'total': total
    }

    session['statement_data'] = statement_data

    return redirect(url_for('show_statement'))

@app.route('/show_statement')
@login_required
def show_statement(user):
    statement_data = session.get('statement_data')
    if not statement_data:
        return redirect(url_for('index'))
    return render_template('statement.html', **statement_data)



