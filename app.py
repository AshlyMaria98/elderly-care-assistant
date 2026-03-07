from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
from datetime import datetime
from datetime import date

app = Flask(__name__)
app.secret_key = "secret_key"


# ---------------- DATABASE ----------------
def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def create_tables():
    conn = get_db_connection()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fullname TEXT NOT NULL,
            age INTEGER,
            username TEXT NOT NULL UNIQUE,
            phone TEXT,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
    """)

    # Safely add guardian_id column if it doesn't exist
    try:
        conn.execute("ALTER TABLE users ADD COLUMN guardian_id INTEGER")
    except:
        pass  # Column already exists, ignore error
#____________________module 1 db ending________________________________
#_______________________________________________________________________
#____________________module 2 db starting_____________________________
    # ---------------- REMINDERS TABLE ----------------
    conn.execute("""
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            elder_id INTEGER,
            title TEXT NOT NULL,
            type TEXT NOT NULL,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            notes TEXT,
            created_by TEXT DEFAULT 'elder',
            FOREIGN KEY (elder_id) REFERENCES users(id)
        )
    """)

    # ---------------- ROUTINE TASKS TABLE ----------------
    conn.execute("""
        CREATE TABLE IF NOT EXISTS routine_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            elder_id INTEGER,
            task_name TEXT NOT NULL,
            date TEXT NOT NULL,
            completed INTEGER DEFAULT 0,
            FOREIGN KEY (elder_id) REFERENCES users(id)
        )
    """)


    conn.commit()
    conn.close()



create_tables()


# ---------------- LANDING ----------------
@app.route('/')
def landing():
    return render_template('landing.html')


# ---------------- SIGNUP ----------------
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    error = None

    if request.method == 'POST':
        fullname = request.form['fullname']
        age = request.form['age']
        username = request.form['username']
        phone = request.form['phone']
        password = request.form['password']
        role = request.form['role']

        conn = get_db_connection()

        # Check if username already exists
        existing = conn.execute(
            "SELECT * FROM users WHERE username=?",
            (username,)
        ).fetchone()

        if existing:
            error = "Username already exists"
            conn.close()
            return render_template('signup.html', error=error)

        guardian_id = None  # Default for guardians

        # If role is elder → find guardian
        if role == "elder":
            guardian_username = request.form.get('guardian_username')

            guardian = conn.execute(
                "SELECT id FROM users WHERE username=? AND role='guardian'",
                (guardian_username,)
            ).fetchone()

            if guardian:
                guardian_id = guardian['id']
            else:
                error = "Guardian username not found"
                conn.close()
                return render_template('signup.html', error=error)

        # Insert user with guardian_id
        conn.execute(
            """INSERT INTO users 
               (fullname, age, username, phone, password, role, guardian_id) 
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (fullname, age, username, phone, password, role, guardian_id)
        )

        conn.commit()
        conn.close()

        return redirect(url_for('login'))

    return render_template('signup.html', error=error)


# ---------------- LOGIN ----------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']

        conn = get_db_connection()

        user = conn.execute(
            "SELECT * FROM users WHERE username=? AND password=? AND role=?",
            (username, password, role)
        ).fetchone()

        conn.close()

        if user:
            session['user_id'] = user['id']
            session['role'] = user['role']
            session['name'] = user['fullname']

            if user['role'] == 'elder':
                return redirect(url_for('elder_dashboard'))
            else:
                return redirect(url_for('guardian_dashboard'))
        else:
            error = "Invalid Credentials"

    return render_template('login.html', error=error)


# ---------------- ELDER DASHBOARD ----------------
@app.route('/elder_dashboard')
def elder_dashboard():
    if 'user_id' not in session or session['role'] != 'elder':
        return redirect(url_for('login'))

    return render_template('elder_dashboard.html')


# ---------------- GUARDIAN DASHBOARD ----------------
@app.route('/guardian_dashboard')
def guardian_dashboard():
    if 'user_id' not in session or session['role'] != 'guardian':
        return redirect(url_for('login'))

    return render_template('guardian_dashboard.html')


# ---------------- VIEW ELDERS ----------------
@app.route('/view_elders')
def view_elders():
    if 'user_id' not in session or session['role'] != 'guardian':
        return redirect(url_for('login'))

    conn = get_db_connection()

    elders = conn.execute("""
        SELECT fullname, age, phone FROM users
        WHERE role='elder' AND guardian_id = ?
    """, (session['user_id'],)).fetchall()

    conn.close()

    return render_template('guardian_users.html', elders=elders)



