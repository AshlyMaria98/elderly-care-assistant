from flask import Flask, render_template, request, redirect, url_for, session
from datetime import datetime
from datetime import date
import os
import sqlite3

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(BASE_DIR, "database.db ")

app = Flask(__name__)
app.secret_key = "secret_key"

# ---------------- TEMPLATE FILTERS ----------------
@app.template_filter('datetimeformat')
def datetimeformat(value, format='%B %d, %Y'):
    """Format date strings like '2026-03-08' → 'March 08, 2026'"""
    try:
        dt = datetime.strptime(value, '%Y-%m-%d')
        return dt.strftime(format)
    except:
        return value


# ---------------- DATABASE ----------------
def get_db_connection():
    conn = sqlite3.connect(db_path)
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
    #====================MOD3 DB STARTS========================
    # ---------------- HEALTH RECORDS TABLE ----------------
    conn.execute("""
        CREATE TABLE IF NOT EXISTS health_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            elder_id INTEGER,
            bp TEXT,
            sugar TEXT,
            pulse TEXT,
            weight REAL,
            height REAL,
            bmi REAL,
            date TEXT,
            FOREIGN KEY (elder_id) REFERENCES users(id)
        )
    """)

# ---------------- MOOD LOGS TABLE ----------------
    conn.execute("""
        CREATE TABLE IF NOT EXISTS mood_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            elder_id INTEGER,
            mood TEXT,
            date TEXT,
            FOREIGN KEY (elder_id) REFERENCES users(id)
        )
    """)
# ---------------- SOS ALERTS TABLE ----------------
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sos_alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            elder_id INTEGER,
            message TEXT,
            date_time TEXT,
            status TEXT DEFAULT 'pending',
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

# ---------------- GUARDIAN VIEW HEALTH ----------------
@app.route('/guardian_health')
def guardian_health():

    if 'user_id' not in session or session['role'] != 'guardian':
        return redirect(url_for('login'))

    guardian_id = session['user_id']
    conn = get_db_connection()

    # Get all elders linked to guardian
    elders = conn.execute("""
        SELECT id, fullname, age
        FROM users
        WHERE guardian_id = ?
    """, (guardian_id,)).fetchall()

    health_data = []
    for elder in elders:
        elder_id = elder['id']

        # Latest health entry
        latest = conn.execute("""
            SELECT bp, sugar, pulse, bmi, date
            FROM health_records
            WHERE elder_id = ?
            ORDER BY date DESC
            LIMIT 1
        """, (elder_id,)).fetchone()

        # All BP records for graph
        records = conn.execute("""
            SELECT bp, sugar, pulse, date
            FROM health_records
            WHERE elder_id = ?
            ORDER BY date
        """, (elder_id,)).fetchall()

        bp_list = []
        sugar_list = []
        pulse_list = []
        dates = []

        for r in records:
            try:
                if r['bp'] and '/' in r['bp']:
                    bp_val = int(r['bp'].split('/')[0])
                elif r['bp']:
                    bp_val = int(r['bp'])
                else:
                    bp_val = None
                bp_list.append(bp_val)
            except:
                bp_list.append(None)

            try:
                sugar_list.append(int(r['sugar']) if r['sugar'] else None)
            except:
                sugar_list.append(None)

            try:
                pulse_list.append(int(r['pulse']) if r['pulse'] else None)
            except:
                pulse_list.append(None)

            dates.append(r['date'])

        health_data.append({
            "name": elder['fullname'],
            "age": elder['age'],
            "latest": latest,
            "bp_list": bp_list,
            "sugar_list": sugar_list,
            "pulse_list": pulse_list,
            "dates": dates,
            "id": elder_id
        })


    conn.close()

    return render_template("guardian_health.html", health_data=health_data)

