from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for, session
import json
import os
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "your_secret_key"  # Replace with a strong secret key

# File paths
USERS_FILE = 'users.json'
DATA_FILE = 'accounts_data.json'

# Utility: Load JSON data
# Utility: Load JSON data
# Utility: Load JSON data
def load_json(file_path):
    if not os.path.exists(file_path):
        with open(file_path, 'w') as f:
            json.dump({}, f)  # Initialize with an empty dictionary
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError:
        # Reset the file to an empty dictionary if corrupted
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
        return False  # User already exists
    hashed_password = generate_password_hash(password)
    users[username] = {'password': hashed_password}
    save_json(USERS_FILE, users)
    return True

def authenticate_user(username, password):
    users = load_json(USERS_FILE)
    if username in users and check_password_hash(users[username]['password'], password):
        return True
    return False

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

    accounts = load_json(DATA_FILE)
    user_accounts = accounts.get(session['user'], [])
    return render_template('dashboard.html', accounts=user_accounts)


@app.route('/create_account', methods=['GET', 'POST'])
def create_account():
    if 'user' not in session:
        return redirect(url_for('index'))

    if request.method == 'POST':
        account_name = request.form.get('account_name')
        initial_balance = float(request.form.get('initial_balance'))

        accounts = load_json(DATA_FILE)
        user_accounts = accounts.get(session['user'], [])

        new_account = {
            "account_id": len(user_accounts) + 1,
            "account_name": account_name,
            "balance": initial_balance
        }

        user_accounts.append(new_account)
        accounts[session['user']] = user_accounts
        save_json(DATA_FILE, accounts)
        return redirect(url_for('dashboard'))

    return render_template('create_account.html')

@app.route('/delete_account/<int:account_id>', methods=['POST'])
def delete_account(account_id):
    if 'user' not in session:
        return redirect(url_for('index'))

    # Load the current account data
    accounts = load_json(DATA_FILE)

    # Get the accounts for the logged-in user
    user_accounts = accounts.get(session['user'], [])

    # Find the account to delete
    account_to_delete = next((acc for acc in user_accounts if acc['account_id'] == account_id), None)

    if account_to_delete:
        # Remove the account from the user's list
        user_accounts.remove(account_to_delete)
        # Update the accounts data
        accounts[session['user']] = user_accounts
        save_json(DATA_FILE, accounts)

    return redirect(url_for('dashboard'))


@app.route('/transactions/<int:account_id>', methods=['GET', 'POST'])
def transactions(account_id):
    if 'user' not in session:
        return redirect(url_for('index'))
    
    accounts = load_json(DATA_FILE)
    user_accounts = accounts.get(session['user'], [])
    account = next((acc for acc in user_accounts if acc['account_id'] == account_id), None)
    
    if not account:
        return "Account not found", 404
    
    if 'transactions' not in account:
        account['transactions'] = []  # Ensure transactions list exists
    
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
        
        # Store the transaction
        transaction = {
            "type": transaction_type,
            "amount": amount,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
        }
        account['transactions'].append(transaction)
        save_json(DATA_FILE, accounts)
        return redirect(url_for('dashboard'))
    
    return render_template('transactions.html', account=account)

@app.route('/transaction_history', methods=['GET'])
def transaction_history():
    if 'user' not in session:
        return redirect(url_for('index'))
    
    accounts = load_json(DATA_FILE)
    user_accounts = accounts.get(session['user'], [])
    
    # Collect all transactions
    all_transactions = []
    for acc in user_accounts:
        for txn in acc.get("transactions", []):
            txn["account_name"] = acc["account_name"]  # Add account name for reference
            all_transactions.append(txn)
    
    # Optional: Filtering by account_id
    account_id = request.args.get("account_id")
    if account_id:
        all_transactions = [txn for txn in all_transactions if str(txn.get("account_id")) == account_id]
    
    return render_template('transaction_history.html', transactions=all_transactions, accounts=user_accounts)

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
