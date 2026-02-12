# Implementation Plan: Alice AI Refactor

## Overview

This implementation plan refactors Alice from a fragmented architecture into a unified, robust system. The approach follows a bottom-up strategy: first establish core infrastructure (logging, config, error handling), then implement components (Vision Engine, Discord Bot, Gamepad Controller), then add persistence and validation layers, and finally integrate everything through the orchestrator.

Each task builds on previous tasks with no orphaned code. All components are tested incrementally with property-based tests for critical functionality.

## Tasks

- [x] 1. Set up project structure and core infrastructure
  - Create directory structure: `alice/`, `alice/core/`, `alice/components/`, `alice/utils/`, `tests/`
  - Create `__init__.py` files for all packages
  - Set up `requirements.txt` with dependencies (groq, discord.py, pydantic, pytest, hypothesis, etc.)
  - Create `setup.py` for package installation
  - _Requirements: 1.1, 1.3_

- [x] 2. Implement Config Manager with secure environment variable handling
  - [x] 2.1 Create Config dataclass with all configuration fields
    - Define Config dataclass with Groq, Gemini, Discord, history, logging, rate limiting settings
    - Add type hints for all fields
    - _Requirements: 4.1, 4.2, 4.6_
  
  - [x] 2.2 Implement ConfigManager class with validation
    - Load .env file at startup using python-dotenv
    - Validate all required variables are present
    - Validate types (int, str, URL, bool)
    - Never log or print secret values
    - Raise clear errors without exposing values
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.6_
  
  - [-]* 2.3 Write property tests for ConfigManager
    - **Property 8: Config Validation Rejects Missing Required Variables**
    - **Property 9: Config Never Logs Secrets**
    - **Property 10: Config Type Validation**
    - **Validates: Requirements 4.2, 4.3, 4.6**

- [x] 3. Implement Logger with structured JSON output
  - [x] 3.1 Create Logger class with JSON formatting
    - Implement log method with timestamp, level, component, message, context
    - Support DEBUG, INFO, WARNING, ERROR, CRITICAL levels
    - Output to both console and file simultaneously
    - _Requirements: 5.1, 5.2, 5.3, 5.4_
  
  - [x] 3.2 Implement file rotation and filtering
    - Rotate log files when exceeding size limit
    - Keep configurable number of backup files
    - Implement filter_logs method by component, level, timestamp
    - _Requirements: 5.5, 5.6_
  
  - [x]* 3.3 Write property tests for Logger
    - **Property 11: Logger Output Contains All Required Fields**
    - **Property 12: Logger Writes to Both Console and File**
    - **Property 13: Logger File Rotation on Size Limit**
    - **Property 14: Logger Filtering by Component**
    - **Validates: Requirements 5.1, 5.3, 5.5, 5.6**

- [x] 4. Implement Error Handler with retry logic and timeout management
  - [x] 4.1 Create ErrorHandler class with retry logic
    - Implement execute_with_retry method with exponential backoff
    - Support configurable max retries and backoff factor
    - Distinguish transient errors (retry) from permanent errors (fail fast)
    - _Requirements: 3.1, 3.6_
  
  - [x] 4.2 Implement error classification and logging
    - Classify errors as transient, permanent, or critical
    - Log all errors with full context (component, error type, stack trace)
    - Implement trigger_alert method for critical errors
    - _Requirements: 3.2, 3.3, 3.5_
  
  - [x] 4.3 Implement timeout management
    - Add timeout parameter to execute_with_retry
    - Cancel requests that exceed timeout
    - Trigger retry logic on timeout
    - _Requirements: 6.2_
  
  - [x]* 4.4 Write property tests for ErrorHandler
    - **Property 5: Transient Error Retry with Exponential Backoff**
    - **Property 6: Permanent Error Fails Fast**
    - **Property 7: Error Logging Includes Full Context**
    - **Property 15: API Call Timeout Cancellation**
    - **Validates: Requirements 3.1, 3.3, 3.6, 6.2**

- [x] 5. Implement Schema Validator for API response validation
  - [x] 5.1 Create SchemaValidator class with Pydantic support
    - Define Pydantic models for Groq and Gemini responses
    - Implement validate_groq_response and validate_gemini_response methods
    - Implement generic validate method for any schema
    - _Requirements: 7.1, 7.2_
  
  - [x] 5.2 Implement detailed error reporting
    - Implement get_validation_errors method
    - Provide clear error messages indicating missing/invalid fields
    - _Requirements: 7.3, 7.6_
  
  - [x]* 5.3 Write property tests for SchemaValidator
    - **Property 19: Schema Validation Rejects Invalid Responses**
    - **Property 20: Schema Validation Accepts Valid Responses**
    - **Validates: Requirements 7.1, 7.2, 7.3, 7.6**

