from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session
import json
from collections import defaultdict
import os
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "your_secret_key"

# File paths
USERS_FILE = 'users.json'
DATA_FILE = 'accounts_data.json'

# Utility: Load JSON data
def load_json(file_path):
    if not os.path.exists(file_path):
        with open(file_path, 'w') as f:
            json.dump({}, f)
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError:
        with open(file_path, 'w') as f:
            json.dump({}, f)
        return {}

# Utility: Save JSON data
def save_json(file_path, data):
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=4)

# Ensure files exist
load_json(USERS_FILE)
load_json(DATA_FILE)

# Authentication functions
def register_user(username, password):
    users = load_json(USERS_FILE)
    if username in users:
        return False
    hashed_password = generate_password_hash(password)
    users[username] = {'password': hashed_password}
    save_json(USERS_FILE, users)
    return True

def authenticate_user(username, password):
    users = load_json(USERS_FILE)
    if username in users and check_password_hash(users[username]['password'], password):
        return True
    return False

# Load account data (JSON-based storage)
def load_accounts():
    return load_json(DATA_FILE)  

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if authenticate_user(username, password):
            session['user'] = username
            return redirect('/dashboard')
        return "Invalid credentials", 401
    return render_template('auth.html', action="Login", submit_label="Login")

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            return "Passwords do not match", 400

        if register_user(username, password):
            return redirect('/login')
        return "User already exists", 400
    return render_template('auth.html', action="Register", submit_label="Register")

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('index'))

    username = session['user']
    accounts = load_json(DATA_FILE)
    
    # Ensure the user has accounts, default to empty list
    user_data = accounts.get(username, {})
    user_accounts = user_data.get("accounts", [])  # Fetch account list properly
    
    return render_template('dashboard.html', accounts=user_accounts)


@app.route('/create_account', methods=['GET', 'POST'])
def create_account():
    if 'user' not in session:
        return redirect(url_for('index'))

    if request.method == 'POST':
        account_name = request.form.get('account_name')
        initial_balance = float(request.form.get('initial_balance'))
        goal = float(request.form.get('goal'))
        accounts = load_json(DATA_FILE)

        # Ensure user data exists
        if session['user'] not in accounts:
            accounts[session['user']] = {"accounts": [], "monthly_expenses": {}}

        user_data = accounts[session['user']]
        user_accounts = user_data.get("accounts", [])

        new_account = {
            "account_id": len(user_accounts) + 1,
            "account_name": account_name,
            "balance": initial_balance,
            "Goal": goal,
            "transactions": []  # Ensure transactions key exists
        }

        user_accounts.append(new_account)
        user_data["accounts"] = user_accounts  # Update back to user data
        accounts[session['user']] = user_data  # Save back to main data

        save_json(DATA_FILE, accounts)
        return redirect(url_for('dashboard'))

    return render_template('create_account.html')


@app.route('/delete_account/<int:account_id>', methods=['POST'])
def delete_account(account_id):
    if 'user' not in session:
        return redirect(url_for('index'))

    accounts = load_json(DATA_FILE)
    user_accounts = accounts.get(session['user'], [])
    account_to_delete = next((acc for acc in user_accounts if acc['account_id'] == account_id), None)

    if account_to_delete:
        user_accounts.remove(account_to_delete)
        accounts[session['user']] = user_accounts
        save_json(DATA_FILE, accounts)

    return redirect(url_for('dashboard'))

@app.route('/transactions/<int:account_id>', methods=['GET', 'POST'])
def transactions(account_id):
    if 'user' not in session:
        return redirect(url_for('index'))
    
    accounts = load_json(DATA_FILE)
    user_data = accounts.get(session['user'], {"accounts": []})  # Ensure correct structure
    user_accounts = user_data.get("accounts", [])  # Get accounts list safely

    # Ensure user_accounts is a list before iterating
    if not isinstance(user_accounts, list):
        return "Invalid data format", 500
    
    account = next((acc for acc in user_accounts if acc.get('account_id') == account_id), None)

    if not account:
        return "Account not found", 404

    if 'transactions' not in account:
        account['transactions'] = []

    if request.method == 'POST':
        transaction_type = request.form.get('transaction_type')
        amount = float(request.form.get('amount'))

        if transaction_type == 'deposit':
            account['balance'] += amount
        elif transaction_type == 'withdraw':
            if account['balance'] >= amount:
                account['balance'] -= amount
            else:
                return "Insufficient funds", 400

        transaction = {
            "type": transaction_type,
            "amount": amount,
            "date": datetime.now().strftime("%Y-%m-%d"),  # Stores date in YYYY-MM-DD format
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
        }
        account['transactions'].append(transaction)
        save_json(DATA_FILE, accounts)  # Save updated data back to file
        return redirect(url_for('dashboard'))

    return render_template('transactions.html', account=account)

