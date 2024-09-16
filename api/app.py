from flask import Flask, render_template, redirect, url_for, request, session, jsonify
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.secret_key = 'supersecretkey'
socketio = SocketIO(app)

# Mocked user database
users = {
    'vinicius': {'password': '123456', 'status': 'offline'},
    'usuario': {'password': '123456', 'status': 'offline'},
    'eduardo': {'password': '123456', 'status': 'offline'},
    'alexandre_gilz': {'password': '123456', 'status': 'online'},
}

# Lista de contatos do usuário
contacts = {
    'vinicius': ['usuario','alexandre_gilz'],
    'usuario': ['vinicius','eduardo'],
    'eduardo': ['vinicius','usuario'],
}

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].lower()
        password = request.form['password'].lower()
        
        if username in users and users[username]['password'] == password:
            session['username'] = username
            users[username]['status'] = 'online'
            return redirect(url_for('home'))
        else:
            return render_template('login.html', error='Invalid Credentials')

    return render_template('login.html')

@app.route('/home')
def home():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    username = session['username']
    user_contacts = contacts.get(username, [])
    online_contacts = {u: users[u] for u in user_contacts if users[u]['status'] == 'online'}
    offline_contacts = {u: users[u] for u in user_contacts if users[u]['status'] == 'offline'}

    return render_template('home.html', username=username, online_contacts=online_contacts, offline_contacts=offline_contacts)

@app.route('/logout')
def logout():
    username = session['username']
    users[username]['status'] = 'offline'
    
    socketio.emit('user_disconnected', {'username': username}, to='/')
    
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/get_status')
def get_status():
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    username = session['username']
    user_contacts = contacts.get(username, [])
    status = {
        'online': [u for u in user_contacts if users[u]['status'] == 'online'],
        'offline': [u for u in user_contacts if users[u]['status'] == 'offline']
    }
    return jsonify(status)

@socketio.on('connect')
def handle_connect():
    username = session.get('username')
    if username:
        users[username]['status'] = 'online'
        emit('user_connected', {'username': username}, to='/', include_self=False)

@socketio.on('disconnect')
def handle_disconnect():
    username = session.get('username')
    if username:
        users[username]['status'] = 'offline'
        emit('user_disconnected', {'username': username}, to='/', include_self=False)

chat_history = {}

@socketio.on('send_message')
def handle_send_message(data):
    recipient = data['to']
    message = data['message']
    sender = session.get('username')

    if recipient in users:
        if sender not in chat_history:
            chat_history[sender] = []
        if recipient not in chat_history:
            chat_history[recipient] = []
        
        chat_history[sender].append({'from': sender, 'message': message})
        chat_history[recipient].append({'from': sender, 'message': message})
        
        emit('receive_message', {'from': sender, 'message': message}, to='/')

@app.route('/get_chat_history')
def get_chat_history():
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    current_user = session['username']
    with_user = request.args.get('with')

    if not with_user or with_user not in users:
        return jsonify({'error': 'Invalid user'}), 400

    # Retrieve chat history (simple example using a dictionary)
    history = chat_history.get(current_user, [])
    relevant_history = [msg for msg in history if msg['from'] == with_user or msg['from'] == current_user]

    return jsonify({'history': relevant_history})

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', debug=True)