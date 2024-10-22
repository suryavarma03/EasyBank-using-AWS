from flask import Flask, render_template, request, redirect, url_for
import mysql.connector
from flask import flash, session
from datetime import datetime

app = Flask(__name__)
app.secret_key = "your_secret_key"  # Needed for flash msgs

# Database config
db_config = {
    'host': 'bank.crqmssgockvo.ap-south-1.rds.amazonaws.com',
    'user': 'admin',
    'password': 'Surya123456',
    'database': 'bank'
}

 cnxpool = mysql.connector.pooling.MySQLConnectionPool(pool_name="mypool",
                                                       pool_size=5,
                                                       **db_config)

# Function to establish a database connection
def get_db_connection():
    try:
        return cnxpool.get_connection()
    except mysql.connector.Error as err:
        print(f"Error: {err}")
        return None
    
@app.route("/test-db-connection")
def test_db_connection():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT DATABASE();")  # Test query to check connection
        db_name = cursor.fetchone()
        cursor.close()
        conn.close()
        return f"Connected to the database: {db_name[0]}"
    except mysql.connector.Error as err:
        return f"Error: {err}"



# Define your routes here
@app.route("/")
def index():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
    except mysql.connector.Error as err:
        print(f"Error: {err}")
    finally:
        if conn:
            cursor.close()
            conn.close()
    return render_template("index.html")


@app.route("/register", methods=['post', 'get'])
def register():
    if request.method == 'POST':
        # session.init_app(app)  # Initialize the session
        full_name = request.form['full_name']
        email = request.form['email']
        password = request.form['password']
        phone = request.form['phone']
        address = request.form['address']
        aadhar_number = request.form['aadhar_number']
        pan_card = request.form['pan_card']

        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if the user already exists
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()

        if user:
            flash("email already exists! Please log in")
            return redirect(url_for('login', email= email)) # redirect to login page
        
        # Validate phone number and Aadhar number
        if len(phone) != 10:
            flash("Phone number must be 10 digits")
            return render_template("register.html")
        if len(aadhar_number) != 12:
            flash("Aadhar number must be 12 digits")
            return render_template("register.html")

        # Insert the new user into the database
        cursor.execute("INSERT INTO users (full_name, email, password, phone, address, aadhar_number, pan_card) VALUES (%s,%s, %s, %s, %s, %s, %s)",
                       (full_name, email, password, phone, address, aadhar_number, pan_card))
        conn.commit()
        cursor.close()
        conn.close()

        user_data = {
            'full_name': full_name,
            'email': email,
        }
        session['user'] = user_data
        flash("Registration successful! Please log in.")
        return redirect(url_for('confirm',user=user_data))

    return render_template("register.html")

@app.route("/confirm")
def confirm():
    user = session.get('user')
    if user:
        return render_template("confirm.html", user=user)
    else:
        return redirect(url_for('login'))

