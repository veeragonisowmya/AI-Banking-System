from flask import Flask, render_template,request, session, redirect
import mysql.connector
from decimal import Decimal
import random
from datetime import datetime
import joblib
import numpy as np

app = Flask(__name__)
app.secret_key = "mysmartbank123"

db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="sowmya",          # Change if your MySQL has a password
    database="ai_smart_bank"
)

cursor = db.cursor()

if db.is_connected():
    print("✅ Connected to MySQL Successfully")

model = joblib.load("fraud_model.pkl")

device_encoder = joblib.load("device_encoder.pkl")

location_encoder = joblib.load("location_encoder.pkl")

time_encoder = joblib.load("time_encoder.pkl")


@app.route('/', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        email = request.form['email']
        password = request.form['password']

        sql = """
        SELECT * FROM users
        WHERE email=%s AND password=%s
        """

        cursor.execute(sql, (email, password))

        user = cursor.fetchone()

        if user:
            session['user_id'] = user[0]
            session['account_number'] = user[5]
            return redirect('/dashboard')
        else:
            return """
            <h2>Invalid Email or Password</h2>
            <a href="/">Try Again</a>
            """

    return render_template("login.html")

@app.route('/register', methods=['GET', 'POST'])
def register():

    if request.method == 'POST':

        fullname = request.form['fullname']
        email = request.form['email']
        mobile = request.form['mobile']
        password = request.form['password']

        import random

        account_number = str(random.randint(100000000000,999999999999))

        sql = """
        INSERT INTO users
        (fullname,email,mobile,password,account_number,balance)
        VALUES (%s,%s,%s,%s,%s,%s)
        """

        values = (
            fullname,
            email,
            mobile,
            password,
            account_number,
            50000
        )

        cursor.execute(sql, values)
        db.commit()

        return "<h2>Registration Successful!</h2><a href='/'>Go to Login</a>"

    return render_template('register.html')

@app.route('/dashboard')
def dashboard():

    if 'user_id' not in session:
        return redirect('/')

    # Logged in user
    cursor.execute(
        "SELECT * FROM users WHERE user_id=%s",
        (session['user_id'],)
    )

    user = cursor.fetchone()

    account_number = user[5]

    # ==============================
    # Total Transactions
    # ==============================

    cursor.execute("""
        SELECT COUNT(*)
        FROM transactions
        WHERE sender_account=%s
    """, (account_number,))

    total_transactions = cursor.fetchone()[0]

    # ==============================
    # Fraud Alerts
    # ==============================

    cursor.execute("""
        SELECT COUNT(*)
        FROM transactions
        WHERE sender_account=%s
        AND risk_score>=80
    """, (account_number,))

    fraud_alerts = cursor.fetchone()[0]

    # ==============================
    # Highest Risk Score
    # ==============================

    cursor.execute("""
        SELECT MAX(risk_score)
        FROM transactions
        WHERE sender_account=%s
    """, (account_number,))

    max_risk = cursor.fetchone()[0]

    if max_risk is None:
        max_risk = 0

    # ==============================
    # Risk Level
    # ==============================

    if max_risk >= 80:
        risk_level = "HIGH"

    elif max_risk >= 50:
        risk_level = "MEDIUM"

    else:
        risk_level = "LOW"

    # ==============================
    # Recent Transactions
    # ==============================

    cursor.execute("""
        SELECT
        transaction_id,
        transaction_time,
        amount,
        status
        FROM transactions
        WHERE sender_account=%s
        ORDER BY transaction_time DESC
        LIMIT 5
    """, (account_number,))

    recent_transactions = cursor.fetchall()

    return render_template(
        "dashboard.html",
        user=user,
        total_transactions=total_transactions,
        fraud_alerts=fraud_alerts,
        risk_level=risk_level,
        max_risk=max_risk,
        recent_transactions=recent_transactions
    )

@app.route('/transfer', methods=['GET', 'POST'])
def transfer():

    if 'user_id' not in session:
        return redirect('/')

    # Get logged-in user
    cursor.execute(
        "SELECT * FROM users WHERE user_id=%s",
        (session['user_id'],)
    )

    user = cursor.fetchone()

    if request.method == "POST":

        receiver = request.form['receiver']
        amount = Decimal(request.form['amount'])

        device = request.form['device']
        location = request.form['location']
        time = request.form['time']

        sender_balance = user[6]
        sender_account = user[5]

        # ----------------------------
        # Receiver Validation
        # ----------------------------

        cursor.execute(
            "SELECT * FROM users WHERE account_number=%s",
            (receiver,)
        )

        receiver_user = cursor.fetchone()

        if receiver_user is None:

            return render_template(
                "transfer.html",
                user=user,
                error="Receiver Account Not Found!"
            )

        if sender_balance < amount:

            return render_template(
                "transfer.html",
                user=user,
                error="Insufficient Balance!"
            )

        # ----------------------------
        # AI Fraud Detection
        # ----------------------------

        device_value = device_encoder.transform([device])[0]
        location_value = location_encoder.transform([location])[0]
        time_value = time_encoder.transform([time])[0]

        features = np.array([[
            float(amount),
            device_value,
            location_value,
            time_value
        ]])

        prediction = model.predict(features)[0]

        risk_score = round(
            model.predict_proba(features)[0][1] * 100,
            2
        )

        # ----------------------------
        # Explainable AI
        # ----------------------------

        reasons = []

        if amount >= Decimal("50000"):
            reasons.append("Large transaction amount")

        if device == "New":
            reasons.append("New device detected")

        if location == "Different":
            reasons.append("Transaction from different location")

        if time == "Night":
            reasons.append("Night-time transaction")

        if len(reasons) == 0:
            reasons.append("Normal transaction pattern")

        session['risk_score'] = risk_score
        session['reasons'] = reasons

        # ----------------------------
        # OTP Verification
        # ----------------------------

        if risk_score >= 80:

            otp = random.randint(100000, 999999)

            cursor.execute(
                """
                INSERT INTO otp_verification
                (account_number, otp, created_at)
                VALUES (%s,%s,%s)
                """,
                (
                    sender_account,
                    otp,
                    datetime.now()
                )
            )

            db.commit()

            session['receiver'] = receiver
            session['amount'] = str(amount)
            session['device'] = device
            session['location'] = location
            session['time'] = time

            print("===========================")
            print("OTP :", otp)
            print("===========================")

            return redirect('/otp')

        # ----------------------------
        # Normal Transfer
        # ----------------------------

        new_sender_balance = sender_balance - amount

        cursor.execute(
            "UPDATE users SET balance=%s WHERE user_id=%s",
            (new_sender_balance, session['user_id'])
        )

        receiver_balance = receiver_user[6]
        new_receiver_balance = receiver_balance + amount

        cursor.execute(
            "UPDATE users SET balance=%s WHERE account_number=%s",
            (new_receiver_balance, receiver)
        )

        cursor.execute(
            """
            INSERT INTO transactions
            (sender_account,
             receiver_account,
             amount,
             risk_score,
             status)
            VALUES (%s,%s,%s,%s,%s)
            """,
            (
                sender_account,
                receiver,
                amount,
                risk_score,
                "Success"
            )
        )

        db.commit()

        return render_template(
            "transfer.html",
            user=user,
            success=f"₹{amount} transferred successfully to Account {receiver}."
        )

    return render_template(
        "transfer.html",
        user=user
    )


@app.route('/otp', methods=['GET', 'POST'])
def otp():

    if 'user_id' not in session:
        return redirect('/')

    if request.method == "POST":

        entered_otp = request.form['otp']

        cursor.execute("""
            SELECT otp
            FROM otp_verification
            WHERE account_number=%s
            ORDER BY otp_id DESC
            LIMIT 1
        """, (session['account_number'],))

        data = cursor.fetchone()

        if data is None:

            return render_template(
                "otp.html",
                error="No OTP Found!"
            )

        if entered_otp != str(data[0]):

            return render_template(
                "otp.html",
                error="Invalid OTP!"
            )

        # ============================
        # OTP VERIFIED
        # ============================

        receiver = session['receiver']
        amount = Decimal(session['amount'])
        risk_score = session['risk_score']

        # Sender
        cursor.execute(
            "SELECT * FROM users WHERE user_id=%s",
            (session['user_id'],)
        )

        sender = cursor.fetchone()

        sender_balance = sender[6]
        sender_account = sender[5]

        # Receiver
        cursor.execute(
            "SELECT * FROM users WHERE account_number=%s",
            (receiver,)
        )

        receiver_user = cursor.fetchone()

        receiver_balance = receiver_user[6]

        # Update Sender Balance
        cursor.execute(
            """
            UPDATE users
            SET balance=%s
            WHERE user_id=%s
            """,
            (
                sender_balance - amount,
                session['user_id']
            )
        )

        # Update Receiver Balance
        cursor.execute(
            """
            UPDATE users
            SET balance=%s
            WHERE account_number=%s
            """,
            (
                receiver_balance + amount,
                receiver
            )
        )

        # Save Transaction
        cursor.execute("""
            INSERT INTO transactions
            (
                sender_account,
                receiver_account,
                amount,
                risk_score,
                status
            )
            VALUES (%s,%s,%s,%s,%s)
        """,
        (
            sender_account,
            receiver,
            amount,
            risk_score,
            "Success"
        ))

        db.commit()

        # Clear temporary session values

        session.pop('receiver', None)
        session.pop('amount', None)
        session.pop('device', None)
        session.pop('location', None)
        session.pop('time', None)
        session.pop('risk_score', None)
        session.pop('reasons', None)

        return redirect('/dashboard')

    return render_template("otp.html")


@app.route('/history')
def history():

    if 'user_id' not in session:
        return redirect('/')

    cursor.execute(
        "SELECT * FROM users WHERE user_id=%s",
        (session['user_id'],)
    )

    user = cursor.fetchone()

    account = user[5]

    cursor.execute("""
    SELECT
        t.transaction_id,
        t.sender_account,
        s.fullname,
        t.receiver_account,
        r.fullname,
        t.amount,
        t.risk_score,
        t.status,
        t.transaction_time
    FROM transactions t
    JOIN users s
        ON t.sender_account = s.account_number
    JOIN users r
        ON t.receiver_account = r.account_number
    WHERE
        t.sender_account=%s
        OR
        t.receiver_account=%s
    ORDER BY transaction_time DESC
    """,(account,account))

    transactions = cursor.fetchall()

    return render_template(
        "history.html",
        transactions=transactions,
        account=account
    )

@app.route('/fraud_report')
def fraud_report():

    if 'user_id' not in session:
        return redirect('/')

    cursor.execute("""
        SELECT
        transaction_id,
        sender_account,
        receiver_account,
        amount,
        risk_score,
        status
        FROM transactions
        ORDER BY transaction_id DESC
    """)

    transactions = cursor.fetchall()

    return render_template(
        "fraud_report.html",
        transactions=transactions
    )

@app.route('/admin_dashboard')
def admin_dashboard():

    if 'user_id' not in session:
        return redirect('/')

    # Get logged in user
    cursor.execute(
        "SELECT * FROM users WHERE user_id=%s",
        (session['user_id'],)
    )

    user = cursor.fetchone()

    # Check if logged in user is admin
    if user[-1] != "admin":
        return "<h2>Access Denied! Admin Only.</h2>"

    # -----------------------------
    # Existing Admin Dashboard Code
    # -----------------------------

    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM transactions")
    total_transactions = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*)
        FROM transactions
        WHERE risk_score>=80
    """)
    high_risk = cursor.fetchone()[0]

    cursor.execute("""
        SELECT SUM(amount)
        FROM transactions
    """)

    total_amount = cursor.fetchone()[0]

    if total_amount is None:
        total_amount = 0

    cursor.execute("""
        SELECT fullname,email,account_number,balance
        FROM users
        ORDER BY user_id DESC
        LIMIT 5
    """)

    users = cursor.fetchall()

    cursor.execute("""
        SELECT sender_account,
               receiver_account,
               amount,
               risk_score,
               status
        FROM transactions
        ORDER BY transaction_id DESC
        LIMIT 5
    """)

    transactions = cursor.fetchall()

    return render_template(
        "admin_dashboard.html",
        total_users=total_users,
        total_transactions=total_transactions,
        high_risk=high_risk,
        total_amount=total_amount,
        users=users,
        transactions=transactions
    )

@app.route('/risk_analysis')
def risk_analysis():

    if 'risk_score' not in session:
        return redirect('/dashboard')

    return render_template(
        "risk_analysis.html",
        risk_score=session['risk_score'],
        reasons=session['reasons']
    )


@app.route('/logout')
def logout():

    session.clear()

    return redirect('/')

if __name__ == "__main__":
    app.run(port=8000, debug=False, use_reloader=False)
