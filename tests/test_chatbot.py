import pytest
from unittest.mock import Mock, patch, MagicMock
from bot.core import TherapyDocumentationBot
from llama_index.llms import ChatMessage, MessageRole, ChatResponse

@pytest.fixture
def mock_openai():
    with patch('llama_index.llms.OpenAI') as mock:
        mock_instance = Mock()
        mock_instance.chat.return_value = ChatResponse(
            message=ChatMessage(
                role=MessageRole.ASSISTANT,
                content="Selected category: Sleep (Fitbit data / Dreaming). What would you like to document?"
            )
        )
        mock.return_value = mock_instance
        yield mock

@pytest.fixture
def mock_tools():
    mock_instance = Mock()
    mock_instance.get_tools.return_value = [
        {
            'name': 'set_category_observations',
            'description': 'Set observations for a therapy category',
            'func': lambda **kwargs: "Observations recorded"
        },
        {
            'name': 'set_category_next_steps',
            'description': 'Set next steps for a therapy category',
            'func': lambda **kwargs: "Next steps recorded"
        },
        {
            'name': 'add_category_notes',
            'description': 'Add notes to a therapy category',
            'func': lambda **kwargs: "Notes added"
        }
    ]
    mock_instance.get_categories.return_value = [
        {
            "id": "sleep",
            "name": "Sleep (Fitbit data / Dreaming)"
        }
    ]
    mock_instance.current_data = {}
    mock_instance.notes = {}
    mock_instance.current_category = None
    
    # Set up mock responses for tool methods
    mock_instance.set_category_observations = Mock(return_value="Observations recorded")
    mock_instance.set_category_next_steps = Mock(return_value="Next steps recorded")
    mock_instance.add_category_notes = Mock(return_value="Notes added")
    mock_instance.get_category_summary = Mock(return_value={
        'observations': 'Test observations',
        'next_steps': 'Test next steps',
        'notes': 'Test notes'
    })
    mock_instance.clear_category = Mock()
    
    return mock_instance

@pytest.fixture
def chatbot(mock_openai, mock_tools):
    with patch('bot.core.TherapyDocTools', return_value=mock_tools):
        bot = TherapyDocumentationBot(test_mode=True)
        return bot

def test_chatbot_initialization(chatbot):
    """Test that chatbot initializes with correct components"""
    assert chatbot.tools is not None
    assert chatbot.agent is not None
    assert len(chatbot.llama_tools) > 0

def test_start_documentation(chatbot):
    """Test starting a new documentation session"""
    response = chatbot.start_documentation()
    assert isinstance(response, dict)
    assert "response" in response
    assert "What's up?" in response["response"]
    assert "How have you been doing?" in response["response"]

def test_process_message(chatbot):
    """Test processing user message"""
    response = chatbot.process_message("I slept well last night")
    assert isinstance(response, dict)
    assert "response" in response

def test_process_empty_message(chatbot):
    """Test handling empty message"""
    response = chatbot.process_message("")
    assert isinstance(response, dict)
    assert "response" in response
    assert "I'm sorry" in response["response"]
    assert "tell me more" in response["response"]

def test_process_message_error(chatbot, mock_openai):
    """Test error handling in message processing"""
    # Make the agent raise an exception
    mock_openai.return_value.chat.side_effect = Exception("Test error")
    
    response = chatbot.process_message("tell me about my progress")
    assert isinstance(response, dict)
    assert "response" in response
    assert "Error" in response["response"]

def test_tools_functionality(chatbot):
    """Test the underlying tools functionality"""
    category_id = "sleep"
    
    # Test setting observations
    result = chatbot.tools.set_category_observations(category_id=category_id, observations="Slept 8 hours")
    assert "Observations recorded" in result
    
    # Test setting next steps
    result = chatbot.tools.set_category_next_steps(category_id=category_id, next_steps="Maintain schedule")
    assert "Next steps recorded" in result
    
    # Test adding notes
    result = chatbot.tools.add_category_notes(category_id=category_id, notes="Important note")
    assert "Notes added" in result
    
    # Test getting summary
    result = chatbot.tools.get_category_summary(category_id=category_id)
    assert isinstance(result, dict)
    assert 'observations' in result
    assert 'next_steps' in result
    assert 'notes' in result

def test_tools_get_categories(chatbot):
    """Test getting available categories"""
    categories = chatbot.tools.get_categories()
    assert isinstance(categories, list)
    assert len(categories) > 0
    assert any(cat['name'] == "Sleep (Fitbit data / Dreaming)" for cat in categories)

def test_clear_data(chatbot):
    """Test clearing all documentation data"""
    chatbot.clear_data()
    # Verify clear_category was called for each category
    assert chatbot.tools.clear_category.call_count == len(chatbot.tools.get_categories())