@app.route('/transaction_history')
def transaction_history():
    if 'user' not in session:
        return redirect(url_for('index'))

    username = session['user']
    accounts = load_json(DATA_FILE)

    user_data = accounts.get(username, {"accounts": [], "monthly_expenses": {}})
    
    transactions = []
    account_names = []

    for account in user_data.get("accounts", []):
        account_name = account.get("account_name", "Unknown Account")  # Ensure account name exists
        account_names.append(account_name)
        
        for transaction in account.get("transactions", []):
            transactions.append({
                "date": transaction.get("date", "Unknown Date"),  # Ensure date is included
                "account_name": account_name,
                "type": transaction.get("type", "N/A"),
                "amount": transaction.get("amount", 0),
                "description": transaction.get("description", "No description")
            })

    return render_template(
        'transaction_history.html', 
        transactions=transactions, 
        account_names=account_names
    )



# Monthly Expense Tracking
@app.route('/met', methods=['GET', 'POST'])
def MET():
    if 'user' not in session:
        return redirect(url_for('index'))

    username = session['user']
    accounts = load_json(DATA_FILE)

    if username not in accounts:
        accounts[username] = {"accounts": [], "monthly_expenses": {}}

    user_data = accounts[username]

    if request.method == 'POST':
        category = request.form['category']
        amount = float(request.form['amount'])
        description = request.form['description']
        date = datetime.now().strftime("%Y-%m")

        if 'monthly_expenses' not in user_data:
            user_data['monthly_expenses'] = {}

        if date not in user_data['monthly_expenses']:
            user_data['monthly_expenses'][date] = []

        user_data['monthly_expenses'][date].append({
            "category": category,
            "amount": amount,
            "description": description,
            "date": datetime.now().strftime("%Y-%m-%d")
        })

        save_json(DATA_FILE, accounts)

    selected_month = request.args.get("month", datetime.now().strftime("%Y-%m"))
    expenses = user_data.get('monthly_expenses', {}).get(selected_month, [])

    return render_template('met.html', expenses=expenses, selected_month=selected_month)




# Track Progress Route

@app.route('/track_progress/<int:account_id>')
def track_progress(account_id):
    if 'user' not in session:
        return redirect(url_for('index'))

    username = session['user']
    accounts = load_accounts()
    
    # Ensure the user has data
    user_data = accounts.get(username, {"accounts": []})
    user_accounts = user_data.get("accounts", [])

    # Find the specific account
    account = next((acc for acc in user_accounts if acc.get('account_id') == account_id), None)

    if not account:
        return "Account not found", 404

    # Fetch transactions
    transactions = account.get("transactions", [])

    # Calculate progress
    goal = account.get("Goal", 0)
    balance = account.get("balance", 0)
    progress_percentage = min((balance / goal) * 100, 100) if goal else 0

    # Estimate completion time
    monthly_savings = [t["amount"] for t in transactions if t["type"] == "deposit"]
    avg_savings = sum(monthly_savings) / len(monthly_savings) if monthly_savings else 0
    months_remaining = ((goal - balance) / avg_savings) if avg_savings else "N/A"

    # Encouraging message
    if progress_percentage < 50:
        message = "Keep going! You're making steady progress."
    elif progress_percentage < 90:
        message = "You're almost there! Keep pushing!"
    else:
        message = "Congratulations! You're very close to your goal!"

    # Prepare savings trend
    months = sorted(set(t["date"][:7] for t in transactions))  # Extract YYYY-MM
    savings_data = [
        sum(t["amount"] for t in transactions if t["date"].startswith(month)) for month in months
    ]

    return render_template(
        "track_progress.html",
        account=account,
        progress_percentage=progress_percentage,
        message=message,
        months=months,
        savings_data=savings_data,
    )

@app.route('/analyze_met', methods=['GET'])
def analyze_met():
    if 'user' not in session:
        return redirect(url_for('index'))

    selected_month = request.args.get('month')
    if not selected_month:
        return "Please select a valid month", 400

    accounts = load_json(DATA_FILE)
    user_data = accounts.get(session['user'], {"monthly_expenses": {}})

    expenses_by_category = defaultdict(float)

    # Extract transactions for the selected month
    monthly_expenses = user_data.get("monthly_expenses", {}).get(selected_month, [])

    for expense in monthly_expenses:
        category = expense.get('category', 'Other')
        expenses_by_category[category] += expense['amount']

    return render_template('expense_chart.html', expenses=dict(expenses_by_category), month=selected_month)

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
