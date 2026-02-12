# Requirements Document: Alice AI Refactor

## Introduction

Alice is an AI-powered Terraria gameplay bot that combines computer vision (Groq/Llama Vision) for gameplay analysis with Discord integration (Google Gemini) for chat. The current implementation suffers from architectural inconsistencies, fragile state management, weak error handling, and security vulnerabilities. This refactor addresses all critical issues to create a robust, maintainable, and secure system.

## Glossary

- **Alice_System**: The complete AI gameplay and Discord bot system
- **Vision_Engine**: Component responsible for screenshot analysis and gameplay decisions (Groq/Llama Vision)
- **Discord_Bot**: Component handling Discord chat integration (Google Gemini)
- **Gamepad_Controller**: Virtual gamepad interface for sending inputs to Terraria
- **History_Manager**: Component managing conversation and gameplay history with persistence
- **Error_Handler**: Component managing retry logic, timeouts, and error recovery
- **Config_Manager**: Component managing environment variables and configuration with validation
- **Logger**: Structured logging system for debugging and monitoring
- **Schema_Validator**: Component validating API responses against defined schemas
- **Macro_System**: Predefined gameplay sequences (e.g., mining, combat) with validation

## Requirements

### Requirement 1: Unified Architecture

**User Story:** As a developer, I want a clear, unified architecture with well-defined module boundaries, so that I can understand, maintain, and extend the system without confusion.

#### Acceptance Criteria

1. THE Alice_System SHALL have a single entry point (main.py) that orchestrates all components
2. WHEN the system starts, THE Alice_System SHALL initialize Vision_Engine, Discord_Bot, Gamepad_Controller, and History_Manager in the correct order
3. THE Alice_System SHALL define clear interfaces for each component (Vision_Engine, Discord_Bot, Gamepad_Controller, History_Manager, Error_Handler, Config_Manager, Logger, Schema_Validator)
4. WHEN a component needs to communicate with another, THE Alice_System SHALL use dependency injection through constructor parameters
5. THE Alice_System SHALL have no circular dependencies between modules
6. WHERE a component is optional (e.g., Discord_Bot can be disabled), THE Alice_System SHALL support graceful degradation

### Requirement 2: Robust History Management with Persistence

**User Story:** As a system operator, I want conversation and gameplay history to persist across restarts, so that the system can recover from crashes and maintain continuity.

#### Acceptance Criteria

1. WHEN the system starts, THE History_Manager SHALL load previous conversation history from persistent storage
2. WHEN a new message is added to history, THE History_Manager SHALL immediately persist it to disk
3. WHEN the system crashes and restarts, THE History_Manager SHALL recover all persisted history without data loss
4. THE History_Manager SHALL support multiple history formats (JSON, SQLite) with a pluggable backend
5. WHEN history reaches a configurable size limit, THE History_Manager SHALL archive old entries while keeping recent ones
6. THE History_Manager SHALL provide query methods to retrieve history by timestamp, source (gameplay/discord), or content

### Requirement 3: Comprehensive Error Handling with Retry Logic

**User Story:** As a system operator, I want the system to automatically recover from transient failures, so that temporary network issues or API rate limits don't cause the system to crash.

#### Acceptance Criteria

1. WHEN an API call fails with a transient error (timeout, rate limit, temporary network issue), THE Error_Handler SHALL automatically retry with exponential backoff
2. WHEN an API call fails after maximum retries, THE Error_Handler SHALL log the failure and return a graceful error response
3. WHEN a component encounters an error, THE Error_Handler SHALL not propagate the error silently but SHALL log it with full context
4. THE Error_Handler SHALL support configurable retry policies (max retries, backoff strategy, timeout duration)
5. WHEN a critical error occurs, THE Error_Handler SHALL trigger an alert mechanism (e.g., Discord notification, log file)
6. THE Error_Handler SHALL distinguish between transient errors (retry) and permanent errors (fail fast)

### Requirement 4: Secure Configuration Management

**User Story:** As a security officer, I want environment variables and secrets to be properly validated and protected, so that credentials are not exposed and configuration is correct.

#### Acceptance Criteria

1. THE Config_Manager SHALL load environment variables from .env file only at startup
2. THE Config_Manager SHALL validate all required environment variables are present before system initialization
3. THE Config_Manager SHALL never log or print environment variable values (secrets)
4. WHEN an environment variable is missing or invalid, THE Config_Manager SHALL raise an error with a clear message (without exposing the value)
5. THE Config_Manager SHALL support environment-specific configurations (dev, staging, production)
6. THE Config_Manager SHALL use type validation for all configuration values (e.g., integers, URLs, boolean flags)

