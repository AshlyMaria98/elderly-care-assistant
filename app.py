from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3

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


# ---------------- LOGOUT ----------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('landing'))


if __name__ == '__main__':
    app.run(debug=True)
