# Design Document: Alice AI Refactor

## Overview

Alice is being refactored from a fragmented architecture into a unified, robust system. The new architecture separates concerns into distinct components with clear interfaces, implements comprehensive error handling with retry logic, adds structured logging and persistence, and includes property-based testing for critical functionality.

The refactored system consists of:
- **Core Orchestrator** (main.py) - Single entry point managing component lifecycle
- **Vision Engine** - Groq/Llama Vision integration for gameplay analysis
- **Discord Bot** - Google Gemini integration for chat
- **Gamepad Controller** - Thread-safe virtual gamepad interface
- **History Manager** - Persistent conversation and gameplay history
- **Error Handler** - Retry logic, timeout management, error recovery
- **Config Manager** - Secure environment variable management
- **Logger** - Structured JSON logging with multiple outputs
- **Schema Validator** - API response validation
- **Macro System** - Predefined gameplay sequences with validation

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Alice_System (main.py)                   │
│                   (Orchestrator/Lifecycle)                  │
└────────────────────────┬────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
        ▼                ▼                ▼
   ┌─────────┐    ┌──────────┐    ┌──────────────┐
   │ Vision  │    │ Discord  │    │ Gamepad      │
   │ Engine  │    │ Bot      │    │ Controller   │
   └────┬────┘    └────┬─────┘    └──────┬───────┘
        │              │                 │
        └──────────────┼─────────────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
        ▼              ▼              ▼
   ┌─────────┐  ┌──────────┐  ┌──────────────┐
   │ History │  │ Error    │  │ Config       │
   │ Manager │  │ Handler  │  │ Manager      │
   └────┬────┘  └────┬─────┘  └──────┬───────┘
        │            │               │
        └────────────┼───────────────┘
                     │
        ┌────────────┼────────────┐
        │            │            │
        ▼            ▼            ▼
   ┌─────────┐  ┌──────────┐  ┌──────────────┐
   │ Logger  │  │ Schema   │  │ Macro        │
   │         │  │ Validator│  │ System       │
   └─────────┘  └──────────┘  └──────────────┘
```

## Components and Interfaces

### 1. Core Orchestrator (main.py)

**Responsibility**: Initialize all components in correct order, manage lifecycle, handle graceful shutdown.

**Interface**:
```python
class AliceSystem:
    def __init__(self, config: Config):
        # Initialize all components with dependency injection
        pass
    
    def start(self) -> None:
        # Start all components in order
        pass
    
    def stop(self) -> None:
        # Stop all components gracefully
        pass
    
    def is_running(self) -> bool:
        # Check if system is running
        pass
```

**Key Design Decisions**:
- Single entry point for all initialization
- Dependency injection for all components
- Graceful degradation when optional components fail
- Clear initialization order: Config → Logger → History → Error Handler → Vision/Discord/Gamepad

### 2. Vision Engine

**Responsibility**: Analyze screenshots using Groq/Llama Vision, generate gameplay decisions.

**Interface**:
```python
class VisionEngine:
    def __init__(self, config: Config, logger: Logger, error_handler: ErrorHandler, 
                 schema_validator: SchemaValidator):
        pass
    
    def analyze_screenshot(self, screenshot: bytes) -> GameplayDecision:
        # Analyze screenshot and return decision
        # Uses error handler for retries, schema validator for response validation
        pass
    
    def get_status(self) -> str:
        # Return current status
        pass
```

**Key Design Decisions**:
- All API calls go through Error Handler for retry logic
- All responses validated by Schema Validator
- Timeouts configured via Config Manager
- All errors logged via Logger

### 3. Discord Bot

**Responsibility**: Handle Discord chat integration using Google Gemini.

**Interface**:
```python
class DiscordBot:
    def __init__(self, config: Config, logger: Logger, error_handler: ErrorHandler,
                 schema_validator: SchemaValidator, history_manager: HistoryManager):
        pass
    
    def send_message(self, channel_id: str, message: str) -> None:
        # Send message to Discord channel
        pass
    
    def process_message(self, message: str) -> str:
        # Process message with Gemini and return response
        pass
    
    def get_status(self) -> str:
        # Return current status
        pass
