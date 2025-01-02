# Personal Metrics Agent

A Flask-based web application for tracking personal therapy metrics and documentation with an AI-powered chatbot interface.

## Features

- Basic authentication for user accounts
- Track metrics across multiple therapy categories
- AI-powered chatbot for guided documentation
- History view of all documentation entries
- Increment and override counters for each category
- Notes support for additional context

## Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd personal_metrics_agent
```

2. Run with Docker using the provided operations script:
```bash
# Run the main application
./docker-ops.sh app

# Run in development mode with auto-reload
./docker-ops.sh dev

# Run tests
./docker-ops.sh test

# Run CLI interface
./docker-ops.sh cli
```

The docker-ops.sh script provides efficient Docker image management:
- Automatically caches images based on code changes
- Reuses existing images when code hasn't changed
- Maintains only the latest versions to save disk space
- Cleans up old/dangling images automatically

3. Create a user account:
```bash
# Get the container ID
CONTAINER_ID=$(docker ps -qf "name=personal-metrics-agent")

# Create user
docker exec -it $CONTAINER_ID python create_user.py <username> <password>
```

## Environment Variables

- `DATABASE`: Path to SQLite database file (default: therapy.db)
- `OPENAI_API_KEY`: Your OpenAI API key for the chatbot
- `JOPLIN_TOKEN`: (Optional) Joplin API token for integration
- `LLAMA_INDEX_CACHE_DIR`: Directory for LlamaIndex cache

## Development

The docker-ops.sh script supports different modes for development:

1. Development mode with auto-reload:
```bash
./docker-ops.sh dev
```

2. Run tests:
```bash
./docker-ops.sh test
```

3. CLI interface:
```bash
./docker-ops.sh cli
```

## Project Structure

- `app.py`: Main Flask application
- `chatbot.py`: AI chatbot implementation using LlamaIndex and LangChain
- `tools.py`: Therapy documentation tools and utilities
- `categories.py`: Therapy category definitions
- `templates/`: HTML templates
  - `index.html`: Main dashboard
  - `chat.html`: Chatbot interface
  - `history.html`: Documentation history
- `tests/`: Test files
  - `test_app.py`: Application tests
  - `test_chatbot.py`: Chatbot tests

## API Endpoints

- `/`: Main dashboard
- `/chat-interface`: Chatbot interface
- `/history`: Documentation history
- `/categories`: List available categories
- `/increment/<category>`: Increment category count
- `/override/<category>/<count>`: Set category count
- `/chat-message`: Send message to chatbot
- `/start-chat`: Start new chat session
- `/submit`: Submit documentation

## Testing

Run tests with:
```bash
pytest
```

## License

MIT License