### Requirement 5: Structured Logging System

**User Story:** As a developer, I want structured, centralized logging with multiple output targets, so that I can debug issues and monitor system behavior.

#### Acceptance Criteria

1. THE Logger SHALL output logs in structured format (JSON) with timestamp, level, component, and message
2. THE Logger SHALL support multiple log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
3. THE Logger SHALL write logs to both console and file simultaneously
4. WHEN a component logs a message, THE Logger SHALL automatically include the component name and context
5. THE Logger SHALL rotate log files when they exceed a configurable size limit
6. THE Logger SHALL provide a way to filter logs by component, level, or timestamp for debugging

### Requirement 6: Timeout and Rate Limiting Configuration

**User Story:** As a system operator, I want configurable timeouts and rate limiting, so that the system doesn't hang or get blocked by API rate limits.

#### Acceptance Criteria

1. THE Alice_System SHALL have configurable timeout values for each API call (Vision_Engine, Discord_Bot)
2. WHEN an API call exceeds the timeout, THE Error_Handler SHALL cancel the request and retry if applicable
3. THE Alice_System SHALL implement rate limiting to respect API quotas (Groq, Google Gemini)
4. WHEN rate limit is approached, THE Alice_System SHALL proactively slow down requests to avoid hitting the limit
5. THE Alice_System SHALL log rate limit status and remaining quota for monitoring
6. WHERE rate limiting is enforced, THE Alice_System SHALL queue requests and process them in order

### Requirement 7: Response Validation with Schema

**User Story:** As a developer, I want API responses to be validated against defined schemas, so that invalid or malformed responses are caught early.

#### Acceptance Criteria

1. WHEN the Vision_Engine receives a response from Groq API, THE Schema_Validator SHALL validate it against the expected schema
2. WHEN the Discord_Bot receives a response from Google Gemini API, THE Schema_Validator SHALL validate it against the expected schema
3. IF a response does not match the schema, THEN THE Schema_Validator SHALL raise a validation error with details about the mismatch
4. THE Schema_Validator SHALL support multiple schema formats (JSON Schema, Pydantic models)
5. WHEN a response is invalid, THE Error_Handler SHALL log the invalid response and retry if applicable
6. THE Schema_Validator SHALL provide clear error messages indicating which fields are missing or invalid

### Requirement 8: Gamepad Control with Thread Safety

**User Story:** As a developer, I want the gamepad controller to be thread-safe and well-tested, so that concurrent gameplay commands don't cause race conditions or crashes.

#### Acceptance Criteria

1. THE Gamepad_Controller SHALL use thread-safe mechanisms (locks, queues) to handle concurrent input commands
2. WHEN multiple threads attempt to send gamepad commands simultaneously, THE Gamepad_Controller SHALL queue them and process sequentially
3. THE Gamepad_Controller SHALL validate all input commands before sending to the virtual gamepad
4. WHEN an invalid command is received, THE Gamepad_Controller SHALL log the error and skip the command
5. THE Gamepad_Controller SHALL support macro sequences (predefined gameplay patterns) with atomic execution
6. WHEN a macro is interrupted, THE Gamepad_Controller SHALL release all held keys and return to a safe state

### Requirement 9: Macro System with Validation

**User Story:** As a gameplay developer, I want predefined macro sequences to be validated and tested, so that gameplay automation is reliable and predictable.

#### Acceptance Criteria

1. THE Macro_System SHALL define macros as sequences of gamepad commands with timing information
2. WHEN a macro is executed, THE Macro_System SHALL validate all commands before execution
3. THE Macro_System SHALL support parameterized macros (e.g., mine_area with coordinates)
4. WHEN a macro fails during execution, THE Macro_System SHALL log the failure and attempt recovery
5. THE Macro_System SHALL provide a way to test macros without affecting actual gameplay
6. THE Macro_System SHALL track macro execution history for debugging and optimization

### Requirement 10: Modular Testing Strategy

**User Story:** As a QA engineer, I want comprehensive testing including property-based tests for macros, so that system correctness is verified across many scenarios.

#### Acceptance Criteria

1. THE Alice_System SHALL have unit tests for all components with at least 80% code coverage
2. THE Alice_System SHALL have property-based tests for macro execution to verify correctness across many input combinations
3. WHEN a property test fails, THE Alice_System SHALL provide a minimal failing example for debugging
4. THE Alice_System SHALL have integration tests that verify component interactions
5. THE Alice_System SHALL have tests for error handling and recovery scenarios
6. THE Alice_System SHALL support running tests in isolation without external API dependencies (mocked)