# ---------------- GUARDIAN VIEW ELDER HEALTH HISTORY ----------------
@app.route('/guardian_health_history/<int:elder_id>')
def guardian_health_history(elder_id):

    if 'user_id' not in session or session['role'] != 'guardian':
        return redirect(url_for('login'))

    conn = get_db_connection()

    elder = conn.execute(
        "SELECT fullname, age FROM users WHERE id=?",
        (elder_id,)
    ).fetchone()

    records = conn.execute(
        "SELECT * FROM health_records WHERE elder_id=? ORDER BY date DESC",
        (elder_id,)
    ).fetchall()

    # Lists for chart
    bp_list = []
    sugar_list = []
    pulse_list = []
    dates = []
    insights = []

    for r in records:

        # BP
        try:
            if r['bp'] and '/' in r['bp']:
                bp_val = int(r['bp'].split('/')[0])
            else:
                bp_val = int(r['bp'])
        except:
            bp_val = None
        bp_list.append(bp_val)

        # Sugar
        try:
            sugar_val = int(r['sugar']) if r['sugar'] else None
        except:
            sugar_val = None
        sugar_list.append(sugar_val)

        # Pulse
        try:
            pulse_val = int(r['pulse']) if r['pulse'] else None
        except:
            pulse_val = None
        pulse_list.append(pulse_val)

        # Date
        dates.append(r['date'])

        # Insights
        msg = []
        if bp_val and bp_val > 140:
            msg.append("High BP")
        if sugar_val and sugar_val > 150:
            msg.append("High sugar")
        if r['bmi'] and (r['bmi'] > 25 or r['bmi'] < 18.5):
            msg.append("BMI abnormal")

        insights.append(msg)

    conn.close()

    return render_template(
        "guardian_health_history.html",
        elder=elder,
        records=records,
        insights=insights,
        bp_list=bp_list,
        sugar_list=sugar_list,
        pulse_list=pulse_list,
        dates=dates,
        zip=zip
    )
