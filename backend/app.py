from flask import Flask, request, jsonify

app = Flask(__name__)

# Sample in-memory data storage
users = []
expenses = []

@app.route('/register', methods=['POST'])
def register_user():
    data = request.json
    users.append(data)
    return jsonify({'message': 'User registered successfully!'}), 201

@app.route('/add_expense', methods=['POST'])
def add_expense():
    data = request.json
    expenses.append(data)
    return jsonify({'message': 'Expense added successfully!'}), 201

@app.route('/expenses', methods=['GET'])
def get_expenses():
    return jsonify(expenses), 200

if __name__ == '__main__':
    app.run(debug=True)