@app.route("/login", methods=['post','get'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']


        conn = get_db_connection()
        cursor = conn.cursor()

        # Verify login credentials
        cursor.execute("SELECT * FROM users WHERE email = %s AND password = %s", 
                       (email, password))
        user = cursor.fetchone()

        cursor.close()
        conn.close()

        if user:
            user_data = {
                'fullname' : user[4],
                'email': user[1],
                'user_id':user[0]                
            }
            session['user'] = user_data
            print('this is email', email)
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid login credentials!")
            return redirect(url_for('login'))


    return render_template("login.html")


@app.route("/dashboard")
def dashboard():
    user_data = session.get('user')
    if user_data:
        email = user_data['email']
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        return render_template("dashboard.html", user=user)
    else:
        return redirect(url_for('login'))
    
@app.route("/deposit", methods=['post', 'get'])
def deposit():
    user_data = session.get('user')
    if user_data:
        if request.method == 'POST':
            amount = float(request.form['deposit_amount'])
            account_type = request.form['account_type']
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM accounts WHERE user_id = %s", (user_data['user_id'],))
            if not cursor.fetchone():
                # Insert a new row
                cursor.execute("INSERT INTO accounts (user_id, balance, account_type) VALUES (%s, %s, %s)", (user_data['user_id'], amount, account_type))
                cursor.execute("INSERT INTO account_statements (user_id, transaction_type,transaction_amount, transaction_date) VALUES (%s, 'Credit', %s, %s)", (user_data['user_id'], amount, datetime.now()))
            else:
                # Update the existing row
                cursor.execute("UPDATE accounts SET balance = balance + %s WHERE user_id = %s", (amount, user_data['user_id']))
                cursor.execute("INSERT INTO account_statements (user_id, transaction_type,transaction_amount,  transaction_date) VALUES (%s, 'Credit', %s, %s)", (user_data['user_id'], amount, datetime.now()))
            conn.commit()
            cursor.close()
            conn.close()
            flash("Funds deposited successfully!")
            return redirect(url_for('dashboard'))
        return render_template("deposit.html")
    else:
        return redirect(url_for('login'))
    
@app.route("/balance", methods=['get'])
def check_balance():
    user_data = session.get('user')
    if user_data:
        email = user_data['email']
        conn = cnxpool.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT balance FROM accounts WHERE user_id = %s", (user_data['user_id'],))
        balance = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        return render_template("balance.html", balance=balance)
    else:
        return redirect(url_for('login'))

@app.route("/account-statement", methods=['get'])
def account_statement():
    user_data = session.get('user')
    if user_data:
        email = user_data['email']
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM transactions WHERE email = %s", (email,))
        transactions = cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template("account_statement.html", transactions=transactions)
    else:
        return redirect(url_for('login'))
    
@app.route("/transfer", methods=['post', 'get'])
def transfer():
    user_data = session.get('user')
    if user_data:
        if request.method == 'POST':
            user_id = request.form.get('user_id')
            amount = request.form.get('amount')
            
            if user_id and amount:
                try:
                    amount = float(amount)
                    
                    # Check if the user_id exists
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute("SELECT user_id FROM users WHERE user_id = %s", (user_id,))
                    recipient_user_id = cursor.fetchone()
                    
                    if recipient_user_id is None:
                        flash("Recipient user not found!")
                        return redirect(url_for('transfer'))
                    
                    # Check if the sender has sufficient balance
                    cursor.execute("SELECT balance FROM accounts WHERE user_id = %s", (user_data['user_id'],))
                    sender_balance = cursor.fetchone()
                    
                    if sender_balance is None:
                        flash("Sender account not found!")
                        return redirect(url_for('transfer'))
                    
                    sender_balance = sender_balance[0]
                    
                    if sender_balance >= amount:
                        # Update sender's balance
                        cursor.execute("UPDATE accounts SET balance = balance - %s WHERE user_id = %s", (amount, user_data['user_id']))
                        
                        # Update recipient's balance
                        cursor.execute("UPDATE accounts SET balance = balance + %s WHERE user_id = %s", (amount, user_id))
                        
                        # Insert a new transaction into the account_statements table
                        cursor.execute("INSERT INTO account_statements (user_id, transaction_type, transaction_amount, transaction_date) VALUES (%s, 'Debit', %s, %s)", (user_data['user_id'], amount, datetime.now()))
                        cursor.execute("INSERT INTO account_statements (user_id, transaction_type, transaction_amount, transaction_date) VALUES (%s, 'Credit', %s, %s)", (user_id, amount, datetime.now()))
                        
                        conn.commit()
                        cursor.close()
                        conn.close()
                        flash("Funds transferred successfully!")
                        return redirect(url_for('dashboard'))
                    else:
                        flash("Insufficient balance!")
                        return redirect(url_for('transfer'))
                except ValueError:
                    flash("Invalid transfer amount!")
                    return redirect(url_for('transfer'))
            else:
                flash("Please fill in all fields!")
                return redirect(url_for('transfer'))
        return render_template("transfer.html")
    else:
        return redirect(url_for('login'))

@app.route("/statement", methods=['GET'])
def statements():
    user_data = session.get('user')
    if user_data:
        user_id = user_data['user_id']
        conn = get_db_connection()
        cursor = conn.cursor()

        # Fetch the account statements for the logged-in user
        cursor.execute("""
            SELECT transaction_type, transaction_amount, transaction_date, description
            FROM account_statements
            WHERE user_id = %s
            ORDER BY transaction_date DESC
        """, (user_id,))
        
        transactions = cursor.fetchall()

        cursor.close()
        conn.close()

        return render_template("statement.html", transactions=transactions)
    else:
        return redirect(url_for('login'))
    

@app.route("/customer-support")
def customer_support():
    return render_template("customer_support.html")


@app.route("/services")
def services():
    return render_template("services.html")

@app.route("/contact")
def contact():
    return render_template("contact.html")


if __name__ == "__main__":
    app.run(host='0.0.0.0',port=5000,debug=True)