# ---------------- PROFILE ----------------
@app.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    user = conn.execute(
        "SELECT * FROM users WHERE id=?",
        (session['user_id'],)
    ).fetchone()
    conn.close()

    return render_template('profile.html', user=user)



# ---------------- BMI ----------------
@app.route('/bmi', methods=['GET', 'POST'])
def bmi():
    result = None
    message = None

    if request.method == 'POST':
        weight = float(request.form['weight'])
        height_cm = float(request.form['height'])

        # Convert cm to meters
        height_m = height_cm / 100

        result = round(weight / (height_m * height_m), 2)

        # Classification
        if result < 18.5:
            message = "Underweight – You may need nutritional improvement."
        elif 18.5 <= result < 25:
            message = "Normal – Keep maintaining a healthy lifestyle!"
        elif 25 <= result < 30:
            message = "Overweight – Consider light exercise and balanced diet."
        else:
            message = "Obese – It is advisable to consult a doctor."

    return render_template('bmi.html', result=result, message=message)



# ---------------- FORGOT PASSWORD ----------------
@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    message = None

    if request.method == 'POST':
        username = request.form['username']
        new_password = request.form['new_password']

        conn = get_db_connection()

        user = conn.execute(
            "SELECT * FROM users WHERE username=?",
            (username,)
        ).fetchone()

        if user:
            conn.execute(
                "UPDATE users SET password=? WHERE username=?",
                (new_password, username)
            )
            conn.commit()
            message = "Password Updated Successfully!"
        else:
            message = "Username not found!"

        conn.close()

    return render_template('forgot_password.html', message=message)
#---------------------module 1 break-------------------------
#_________________module 2 reminder route starting_______________________
#------------------------ADD REMINDER-----------------------

@app.route('/add_reminder', methods=['GET', 'POST'])
def add_reminder():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row

    if request.method == 'POST':
        title = request.form['title']
        reminder_type = request.form['type']
        date_value = request.form['date']
        time_value = request.form['time']
        notes = request.form['notes']

        if session['role'] == 'elder':
            elder_id = session['user_id']
        else:
            elder_id = request.form['elder_id']

        conn.execute("""
            INSERT INTO reminders 
            (title, type, date, time, status, notes, elder_id)
            VALUES (?, ?, ?, ?, 'pending', ?, ?)
        """, (title, reminder_type, date_value, time_value, notes, elder_id))

        conn.commit()
        conn.close()

        return redirect(url_for('view_reminders'))

    # GET request
    if session['role'] == 'guardian':
        elders = conn.execute("""
            SELECT * FROM users
            WHERE guardian_id = ?
        """, (session['user_id'],)).fetchall()
    else:
        elders = None

    conn.close()
    return render_template('add_reminder.html', elders=elders)

#------------------------VIEW REMINDER-----------------------
  
@app.route('/view_reminders')
def view_reminders():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row

    if session['role'] == 'elder':
        reminders = conn.execute("""
            SELECT * FROM reminders
            WHERE elder_id = ?
            ORDER BY date, time
        """, (session['user_id'],)).fetchall()

    else:  # guardian
       reminders = conn.execute("""
        SELECT r.*, u.fullname AS elder_name
        FROM reminders r
        JOIN users u ON r.elder_id = u.id
        WHERE u.guardian_id = ?
        ORDER BY r.date, r.time
        """, (session['user_id'],)).fetchall()


    conn.close()

    return render_template('view_reminders.html', reminders=reminders)


#---------------------------MARK REMINDER AS COMPLETED----------------

