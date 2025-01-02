import os
import sqlite3
from flask import Flask, request, jsonify, session, g, render_template
from flask_cors import CORS
from werkzeug.security import check_password_hash
from datetime import datetime, timedelta
from bot.core import TherapyDocumentationBot
from llama_index.core.base.llms.types import ChatMessage, MessageRole

app = Flask(__name__)
CORS(app)

# Configure Flask app
app.config.update(
    SECRET_KEY='dev',
    DATABASE=os.environ.get('DATABASE', 'therapy.db'),
    SESSION_COOKIE_HTTPONLY=True,
    PERMANENT_SESSION_LIFETIME=timedelta(days=7)
)

def get_db_connection():
    """Get database connection"""
    if 'db' not in g:
        g.db = sqlite3.connect(
            app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row
    return g.db

def init_db():
    """Initialize the database"""
    db = get_db_connection()
    with app.open_resource('schema.sql') as f:
        db.executescript(f.read().decode('utf8'))

def get_bot():
    """Get or create bot instance"""
    if 'bot' not in g:
        g.bot = TherapyDocumentationBot()
        # Restore chat history from session if available
        if 'chat_history' in session:
            g.bot.chat_history = [
                ChatMessage(
                    role=MessageRole(msg['role']),
                    content=msg['content']
                )
                for msg in session['chat_history']
            ]
    return g.bot

@app.route('/start-chat', methods=['GET'])
def start_chat():
    """Start a new chat session"""
    if 'username' not in session:
        return jsonify({"error": "Not logged in"}), 401
    
    bot = get_bot()
    response = bot.start_documentation()
    return jsonify(response)

@app.route('/chat-message', methods=['POST'])
def chat_message():
    """Process a chat message"""
    if 'username' not in session:
        return jsonify({"error": "Not logged in"}), 401
    
    data = request.get_json()
    if not data or 'message' not in data:
        return jsonify({"error": "No message provided"}), 400
    
    bot = get_bot()
    response = bot.process_message(data['message'])
    # Save updated chat history to session in a serializable format
    session['chat_history'] = [
        {
            'role': msg.role.value,  # Convert enum to string
            'content': msg.content
        }
        for msg in bot.chat_history
    ]
    return jsonify(response)

@app.route('/categories', methods=['GET'])
def get_categories():
    """Get available categories"""
    if 'username' not in session:
        return jsonify({"error": "Not logged in"}), 401
    
    bot = get_bot()
    categories = bot.tools.get_categories()
    return jsonify(categories)

@app.route('/')
def index():
    """Render the form view"""
    if 'username' not in session:
        return render_template('login.html')
    return render_template('form.html')

@app.route('/form')
def form():
    """Render the form view"""
    if 'username' not in session:
        return render_template('login.html')
    return render_template('form.html')

@app.route('/chat')
def chat():
    """Render the chat view"""
    if 'username' not in session:
        return render_template('login.html')
    return render_template('chat.html')

@app.route('/get-all-data')
def get_all_data():
    """Get all data for all categories"""
    if 'username' not in session:
        return jsonify({"error": "Not logged in"}), 401
    
    bot = get_bot()
    all_data = {}
    
    for category in bot.tools.get_categories():
        try:
            all_data[category['id']] = bot.tools.get_category_summary(category_id=category['id'])
        except Exception as e:
            print(f"Error getting data for category {category['id']}: {e}")
            continue
    
    return jsonify(all_data)

@app.route('/submit', methods=['POST'])
def submit_documentation():
    """Submit documentation for a category"""
    if 'username' not in session:
        return jsonify({"error": "Not logged in"}), 401
    
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    bot = get_bot()
    
    try:
        # Handle section observations
        if 'category_id' in data and 'section_name' in data and 'observations' in data:
            bot.tools.set_category_section_observations(
                category_id=data['category_id'],
                section_name=data['section_name'],
                observations=data['observations']
            )
        # Handle next steps
        elif 'category_id' in data and 'next_steps' in data:
            bot.tools.set_category_next_steps(
                category_id=data['category_id'],
                next_steps=data['next_steps']
            )
        # Handle notes
        elif 'category_id' in data and 'notes' in data:
            bot.tools.add_category_notes(
                category_id=data['category_id'],
                notes=data['notes']
            )
        else:
            return jsonify({"error": "Invalid data format"}), 400
        
        return jsonify({"status": "success"})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        print(f"Error in submit_documentation: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/login', methods=['POST'])
def login():
    """Log in a user"""
    data = request.get_json()
    if not data or 'username' not in data or 'password' not in data:
        return jsonify({"error": "Username and password required"}), 400
    
    # For development, allow auto-login with test user
    if os.environ.get('AUTO_LOGIN') == 'true' and data['username'] == 'test':
        session['username'] = data['username']
        return jsonify({"status": "success"})
    
    # For now, just check against hardcoded test user
    if data['username'] == 'test' and data['password'] == 'test123':
        session['username'] = data['username']
        session.permanent = True  # Make session persistent
        return jsonify({"status": "success"})
    
    return jsonify({"error": "Invalid username or password"}), 401

@app.route('/delete-entry/<int:entry_id>', methods=['DELETE'])
def delete_entry(entry_id):
    """Delete a documentation entry"""
    if 'username' not in session:
        return jsonify({"error": "Not logged in"}), 401
    
    db = get_db_connection()
    try:
        db.execute('DELETE FROM category_sections WHERE id = ?', (entry_id,))
        db.commit()
        return jsonify({"status": "success"})
    except Exception as e:
        print(f"Error deleting entry: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/logout', methods=['POST'])
def logout():
    """Log out the current user"""
    session.pop('username', None)
    session.pop('chat_history', None)  # Also clear chat history on logout
    return jsonify({"status": "success"})

@app.teardown_appcontext
def teardown_db(exception):
    """Clean up database connection"""
    db = g.pop('db', None)
    if db is not None:
        db.close()
    
    bot = g.pop('bot', None)
    if bot is not None:
        # Clean up any bot resources if needed
        pass

def create_test_user():
    """Create default test user"""
    db = get_db_connection()
    try:
        db.execute(
            "INSERT INTO user (username, password) VALUES (?, ?)",
            ("test", "pbkdf2:sha256:260000$test123")
        )
        db.commit()
        print("User 'test' created successfully!")
    except sqlite3.IntegrityError:
        print("User 'test' already exists")
    except Exception as e:
        print(f"Error creating test user: {e}")