```

**Key Design Decisions**:
- Integrates with History Manager for context
- Uses Error Handler for API resilience
- Schema Validator ensures Gemini responses are valid
- All operations logged

### 4. Gamepad Controller

**Responsibility**: Send inputs to virtual gamepad with thread safety and macro support.

**Interface**:
```python
class GamepadController:
    def __init__(self, config: Config, logger: Logger, error_handler: ErrorHandler):
        pass
    
    def send_command(self, command: GamepadCommand) -> None:
        # Send command to gamepad (thread-safe, queued)
        pass
    
    def execute_macro(self, macro: Macro) -> MacroResult:
        # Execute macro atomically
        pass
    
    def release_all_keys(self) -> None:
        # Release all held keys (safe state)
        pass
    
    def get_status(self) -> str:
        # Return current status
        pass
```

**Key Design Decisions**:
- Thread-safe command queue with locks
- Atomic macro execution
- Automatic key release on interrupt
- All commands validated before execution

### 5. History Manager

**Responsibility**: Persist and retrieve conversation/gameplay history.

**Interface**:
```python
class HistoryManager:
    def __init__(self, config: Config, logger: Logger, error_handler: ErrorHandler):
        pass
    
    def add_entry(self, entry: HistoryEntry) -> None:
        # Add entry and persist immediately
        pass
    
    def get_history(self, filters: HistoryFilter) -> List[HistoryEntry]:
        # Query history by timestamp, source, or content
        pass
    
    def archive_old_entries(self) -> None:
        # Archive entries older than configured threshold
        pass
    
    def load_from_disk(self) -> None:
        # Load history from persistent storage
        pass
```

**Key Design Decisions**:
- Immediate persistence on every add_entry call
- Pluggable backends (JSON, SQLite)
- Automatic archival when size limit reached
- Crash recovery through persistent storage

### 6. Error Handler

**Responsibility**: Manage retries, timeouts, and error recovery.

**Interface**:
```python
class ErrorHandler:
    def __init__(self, config: Config, logger: Logger):
        pass
    
    def execute_with_retry(self, func: Callable, *args, **kwargs) -> Any:
        # Execute function with retry logic
        # Exponential backoff for transient errors
        pass
    
    def is_transient_error(self, error: Exception) -> bool:
        # Determine if error is transient (retry) or permanent (fail fast)
        pass
    
    def trigger_alert(self, error: Exception) -> None:
        # Send alert for critical errors
        pass
```

**Key Design Decisions**:
- Exponential backoff with configurable max retries
- Distinction between transient and permanent errors
- Full context logging on all errors
- Alert mechanism for critical failures

### 7. Config Manager

**Responsibility**: Load and validate environment variables securely.

**Interface**:
```python
class ConfigManager:
    def __init__(self, env_file: str = ".env"):
        # Load and validate all environment variables
        pass
    
    def get(self, key: str, default: Any = None) -> Any:
        # Get configuration value with type validation
        pass
    
    def validate(self) -> bool:
        # Validate all required variables are present and valid
        pass
```

**Key Design Decisions**:
- Load only at startup
- Never log or print secret values
- Type validation for all values
- Environment-specific configurations (dev/staging/prod)
- Clear error messages without exposing values

### 8. Logger

**Responsibility**: Structured logging to console and file.

**Interface**:
```python
class Logger:
    def __init__(self, config: Config):
        # Initialize logger with file rotation
        pass
    
    def log(self, level: str, component: str, message: str, context: dict = None) -> None:
        # Log structured message to console and file
        pass
    
    def debug(self, component: str, message: str, context: dict = None) -> None:
        pass
    
    def info(self, component: str, message: str, context: dict = None) -> None:
        pass
    
    def warning(self, component: str, message: str, context: dict = None) -> None:
        pass
    
    def error(self, component: str, message: str, context: dict = None) -> None:
        pass
    
    def critical(self, component: str, message: str, context: dict = None) -> None:
        pass
    
    def filter_logs(self, component: str = None, level: str = None, 
                   start_time: datetime = None, end_time: datetime = None) -> List[dict]:
        # Filter logs by component, level, or timestamp
        pass
