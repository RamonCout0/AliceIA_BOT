# Alice AI System - Refactored Architecture

## Project Structure

```
alice/
├── core/                 # Core infrastructure components
│   ├── config.py        # Configuration management
│   ├── logger.py        # Structured logging
│   ├── error_handler.py # Error handling and retry logic
│   └── schema_validator.py # API response validation
├── components/          # Main system components
│   ├── vision_engine.py # Groq/Llama Vision integration
│   ├── discord_bot.py   # Discord/Gemini integration
│   ├── gamepad_controller.py # Virtual gamepad control
│   ├── history_manager.py # Persistent history storage
│   ├── rate_limiter.py  # API rate limiting
│   └── macro_system.py  # Gameplay macro system
├── utils/              # Utility functions
│   └── models.py       # Data models and dataclasses
└── __init__.py

tests/
├── unit/               # Unit tests
├── integration/        # Integration tests
├── property/          # Property-based tests
└── conftest.py        # Shared fixtures

main.py                # Entry point (AliceSystem orchestrator)
requirements.txt       # Python dependencies
setup.py              # Package setup
pytest.ini            # Test configuration
.env.example          # Environment variables template
.gitignore            # Git ignore rules
```

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your API keys
```

### 3. Run Tests

```bash
# All tests
pytest

# Unit tests only
pytest tests/unit -v

# Property-based tests
pytest tests/property -v

# With coverage
pytest --cov=alice --cov-report=html
```

### 4. Run Application

```bash
python main.py
```

## Architecture Overview

The refactored Alice system follows a clean architecture with:

- **Dependency Injection**: All components receive dependencies through constructors
- **Clear Interfaces**: Each component has well-defined public methods
- **Error Handling**: Comprehensive retry logic with exponential backoff
- **Logging**: Structured JSON logging to console and file
- **Persistence**: History stored on disk with crash recovery
- **Testing**: Unit, integration, and property-based tests

## Key Components

### Core Infrastructure

- **ConfigManager**: Secure environment variable loading and validation
- **Logger**: Structured JSON logging with file rotation
- **ErrorHandler**: Retry logic with exponential backoff
- **SchemaValidator**: API response validation with Pydantic

### Main Components

- **VisionEngine**: Groq/Llama Vision for gameplay analysis
- **DiscordBot**: Google Gemini for Discord chat
- **GamepadController**: Thread-safe virtual gamepad control
- **HistoryManager**: Persistent conversation/gameplay history
- **RateLimiter**: API quota management
- **MacroSystem**: Predefined gameplay sequences

### Orchestrator

- **AliceSystem**: Single entry point managing all components

## Development

### Code Style

- Follow PEP 8
- Use type hints for all functions
- Document public methods with docstrings

### Testing

- Write unit tests for all new functions
- Add property-based tests for critical logic
- Aim for 80%+ code coverage
- All tests must pass before committing

### Git Workflow

1. Create feature branch from `dev`
2. Implement feature with tests
3. Ensure all tests pass
4. Create pull request to `dev`
5. Merge to `main` after review

## Next Steps

1. Implement Config Manager (Task 2)
2. Implement Logger (Task 3)
3. Implement Error Handler (Task 4)
4. Continue with remaining components...

See `.kiro/specs/alice-refactor/tasks.md` for detailed implementation plan.