@app.route('/complete_reminder/<int:id>')
def complete_reminder(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row

    reminder = conn.execute("""
        SELECT * FROM reminders WHERE id = ?
    """, (id,)).fetchone()

    if session['role'] == 'elder' and reminder['elder_id'] != session['user_id']:
        return "Unauthorized"

    if session['role'] == 'guardian':
        check = conn.execute("""
            SELECT r.* FROM reminders r
            JOIN users u ON r.elder_id = u.id
            WHERE r.id = ? AND u.guardian_id = ?
        """, (id, session['user_id'])).fetchone()

        if not check:
            return "Unauthorized"

    conn.execute("""
        UPDATE reminders SET status = 'completed'
        WHERE id = ?
    """, (id,))
    conn.commit()
    conn.close()

    return redirect(url_for('view_reminders'))


#----------------------------------------SHOW DUE TODAY------------------

@app.route('/due_today')
def due_today():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    today = date.today().isoformat()

    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row

    if session['role'] == 'elder':
        reminders = conn.execute("""
            SELECT * FROM reminders
            WHERE elder_id = ?
            AND date = ?
            AND status = 'pending'
            ORDER BY time
        """, (session['user_id'], today)).fetchall()

    else:  # guardian
        reminders = conn.execute("""
    SELECT r.*, u.fullname AS elder_name
    FROM reminders r
    JOIN users u ON r.elder_id = u.id
    WHERE u.guardian_id = ?
    AND r.date = ?
    AND r.status = 'pending'
    ORDER BY r.time
""", (session['user_id'], today)).fetchall()

    conn.close()

    return render_template('due_today.html', reminders=reminders)

#---------------------------MISSED REMINDERS-------------------

@app.route('/missed_reminders')
def missed_reminders():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row

    if session['role'] == 'elder':
        reminders = conn.execute("""
            SELECT * FROM reminders
            WHERE elder_id = ?
            AND status = 'pending'
            AND (date || ' ' || time) < ?
            ORDER BY date, time
        """, (session['user_id'], now)).fetchall()

    else:  # guardian
        reminders = conn.execute("""
            SELECT r.*, u.fullname AS elder_name
            FROM reminders r
            JOIN users u ON r.elder_id = u.id
            WHERE u.guardian_id = ?
            AND r.status = 'pending'
            AND (r.date || ' ' || r.time) < ?
            ORDER BY r.date, r.time
        """, (session['user_id'], now)).fetchall()

    conn.close()

    return render_template('missed_reminders.html', reminders=reminders)

#---------------------------ADD DAILY ROUTINE TASK---------------------
@app.route('/add_task', methods=['GET', 'POST'])
def add_task():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()

    if request.method == 'POST':
        task_name = request.form['task_name']
        date = request.form['date']

        if session['role'] == 'elder':
            elder_id = session['user_id']
        else:
            elder_id = request.form['elder_id']

        conn.execute("""
            INSERT INTO routine_tasks (elder_id, task_name, date)
            VALUES (?, ?, ?)
        """, (elder_id, task_name, date))

        conn.commit()
        conn.close()

        return redirect(url_for('view_tasks'))

    # GET request
    if session['role'] == 'guardian':
        elders = conn.execute("""
            SELECT * FROM users
            WHERE guardian_id = ?
        """, (session['user_id'],)).fetchall()
    else:
        elders = None

    conn.close()
    return render_template('add_task.html', elders=elders)


#-----------------------------------------VIEW TASKS-------------------
@app.route('/view_tasks')
def view_tasks():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()

    if session['role'] == 'elder':
        tasks = conn.execute("""
            SELECT * FROM routine_tasks
            WHERE elder_id=?
            ORDER BY date
        """, (session['user_id'],)).fetchall()

    else:
        tasks = conn.execute("""
       SELECT t.*, u.fullname AS elder_name
        FROM routine_tasks t
        JOIN users u ON t.elder_id = u.id
        WHERE u.guardian_id = ?
        ORDER BY t.date
        """, (session['user_id'],)).fetchall()


    conn.close()

    return render_template('view_tasks.html', tasks=tasks)

#------------------------------MARK TASK COMPLETED-----------------

@app.route('/complete_task/<int:id>')
def complete_task(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()

    task = conn.execute("""
        SELECT * FROM routine_tasks WHERE id=?
    """, (id,)).fetchone()

    if not task:
        return "Task not found"

    if session['role'] == 'elder':
        if task['elder_id'] != session['user_id']:
            return "Unauthorized"

    else:  # guardian
        check = conn.execute("""
            SELECT t.* FROM routine_tasks t
            JOIN users u ON t.elder_id = u.id
            WHERE t.id=? AND u.guardian_id=?
        """, (id, session['user_id'])).fetchone()

        if not check:
            return "Unauthorized"

    conn.execute("""
        UPDATE routine_tasks
        SET completed=1
        WHERE id=?
    """, (id,))

    conn.commit()
    conn.close()

    return redirect(url_for('view_tasks'))


#________________module 2 reminder route ending__________________________
#--------------------module 1 break continues-------------------
# ---------------- LOGOUT ----------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('landing'))
#___________________module 1 route ending__________________________

if __name__ == '__main__':
    app.run(debug=True)