```

**Key Design Decisions**:
- JSON structured format with timestamp, level, component, message
- Simultaneous console and file output
- Automatic file rotation on size limit
- Component name automatically included
- Filtering support for debugging

### 9. Schema Validator

**Responsibility**: Validate API responses against defined schemas.

**Interface**:
```python
class SchemaValidator:
    def __init__(self, logger: Logger):
        pass
    
    def validate_groq_response(self, response: dict) -> bool:
        # Validate Groq API response
        pass
    
    def validate_gemini_response(self, response: dict) -> bool:
        # Validate Google Gemini API response
        pass
    
    def validate(self, response: dict, schema: dict) -> bool:
        # Generic validation against schema
        pass
    
    def get_validation_errors(self) -> List[str]:
        # Get detailed error messages about validation failures
        pass
```

**Key Design Decisions**:
- Support for JSON Schema and Pydantic models
- Detailed error messages indicating missing/invalid fields
- Separate validators for each API
- Generic validation method for extensibility

### 10. Macro System

**Responsibility**: Define, validate, and execute gameplay macros.

**Interface**:
```python
class MacroSystem:
    def __init__(self, gamepad_controller: GamepadController, logger: Logger, 
                 error_handler: ErrorHandler):
        pass
    
    def register_macro(self, name: str, macro: Macro) -> None:
        # Register a macro
        pass
    
    def execute_macro(self, name: str, params: dict = None) -> MacroResult:
        # Execute a macro with optional parameters
        pass
    
    def validate_macro(self, macro: Macro) -> bool:
        # Validate macro before execution
        pass
    
    def get_execution_history(self, macro_name: str) -> List[MacroExecution]:
        # Get execution history for debugging
        pass
```

**Key Design Decisions**:
- Parameterized macros for flexibility
- Atomic execution through Gamepad Controller
- Validation before execution
- Execution history tracking for optimization

## Data Models

### GameplayDecision
```python
@dataclass
class GameplayDecision:
    action: str  # e.g., "move_left", "attack", "use_item"
    parameters: dict  # Action-specific parameters
    confidence: float  # 0.0 to 1.0
    reasoning: str  # Why this decision was made
    timestamp: datetime
```

### HistoryEntry
```python
@dataclass
class HistoryEntry:
    timestamp: datetime
    source: str  # "gameplay" or "discord"
    content: str
    metadata: dict  # Additional context
```

### GamepadCommand
```python
@dataclass
class GamepadCommand:
    button: str  # Button name
    action: str  # "press", "release", "hold"
    duration_ms: int = 0  # For hold actions
    timestamp: datetime = field(default_factory=datetime.now)
```

### Macro
```python
@dataclass
class Macro:
    name: str
    description: str
    commands: List[GamepadCommand]
    parameters: List[str]  # Parameterized macro variables
    timeout_ms: int  # Max execution time
```

### MacroResult
```python
@dataclass
class MacroResult:
    success: bool
    macro_name: str
    execution_time_ms: float
    error: Optional[str]
    commands_executed: int
```

### Config
```python
@dataclass
class Config:
    groq_api_key: str
    groq_timeout_ms: int
    groq_max_retries: int
    
    gemini_api_key: str
    gemini_timeout_ms: int
    gemini_max_retries: int
    
    discord_token: str
    
    history_backend: str  # "json" or "sqlite"
    history_max_size_mb: int
    history_archive_days: int
    
    log_level: str  # "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"
    log_file_max_size_mb: int
    log_file_backup_count: int
    
    rate_limit_requests_per_minute: int
    rate_limit_burst_size: int
    
    gamepad_queue_timeout_ms: int
    
    environment: str  # "dev", "staging", "production"