- [x] 6. Implement History Manager with persistence
  - [x] 6.1 Create HistoryEntry and HistoryFilter dataclasses
    - Define HistoryEntry with timestamp, source, content, metadata
    - Define HistoryFilter for querying by timestamp, source, content
    - _Requirements: 2.1, 2.6_
  
  - [x] 6.2 Implement HistoryManager with JSON backend
    - Implement add_entry method with immediate persistence to disk
    - Implement load_from_disk method for crash recovery
    - Implement get_history method with filtering by timestamp, source, content
    - _Requirements: 2.1, 2.2, 2.3, 2.6_
  
  - [x] 6.3 Implement history archival
    - Implement archive_old_entries method
    - Archive entries older than configured threshold
    - Keep recent entries in active history
    - _Requirements: 2.5_
  
  - [x]* 6.4 Write property tests for HistoryManager
    - **Property 2: History Persistence Round Trip**
    - **Property 3: History Archival Preserves Recent Entries**
    - **Property 4: History Query Correctness**
    - **Validates: Requirements 2.2, 2.3, 2.5, 2.6**

- [x] 7. Implement Rate Limiter for API quota management
  - [x] 7.1 Create RateLimiter class with token bucket algorithm
    - Implement rate limiting with configurable requests per minute
    - Implement burst size support
    - Queue requests when rate limit is approached
    - _Requirements: 6.3, 6.4, 6.6_
  
  - [x] 7.2 Implement quota tracking and logging
    - Track remaining quota and log status
    - Proactively slow down requests as quota is consumed
    - _Requirements: 6.5_
  
  - [x]* 7.3 Write property tests for RateLimiter
    - **Property 16: Rate Limiting Respects Quota**
    - **Property 17: Rate Limiting Proactive Slowdown**
    - **Property 18: Rate Limiting Queue Ordering**
    - **Validates: Requirements 6.3, 6.4, 6.6**

- [x] 8. Implement Gamepad Controller with thread safety
  - [x] 8.1 Create GamepadCommand and Macro dataclasses
    - Define GamepadCommand with button, action, duration, timestamp
    - Define Macro with name, description, commands, parameters, timeout
    - _Requirements: 8.1, 9.1_
  
  - [x] 8.2 Implement GamepadController with thread-safe queue
    - Use threading.Lock for thread safety
    - Implement command queue with FIFO ordering
    - Implement send_command method (queued, validated)
    - Implement release_all_keys method for safe state
    - _Requirements: 8.1, 8.2, 8.3, 8.4_
  
  - [x] 8.3 Implement macro execution with atomicity
    - Implement execute_macro method with atomic execution
    - Validate all commands before execution
    - Release all keys on interrupt
    - _Requirements: 8.5, 8.6_
  
  - [x]* 8.4 Write property tests for GamepadController
    - **Property 21: Gamepad Command Queue Ordering**
    - **Property 22: Gamepad Command Validation**
    - **Property 23: Macro Atomic Execution**
    - **Property 24: Macro Interrupt Key Release**
    - **Validates: Requirements 8.2, 8.3, 8.4, 8.5, 8.6**

- [x] 9. Implement Macro System with validation and history
  - [x] 9.1 Create MacroResult and MacroExecution dataclasses
    - Define MacroResult with success, macro_name, execution_time, error, commands_executed
    - Define MacroExecution for history tracking
    - _Requirements: 9.4, 9.6_
  
  - [x] 9.2 Implement MacroSystem class
    - Implement register_macro method
    - Implement validate_macro method (validate all commands)
    - Implement execute_macro method with parameter substitution
    - _Requirements: 9.2, 9.3_
  
  - [x] 9.3 Implement macro execution history tracking
    - Implement get_execution_history method
    - Track success/failure, execution time, errors
    - _Requirements: 9.4, 9.6_
  
  - [x]* 9.4 Write property tests for MacroSystem
    - **Property 25: Macro Validation Before Execution**
    - **Property 26: Parameterized Macro Substitution**
    - **Property 27: Macro Execution History Tracking**
    - **Validates: Requirements 9.2, 9.3, 9.4, 9.6**

- [x] 10. Implement Vision Engine with Groq integration
  - [x] 10.1 Create GameplayDecision dataclass
    - Define GameplayDecision with action, parameters, confidence, reasoning, timestamp
    - _Requirements: 1.3_
  
  - [x] 10.2 Implement VisionEngine class
    - Initialize with Config, Logger, ErrorHandler, SchemaValidator
    - Implement analyze_screenshot method
    - Use ErrorHandler for retries and timeouts
    - Use SchemaValidator for response validation
    - _Requirements: 1.3, 3.1, 7.1_
  
  - [x] 10.3 Implement Groq API integration
    - Call Groq API with screenshot
    - Parse response into GameplayDecision
    - Handle errors and retries through ErrorHandler
    - _Requirements: 1.3, 3.1, 7.1_
  
  - [x] 10.4 Implement status reporting
    - Implement get_status method
    - Return current status (idle, analyzing, error)
    - _Requirements: 1.3_

