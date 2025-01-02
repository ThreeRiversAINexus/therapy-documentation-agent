import os
import pytest

@pytest.fixture(autouse=True)
def mock_env_vars(monkeypatch):
    """Mock environment variables for testing."""
    monkeypatch.setenv('OPENAI_API_KEY', 'test-key-123')
    monkeypatch.setenv('DATABASE', ':memory:')
    monkeypatch.setenv('PYTHONPATH', '/app')
    monkeypatch.setenv('TOKENIZERS_PARALLELISM', 'true')
    monkeypatch.setenv('LLAMA_INDEX_CACHE_DIR', '/app/data/llama_index_cache')

@pytest.fixture(autouse=True)
def mock_openai():
    """Mock OpenAI API calls."""
    import openai
    openai.api_key = 'test-key-123'
    return openai