```

## Correctness Properties

A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.

### Property 1: Graceful Degradation on Optional Component Failure

*For any* Alice_System configuration where a component is marked optional, if that component fails to initialize, the system should continue to start with reduced capabilities rather than failing completely.

**Validates: Requirements 1.6**

### Property 2: History Persistence Round Trip

*For any* history entry added to the History_Manager, if the system is restarted, querying the history should return an equivalent entry without data loss.

**Validates: Requirements 2.2, 2.3**

### Property 3: History Archival Preserves Recent Entries

*For any* History_Manager with entries spanning multiple days, when archival is triggered at the size limit, all entries within the configured recent threshold should remain in active history while older entries are archived.

**Validates: Requirements 2.5**

### Property 4: History Query Correctness

*For any* set of history entries with different timestamps, sources, and content, querying by timestamp should return only entries within the specified range, querying by source should return only entries from that source, and querying by content should return only entries containing that content.

**Validates: Requirements 2.6**

### Property 5: Transient Error Retry with Exponential Backoff

*For any* API call that fails with a transient error, the Error_Handler should retry with exponential backoff (delay = base_delay * (backoff_factor ^ attempt_number)) until either success or max retries is reached.

**Validates: Requirements 3.1**

### Property 6: Permanent Error Fails Fast

*For any* API call that fails with a permanent error (e.g., 401 Unauthorized, 404 Not Found), the Error_Handler should fail immediately without retrying.

**Validates: Requirements 3.6**

### Property 7: Error Logging Includes Full Context

*For any* error encountered by a component, the logged error should include the component name, error type, error message, stack trace, and any available context (e.g., API endpoint, request parameters).

**Validates: Requirements 3.3**

### Property 8: Config Validation Rejects Missing Required Variables

*For any* Config_Manager initialization with missing required environment variables, validation should fail with a clear error message that does not expose the variable names or values.

**Validates: Requirements 4.2**

### Property 9: Config Never Logs Secrets

*For any* log message generated by the system, if the message contains a configuration value that is marked as secret (API keys, tokens), the log should not contain the actual value.

**Validates: Requirements 4.3**

### Property 10: Config Type Validation

*For any* configuration value with a specified type (integer, URL, boolean), if a value of a different type is provided, Config_Manager should reject it with a clear error message.

**Validates: Requirements 4.6**

### Property 11: Logger Output Contains All Required Fields

*For any* log message written by the Logger, the output should be valid JSON containing timestamp, level, component, and message fields.

**Validates: Requirements 5.1**

### Property 12: Logger Writes to Both Console and File

*For any* log message written by the Logger, the message should appear in both console output and the log file.

**Validates: Requirements 5.3**

### Property 13: Logger File Rotation on Size Limit

*For any* Logger with a configured file size limit, when the log file exceeds the limit, a new log file should be created and old files should be rotated according to the backup count configuration.

**Validates: Requirements 5.5**

### Property 14: Logger Filtering by Component

*For any* set of log messages from different components, filtering by component should return only messages from that component.

**Validates: Requirements 5.6**

### Property 15: API Call Timeout Cancellation

*For any* API call configured with a timeout, if the call takes longer than the timeout duration, the Error_Handler should cancel the request and trigger retry logic if applicable.

**Validates: Requirements 6.2**

### Property 16: Rate Limiting Respects Quota

*For any* sequence of API calls with a configured rate limit, the number of successful calls should not exceed the quota within the time window.

**Validates: Requirements 6.3**

### Property 17: Rate Limiting Proactive Slowdown

*For any* API with a configured rate limit, as the quota consumption approaches the limit, the request rate should decrease to avoid hitting the limit.

**Validates: Requirements 6.4**

### Property 18: Rate Limiting Queue Ordering

*For any* sequence of requests sent to a rate-limited API, the requests should be processed in the order they were queued.

**Validates: Requirements 6.6**

### Property 19: Schema Validation Rejects Invalid Responses

*For any* API response that does not match the expected schema, the Schema_Validator should reject it and provide detailed error messages indicating which fields are missing or invalid.

**Validates: Requirements 7.3, 7.6**

### Property 20: Schema Validation Accepts Valid Responses

*For any* API response that matches the expected schema, the Schema_Validator should accept it without errors.

**Validates: Requirements 7.1, 7.2**

### Property 21: Gamepad Command Queue Ordering

*For any* sequence of gamepad commands sent from multiple threads, the Gamepad_Controller should execute them in the order they were queued.

**Validates: Requirements 8.2**

### Property 22: Gamepad Command Validation

*For any* gamepad command with invalid parameters (e.g., unknown button, invalid action), the Gamepad_Controller should reject it and log an error.

**Validates: Requirements 8.3, 8.4**

### Property 23: Macro Atomic Execution

*For any* macro execution, either all commands in the macro should execute successfully or none should execute (all-or-nothing semantics).

**Validates: Requirements 8.5**

### Property 24: Macro Interrupt Key Release

*For any* macro that is interrupted during execution, all held keys should be released and the gamepad should return to a safe state.

**Validates: Requirements 8.6**

### Property 25: Macro Validation Before Execution

*For any* macro with invalid commands, the Macro_System should reject it before execution and provide detailed error messages.

**Validates: Requirements 9.2**

### Property 26: Parameterized Macro Substitution

*For any* parameterized macro with parameters provided, the Macro_System should substitute the parameters into the macro commands before execution.

**Validates: Requirements 9.3**

### Property 27: Macro Execution History Tracking

*For any* macro execution, the Macro_System should record the execution in history including success/failure, execution time, and any errors.

**Validates: Requirements 9.6**

## Error Handling

### Error Classification

**Transient Errors** (retry with backoff):
- Network timeouts
- HTTP 429 (Rate Limited)
- HTTP 503 (Service Unavailable)
- HTTP 504 (Gateway Timeout)
- Temporary connection failures

**Permanent Errors** (fail fast):
- HTTP 401 (Unauthorized)
- HTTP 403 (Forbidden)
- HTTP 404 (Not Found)
- Invalid API key
- Malformed request

**Critical Errors** (alert + log):
- System initialization failure
- Persistent storage corruption
- Gamepad driver failure
- Discord connection loss

### Retry Strategy

```
Attempt 1: Immediate
Attempt 2: Wait 1s (base_delay * 2^0)
Attempt 3: Wait 2s (base_delay * 2^1)
Attempt 4: Wait 4s (base_delay * 2^2)
Attempt 5: Wait 8s (base_delay * 2^3)
Max retries: 5 (configurable)
```

### Error Recovery

1. Log error with full context
2. Classify error (transient/permanent/critical)
3. If transient: retry with backoff
4. If permanent: return graceful error response
5. If critical: trigger alert and attempt graceful shutdown

## Testing Strategy

### Unit Testing

- Test each component in isolation with mocked dependencies
- Test error handling and edge cases
- Test configuration validation
- Test schema validation with valid and invalid inputs
- Minimum 80% code coverage per component

### Property-Based Testing

- **Macro Execution Properties**: Test macros with randomly generated parameters and verify correctness
- **History Persistence**: Test history round-trip (add → persist → load → verify)
- **Rate Limiting**: Test rate limiting with random request patterns
- **Error Retry Logic**: Test retry behavior with simulated transient failures
- **Gamepad Queue Ordering**: Test command ordering with concurrent submissions
- Minimum 100 iterations per property test

### Integration Testing

- Test component interactions (Vision Engine → History Manager → Logger)
- Test end-to-end flows (screenshot → decision → gamepad command)
- Test error propagation across components
- Test graceful degradation when components fail

### Test Configuration

- All tests run with mocked external APIs (Groq, Gemini, Discord)
- Tests use in-memory history storage (no disk I/O)
- Tests use temporary log files
- Tests run in isolation without side effects