- [x] 11. Implement Discord Bot with Gemini integration
  - [x] 11.1 Implement DiscordBot class
    - Initialize with Config, Logger, ErrorHandler, SchemaValidator, HistoryManager
    - Implement send_message method
    - Implement process_message method with Gemini
    - _Requirements: 1.3, 3.1, 7.2_
  
  - [x] 11.2 Implement Gemini API integration
    - Call Gemini API with message and history context
    - Parse response into message
    - Handle errors and retries through ErrorHandler
    - _Requirements: 1.3, 3.1, 7.2_
  
  - [x] 11.3 Implement Discord event handlers
    - Handle on_message event
    - Add messages to history
    - Send responses back to Discord
    - _Requirements: 1.3, 2.2_
  
  - [x] 11.4 Implement status reporting
    - Implement get_status method
    - Return current status (connected, disconnected, error)
    - _Requirements: 1.3_

- [x] 12. Implement Core Orchestrator (main.py)
  - [x] 12.1 Create AliceSystem class
    - Initialize all components with dependency injection
    - Implement start method with correct initialization order
    - Implement stop method for graceful shutdown
    - _Requirements: 1.1, 1.2, 1.4_
  
  - [x] 12.2 Implement component lifecycle management
    - Load Config first
    - Initialize Logger
    - Initialize History Manager
    - Initialize Error Handler
    - Initialize Vision Engine, Discord Bot, Gamepad Controller
    - Handle initialization failures gracefully
    - _Requirements: 1.2, 1.6_
  
  - [x] 12.3 Implement graceful degradation
    - If optional component fails, continue with reduced capabilities
    - Log failures but don't crash
    - _Requirements: 1.6_
  
  - [x] 12.4 Create main entry point
    - Create main.py with AliceSystem initialization
    - Handle command-line arguments
    - Implement signal handlers for graceful shutdown
    - _Requirements: 1.1_

- [x] 13. Checkpoint - Ensure all core components are working
  - Ensure all unit tests pass
  - Ensure all property tests pass (100+ iterations each)
  - Verify no circular dependencies
  - Check code coverage is at least 80%
  - Ask the user if questions arise

- [x] 14. Implement integration tests
  - [x] 14.1 Create integration test suite
    - Test Vision Engine → History Manager → Logger flow
    - Test Discord Bot → History Manager → Logger flow
    - Test Gamepad Controller → Macro System flow
    - Test error propagation across components
    - _Requirements: 1.2, 1.4_
  
  - [x] 14.2 Create end-to-end test scenarios
    - Test screenshot → decision → gamepad command flow
    - Test Discord message → Gemini response → Discord send flow
    - Test macro execution with multiple commands
    - _Requirements: 1.2, 1.4_
  
  - [x] 14.3 Create error recovery tests
    - Test system recovery from transient API failures
    - Test history recovery after crash simulation
    - Test graceful degradation when components fail
    - _Requirements: 3.1, 3.2, 2.3, 1.6_

- [x] 15. Implement additional game support infrastructure
  - [x] 15.1 Create game abstraction layer
    - Define GameInterface for different games
    - Implement game-specific screenshot capture
    - Implement game-specific command mapping
    - _Requirements: 1.3_
  
  - [x] 15.2 Implement game registry
    - Register available games (Terraria, Minecraft, Chess, etc.)
    - Switch between games at runtime
    - _Requirements: 1.3_

- [x] 16. Final checkpoint - Ensure all tests pass
  - Ensure all unit tests pass
  - Ensure all property tests pass (100+ iterations each)
  - Ensure all integration tests pass
  - Verify code coverage is at least 80%
  - Verify no circular dependencies
  - Ask the user if questions arise

- [x] 17. Documentation and deployment preparation
  - [x] 17.1 Create API documentation
    - Document all public interfaces
    - Document configuration options
    - Document error codes and recovery strategies
    - _Requirements: 1.3_
  
  - [x] 17.2 Create deployment guide
    - Document installation steps
    - Document configuration setup
    - Document troubleshooting guide
    - _Requirements: 1.1_
  
  - [x] 17.3 Create developer guide
    - Document architecture overview
    - Document how to add new games
    - Document how to extend components
    - _Requirements: 1.1, 1.3_

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties (100+ iterations)
- Unit tests validate specific examples and edge cases
- All external APIs are mocked in tests (no real API calls)
- Implementation uses Python 3.9+ with type hints
- All code follows PEP 8 style guide
- All components use dependency injection for testability

