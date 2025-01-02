import os
import tempfile
import pytest
from unittest.mock import Mock, patch
from passlib.hash import bcrypt
from app import app, init_db, get_db_connection

# Use an in-memory database for testing
TEST_DB = ":memory:"

class MockTherapyDocumentationBot:
    """Mock implementation of TherapyDocumentationBot for testing"""
    def __init__(self):
        self.tools = Mock(current_category=None)
        self.current_data = {}
        self.notes = {}
        self.agent_executor = Mock()
        self.service_context = Mock()
        self.index = Mock()
        self.langchain_tools = []
        self.system_prompt = ""

    def start_documentation(self):
        return {
            "response": "Hey! What's up? How have you been doing?"
        }

    def process_message(self, message):
        # Skip all the agent_executor logic and just return the mock response
        return {
            "response": "I understand you're having trouble sleeping."
        }

    def get_current_data(self):
        return self.current_data

    def get_notes(self):
        return self.notes

    def _create_agent(self, llm):
        return Mock()

@pytest.fixture
def mock_chatbot():
    """Mock the chatbot to return structured responses"""
    with patch('app.chatbot', new_callable=MockTherapyDocumentationBot) as mock:
        yield mock

@pytest.fixture
def client(mock_chatbot):
    """
    Pytest fixture to configure the app to use an in-memory database
    and return a test client.
    """
    app.config["TESTING"] = True
    app.config["DATABASE"] = TEST_DB
    
    with app.app_context():
        # Initialize database and get connection
        conn = init_db()
        cursor = conn.cursor()
        
        # Create test user
        username = "testuser"
        plain_password = "testpass"
        hashed_password = bcrypt.hash(plain_password)
        
        cursor.execute("DELETE FROM users WHERE username = ?", (username,))
        cursor.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)", 
            (username, hashed_password)
        )
        conn.commit()
        
        with app.test_client() as test_client:
            yield test_client

def login(client, username="testuser", password="testpass"):
    """Helper function to log in"""
    return client.post('/login', data={
        'username': username,
        'password': password
    }, follow_redirects=True)

def test_auth_success(client):
    """Ensure that valid credentials allow access to the index page."""
    response = login(client)
    assert response.status_code == 200
    assert b"Therapy Documentation Chat" in response.data

def test_auth_failure(client):
    """Ensure that invalid credentials are rejected."""
    response = login(client, password="wrongpass")
    assert b"Invalid username or password" in response.data

def test_increment_and_override(client):
    """Test that incrementing and overriding entry counts works."""
    login(client)

    # Test incrementing
    response = client.post("/increment/Journaling")
    assert response.status_code == 200
    data = response.get_json()
    assert data["count"] == 1

    # Test incrementing again
    response = client.post("/increment/Journaling")
    assert response.status_code == 200
    data = response.get_json()
    assert data["count"] == 2

    # Test overriding
    response = client.post("/override/Journaling/5")
    assert response.status_code == 200
    data = response.get_json()
    assert data["count"] == 5

def test_submit_updates_history(client):
    """Test that submitting documentation updates the history."""
    login(client)

    # Submit some documentation
    data = {
        "category": "Sleep",
        "observations": "Slept well",
        "next_steps": "Keep same schedule",
        "notes": "Feeling refreshed"
    }
    response = client.post("/submit", json=data)
    assert response.status_code == 200

    # Check history
    response = client.get("/history")
    assert response.status_code == 200
    assert b"Sleep" in response.data
    assert b"Slept well" in response.data

def test_joplin_integration(client):
    """Test that Joplin integration works if configured."""
    login(client)

    # Mock Joplin environment variable
    os.environ["JOPLIN_TOKEN"] = "test_token"

    try:
        # Submit documentation
        data = {
            "category": "Sleep",
            "observations": "Slept well",
            "next_steps": "Keep same schedule",
            "notes": "Feeling refreshed"
        }
        response = client.post("/submit", json=data)
        assert response.status_code == 200

    finally:
        # Clean up
        if "JOPLIN_TOKEN" in os.environ:
            del os.environ["JOPLIN_TOKEN"]

def test_chat_interface(client, mock_chatbot):
    """Test chat interface endpoints."""
    login(client)

    # Test GET /chat-interface
    response = client.get("/chat-interface")
    assert response.status_code == 200

    # Test POST /chat-message
    
    response = client.post("/chat-message", json={"message": "Hello"})
    assert response.status_code == 200
    data = response.get_json()
    print("\nDebug - Response data:")
    print(f"Full response data: {data}")
    print(f"Message field: {data.get('message')}")
    
    assert "message" in data, "Response missing 'message' field"
    assert isinstance(data["message"], dict), f"Message not a dict: {type(data['message'])}"
    assert "response" in data["message"], f"Message missing 'response' field: {data['message']}"
    assert data["message"] == {"response": "I understand you're having trouble sleeping."}

    # Test GET /start-chat
    response = client.get("/start-chat")
    assert response.status_code == 200
    assert response.data.decode() == "Hey! What's up? How have you been doing?"

def test_categories_endpoint(client):
    """Test categories endpoint."""
    login(client)

    response = client.get("/categories")
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert all(isinstance(cat, dict) for cat in data)
    assert all("id" in cat and "name" in cat for cat in data)