# ---------------- GUARDIAN DASHBOARD: LATEST MOODS ----------------
@app.route('/guardian_moods')
def guardian_latest_moods():
    if 'user_id' not in session or session['role'] != 'guardian':
        return redirect(url_for('login'))

    guardian_id = session['user_id']
    conn = get_db_connection()

    # Get all elders linked to guardian
    elders = conn.execute("""
        SELECT id, fullname, age
        FROM users
        WHERE guardian_id = ?
    """, (guardian_id,)).fetchall()

    mood_data = []

    for elder in elders:
        elder_id = elder['id']

        # Get last 3 moods
        recent_moods = conn.execute("""
            SELECT mood, date
            FROM mood_logs
            WHERE elder_id = ?
            ORDER BY date DESC
            LIMIT 3
        """, (elder_id,)).fetchall()

        if not recent_moods:
            mood_data.append({
                "name": elder['fullname'],
                "age": elder['age'],
                "latest": None,
                "alert": False,
                "suggestion": "No mood recorded yet."
            })
            continue

        # Latest mood
        latest = recent_moods[0]

        # Count sad moods for alert
        sad_count = sum(1 for m in recent_moods if m['mood'].lower() == "sad")

        # Generate suggestion based on latest mood
        mood_val = latest['mood'].lower()
        if mood_val == "sad":
            suggestion = "Call or chat with a loved one, listen to music, or go for a gentle walk."
        elif mood_val == "lonely":
            suggestion = "Reach out to family or friends, or join a small social activity."
        elif mood_val == "stressed":
            suggestion = "Take a few deep breaths, stretch lightly, or enjoy a calming activity."
        elif mood_val == "angry":
            suggestion = "Step away for a moment, drink water, or take a short walk to calm down."
        elif mood_val == "happy":
            suggestion = "Keep enjoying activities that make you happy!"
        elif mood_val == "calm":
            suggestion = "Maintain your calm with relaxing activities like reading or light exercise."
        else:
            suggestion = "Stay hydrated and active, and connect with loved ones."

        mood_data.append({
            "name": elder['fullname'],
            "age": elder['age'],
            "latest": latest,
            "alert": sad_count >= 2,  # True if sad 2 or more times in last 3
            "suggestion": suggestion
        })

    conn.close()

    return render_template("guardian_latest_moods.html", mood_data=mood_data)


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
# -------------------- MODULE 3: HEALTH --------------------
@app.route('/add_health', methods=['GET', 'POST'])
def add_health():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        elder_id = session['user_id']
        bp = request.form['bp'].strip()      # expects format "120/80"
        sugar = request.form['sugar'].strip()
        pulse = request.form['pulse'].strip()
        weight = float(request.form['weight'])
        height_cm = float(request.form['height'])

        # Convert height to meters for BMI
        height_m = height_cm / 100
        bmi = round(weight / (height_m ** 2), 2)
        today = date.today().isoformat()

        conn = get_db_connection()
        conn.execute("""
            INSERT INTO health_records (elder_id, bp, sugar, pulse, weight, height, bmi, date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (elder_id, bp, sugar, pulse, weight, height_cm, bmi, today))
        conn.commit()
        conn.close()

        return redirect(url_for('view_health'))

    return render_template('health.html')

#-------------view health---------------------------------------
@app.route('/view_health')
def view_health():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    elder_id = session['user_id']
    conn = get_db_connection()
    records = conn.execute(
        "SELECT * FROM health_records WHERE elder_id=? ORDER BY date DESC",
        (elder_id,)
    ).fetchall()
    conn.close()

    # Convert records to list
    records = list(records)

    insights = []
    bp_list = []  # single BP number for chart

    for r in records:
        msg = []

        # BP
        try:
            bp_val = int(r['bp'])
            bp_list.append(bp_val)
            if bp_val > 140:
                msg.append("High BP warning!")
        except:
            bp_list.append(None)  # if BP missing or invalid

        # Sugar
        try:
            if r['sugar'] and int(r['sugar']) > 150:
                msg.append("High sugar level!")
        except:
            pass

        # BMI
        if r['bmi'] > 25:
            msg.append("BMI high – exercise recommended!")
        elif r['bmi'] < 18.5:
            msg.append("BMI low – consider nutrition!")

        insights.append(msg)

    return render_template(
        'view_health.html',
        records=records,
        insights=insights,
        bp_list=bp_list,
        zip=zip
    )
# -------------------- DELETE HEALTH RECORD --------------------
@app.route('/delete_health/<int:record_id>')
def delete_health(record_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    elder_id = session['user_id']

    conn = get_db_connection()
    # Ensure the record belongs to the logged-in user
    record = conn.execute(
        "SELECT * FROM health_records WHERE id=? AND elder_id=?",
        (record_id, elder_id)
    ).fetchone()

    if record:
        conn.execute("DELETE FROM health_records WHERE id=?", (record_id,))
        conn.commit()

    conn.close()
    return redirect(url_for('view_health'))

# ---------------- HEALTH HUB ----------------
@app.route('/healthhub')
def health_hub():
    if 'user_id' not in session or session['role'] != 'elder':
        return redirect(url_for('login'))
    return render_template('healthhub.html')


# ---------------- MOOD OPTIONS (INTERMEDIATE PAGE) ----------------
@app.route('/mood_options')
def mood_options():
    # Only elders can access
    if 'user_id' not in session or session['role'] != 'elder':
        return redirect(url_for('login'))

    return render_template('mood_options.html')


# ---------------- MOOD HUB ----------------
@app.route('/moodhub', methods=['GET', 'POST'])
def mood_hub():

    if 'user_id' not in session or session['role'] != 'elder':
        return redirect(url_for('login'))

    suggestion = None
    alert_message = None

    if request.method == 'POST':

        elder_id = session['user_id']
        mood = request.form.get('mood', '').lower()
        notes = request.form.get('notes', '').lower()
        today = date.today().isoformat()

        # -------- SAVE MOOD --------
        conn = get_db_connection()

        conn.execute("""
        INSERT INTO mood_logs (elder_id, mood, date)
        VALUES (?, ?, ?)
        """, (elder_id, mood, today))

        conn.commit()

        # -------- HEALTH CHECK FROM NOTES --------
        if "high bp" in notes or "bp high" in notes:

            suggestion = (
                "Your blood pressure may be high. Sit down and rest for a few minutes. "
                "Avoid salty foods today and drink some water. If you feel dizziness "
                "or headache, consider checking your BP or contacting a doctor."
            )

        elif "low bp" in notes:

            suggestion = (
                "Your blood pressure may be low. Sit down and rest and drink some water. "
                "Having a light snack with a little salt may help. If dizziness "
                "continues, inform a caregiver."
            )

        elif "high sugar" in notes or "sugar high" in notes:

            suggestion = (
                "Your blood sugar may be high. Try drinking water and avoid sugary "
                "foods for now. If possible, take a gentle walk and monitor your sugar level."
            )

        elif "low sugar" in notes or "sugar low" in notes:

            suggestion = (
                "Low blood sugar can cause weakness or dizziness. Consider eating "
                "something sweet like fruit juice or a biscuit and rest for a few minutes."
            )

        # -------- MOOD SUGGESTIONS --------
        else:

            if mood == "sad":
                suggestion = (
                    "You may be feeling low today. Try calling a family member or friend "
                    "for a short conversation. Listening to your favorite music or taking "
                    "a gentle walk outside can also improve your mood."
                )

            elif mood == "lonely":
                suggestion = (
                    "Feeling lonely can happen sometimes. Try reaching out to someone "
                    "you trust or spend time with neighbors or family."
                )

            elif mood == "stressed":
                suggestion = (
                    "Take a few minutes to relax. Sit comfortably and take slow deep "
                    "breaths. Drinking water and stretching lightly may help."
                )

            elif mood == "angry":
                suggestion = (
                    "Pause for a moment and breathe slowly. Take a short walk or "
                    "drink some water until you feel calmer."
                )

            elif mood == "happy":
                suggestion = (
                    "That's wonderful! Staying happy supports both mental and "
                    "physical health. Consider sharing your happiness with loved ones."
                )

            elif mood == "calm":
                suggestion = (
                    "Feeling calm is great for wellbeing. Continue activities that "
                    "bring peace like reading, prayer, or light exercise."
                )

            else:
                suggestion = (
                    "Thank you for sharing how you feel today. Remember to stay "
                    "hydrated and stay connected with people around you."
                )

        conn.close()

    return render_template("moodhub.html", suggestion=suggestion, alert=alert_message)
# ---------------- VIEW MOODS ----------------
@app.route('/viewmoods')
def view_moods():
    if 'user_id' not in session or session['role'] != 'elder':
        return redirect(url_for('login'))

    elder_id = session['user_id']
    conn = get_db_connection()
    moods = conn.execute("""
        SELECT mood, date
        FROM mood_logs
        WHERE elder_id = ?
        ORDER BY date DESC
        LIMIT 6
    """, (elder_id,)).fetchall()
    conn.close()

    mood_data = []
    for r in moods:
        mood_val = r['mood']
        date_val = r['date']

        if mood_val.lower() == "sad":
            suggestion = "Call or chat with a loved one, listen to music, or go for a gentle walk."
        elif mood_val.lower() == "lonely":
            suggestion = "Reach out to family or friends, or join a small social activity."
        elif mood_val.lower() == "stressed":
            suggestion = "Take a few deep breaths, stretch lightly, or enjoy a calming activity."
        elif mood_val.lower() == "angry":
            suggestion = "Step away for a moment, drink water, or take a short walk to calm down."
        elif mood_val.lower() == "happy":
            suggestion = "Keep enjoying activities that make you happy!"
        elif mood_val.lower() == "calm":
            suggestion = "Maintain your calm with relaxing activities like reading or light exercise."
        else:
            suggestion = "Stay hydrated and active, and connect with loved ones."

        mood_data.append({
            "date": date_val,
            "mood": mood_val,
            "suggestion": suggestion
        })

    return render_template("view_mood_table.html", mood_data=mood_data)
# ---------------- SOS PAGE (ELDER) ----------------
@app.route('/sos')
def sos():
    if 'user_id' not in session or session['role'] != 'elder':
        return redirect(url_for('login'))
    return render_template('elder_sos.html')


# ---------------- SEND SOS ----------------
@app.route('/send_sos', methods=['POST'])
def send_sos():
    if 'user_id' not in session or session['role'] != 'elder':
        return redirect(url_for('login'))

    elder_id = session['user_id']
    message = "Emergency alert triggered by elder"
    date_time = datetime.now().strftime("%Y-%m-%d %H:%M")

    conn = get_db_connection()
    conn.execute("""
        INSERT INTO sos_alerts (elder_id, message, date_time, status)
        VALUES (?, ?, ?, 'pending')
    """, (elder_id, message, date_time))
    conn.commit()
    conn.close()

    return render_template('elder_sos.html', message="🚨 SOS Alert Sent Successfully!")


# ---------------- SOS HISTORY (ELDER) ----------------
@app.route('/sos_history')
def sos_history():
    if 'user_id' not in session or session['role'] != 'elder':
        return redirect(url_for('login'))

    conn = get_db_connection()
    alerts = conn.execute("""
        SELECT * FROM sos_alerts
        WHERE elder_id = ?
        ORDER BY date_time DESC
    """, (session['user_id'],)).fetchall()
    conn.close()

    return render_template('sos_history.html', alerts=alerts)


# ---------------- GUARDIAN VIEW SOS ----------------
@app.route('/guardian_sos_alerts')
def guardian_sos_alerts():
    if 'user_id' not in session or session['role'] != 'guardian':
        return redirect(url_for('login'))

    conn = get_db_connection()

    alerts = conn.execute("""
        SELECT s.*, u.fullname as elder_name
        FROM sos_alerts s
        JOIN users u ON s.elder_id = u.id
        WHERE u.guardian_id = ?
        ORDER BY s.date_time DESC
    """, (session['user_id'],)).fetchall()

    conn.close()

    return render_template('guardian_sos_alerts.html', alerts=alerts)


# ---------------- RESOLVE SOS ----------------
@app.route('/resolve_sos/<int:id>')
def resolve_sos(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()

    conn.execute("""
        UPDATE sos_alerts
        SET status = 'resolved'
        WHERE id = ?
    """, (id,))

    conn.commit()
    conn.close()

    return redirect(url_for('guardian_sos_alerts'))
# ---------------- DELETE SOS ALERT (NEW) ----------------
@app.route('/delete_alert/<int:id>')
def delete_alert(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()

    conn.execute("""
        DELETE FROM sos_alerts
        WHERE id = ?
    """, (id,))

    conn.commit()
    conn.close()

    # ✅ FIX: redirect based on role
    if session['role'] == 'elder':
        return redirect(url_for('sos_history'))
    else:
        return redirect(url_for('guardian_sos_alerts'))
@app.route('/check_new_sos')
def check_new_sos():
    if 'user_id' not in session or session['role'] != 'guardian':
        return {"new": False}

    conn = get_db_connection()

    alert = conn.execute("""
        SELECT s.id, s.date_time
        FROM sos_alerts s
        JOIN users u ON s.elder_id = u.id
        WHERE u.guardian_id = ?
        AND s.status = 'pending'
        ORDER BY s.date_time DESC
        LIMIT 1
    """, (session['user_id'],)).fetchone()

    conn.close()

    if alert:
        return {"new": True, "id": alert["id"], "time": alert["date_time"]}
    else:
        return {"new": False}
@app.route('/guardian_latest_sos')
def guardian_latest_sos():
        if 'user_id' not in session or session['role'] != 'guardian':
            return redirect(url_for('login'))

        conn = get_db_connection()
        alerts = conn.execute("""
            SELECT s.*, u.fullname as elder_name
            FROM sos_alerts s
            JOIN users u ON s.elder_id = u.id
            WHERE u.guardian_id = ?
            ORDER BY s.date_time DESC
            LIMIT 2
        """, (session['user_id'],)).fetchall()

        conn.close()
        return render_template('guardian_latest_sos.html', alerts=alerts)   
if __name__ == '__main__':
    app.run(debug=True)