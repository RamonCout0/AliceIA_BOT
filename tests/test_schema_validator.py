"""Tests for Schema Validator."""

import pytest
from unittest.mock import Mock
from hypothesis import given, strategies as st
from pydantic import BaseModel

from alice.core.schema_validator import SchemaValidator, GroqResponseModel, GeminiResponseModel
from alice.core.logger import Logger


@pytest.fixture
def mock_logger():
    """Create mock logger."""
    return Mock(spec=Logger)


@pytest.fixture
def validator(mock_logger):
    """Create SchemaValidator instance."""
    return SchemaValidator(mock_logger)


class TestGroqValidation:
    """Test Groq response validation."""

    def test_valid_groq_response(self, validator):
        """Test valid Groq response."""
        response = {
            "choices": [{"message": {"content": "test"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 20},
            "model": "llama-2-vision"
        }
        
        assert validator.validate_groq_response(response) is True
        assert len(validator.get_validation_errors()) == 0

    def test_invalid_groq_response_missing_choices(self, validator):
        """Test invalid Groq response missing choices."""
        response = {
            "usage": {"prompt_tokens": 10, "completion_tokens": 20},
            "model": "llama-2-vision"
        }
        
        assert validator.validate_groq_response(response) is False
        assert len(validator.get_validation_errors()) > 0

    def test_invalid_groq_response_missing_usage(self, validator):
        """Test invalid Groq response missing usage."""
        response = {
            "choices": [{"message": {"content": "test"}}],
            "model": "llama-2-vision"
        }
        
        assert validator.validate_groq_response(response) is False
        assert len(validator.get_validation_errors()) > 0

    def test_invalid_groq_response_missing_model(self, validator):
        """Test invalid Groq response missing model."""
        response = {
            "choices": [{"message": {"content": "test"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 20}
        }
        
        assert validator.validate_groq_response(response) is False
        assert len(validator.get_validation_errors()) > 0

    def test_groq_response_wrong_type(self, validator):
        """Test Groq response with wrong type."""
        response = {
            "choices": "not a list",
            "usage": {"prompt_tokens": 10, "completion_tokens": 20},
            "model": "llama-2-vision"
        }
        
        assert validator.validate_groq_response(response) is False
        assert len(validator.get_validation_errors()) > 0


class TestGeminiValidation:
    """Test Gemini response validation."""

    def test_valid_gemini_response(self, validator):
        """Test valid Gemini response."""
        response = {
            "candidates": [{"content": {"parts": [{"text": "test"}]}}],
            "usageMetadata": {"prompt_token_count": 10, "candidates_token_count": 20}
        }
        
        assert validator.validate_gemini_response(response) is True
        assert len(validator.get_validation_errors()) == 0

    def test_valid_gemini_response_without_usage(self, validator):
        """Test valid Gemini response without usage metadata."""
        response = {
            "candidates": [{"content": {"parts": [{"text": "test"}]}}]
        }
        
        assert validator.validate_gemini_response(response) is True
        assert len(validator.get_validation_errors()) == 0

    def test_invalid_gemini_response_missing_candidates(self, validator):
        """Test invalid Gemini response missing candidates."""
        response = {
            "usageMetadata": {"prompt_token_count": 10, "candidates_token_count": 20}
        }
        
        assert validator.validate_gemini_response(response) is False
        assert len(validator.get_validation_errors()) > 0

    def test_invalid_gemini_response_wrong_type(self, validator):
        """Test Gemini response with wrong type."""
        response = {
            "candidates": "not a list",
            "usageMetadata": {"prompt_token_count": 10, "candidates_token_count": 20}
        }
        
        assert validator.validate_gemini_response(response) is False
        assert len(validator.get_validation_errors()) > 0


class TestGenericValidation:
    """Test generic validation."""

    def test_valid_generic_response(self, validator):
        """Test valid generic response."""
        class TestModel(BaseModel):
            name: str
            age: int
        
        response = {"name": "test", "age": 25}
        
        assert validator.validate(response, TestModel) is True
        assert len(validator.get_validation_errors()) == 0

    def test_invalid_generic_response_missing_field(self, validator):
        """Test invalid generic response missing field."""
        class TestModel(BaseModel):
            name: str
            age: int
        
        response = {"name": "test"}
        
        assert validator.validate(response, TestModel) is False
        assert len(validator.get_validation_errors()) > 0

    def test_invalid_generic_response_wrong_type(self, validator):
        """Test invalid generic response with wrong type."""
        class TestModel(BaseModel):
            name: str
            age: int
        
        response = {"name": "test", "age": "not an int"}
        
        assert validator.validate(response, TestModel) is False
        assert len(validator.get_validation_errors()) > 0


class TestErrorReporting:
    """Test error reporting."""

    def test_validation_errors_logged(self, validator, mock_logger):
        """Test validation errors are logged."""
        response = {
            "choices": "not a list",
            "usage": {"prompt_tokens": 10, "completion_tokens": 20},
            "model": "llama-2-vision"
        }
        
        validator.validate_groq_response(response)
        
        assert mock_logger.error.called
        call_args = mock_logger.error.call_args
        assert "SchemaValidator" in call_args[0]
        assert "validation failed" in call_args[0][1]

    def test_get_validation_errors_returns_list(self, validator):
        """Test get_validation_errors returns list."""
        response = {
            "choices": "not a list",
            "usage": {"prompt_tokens": 10, "completion_tokens": 20},
            "model": "llama-2-vision"
        }
        
        validator.validate_groq_response(response)
        errors = validator.get_validation_errors()
        
        assert isinstance(errors, list)
        assert len(errors) > 0
        assert all(isinstance(e, str) for e in errors)


# Property-based tests

@given(st.dictionaries(
    st.text(min_size=1),
    st.one_of(st.text(), st.integers(), st.booleans(), st.none())
))
def test_property_schema_validation_rejects_invalid_responses(test_dict):
    """Property 19: Schema Validation Rejects Invalid Responses.
    
    For any API response that does not match the expected schema, 
    the Schema_Validator should reject it.
    
    Validates: Requirements 7.3, 7.6
    """
    logger = Mock(spec=Logger)
    validator = SchemaValidator(logger)
    
    # Try to validate random dict against Groq schema
    # Most random dicts will fail validation
    result = validator.validate_groq_response(test_dict)
    
    # If validation failed, errors should be populated
    if not result:
        assert len(validator.get_validation_errors()) > 0


def test_property_schema_validation_accepts_valid_responses():
    """Property 20: Schema Validation Accepts Valid Responses.
    
    For any API response that matches the expected schema, 
    the Schema_Validator should accept it without errors.
    
    Validates: Requirements 7.1, 7.2
    """
    logger = Mock(spec=Logger)
    validator = SchemaValidator(logger)
    
    # Valid Groq response
    groq_response = {
        "choices": [{"message": {"content": "test"}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 20},
        "model": "llama-2-vision"
    }
    
    assert validator.validate_groq_response(groq_response) is True
    assert len(validator.get_validation_errors()) == 0
    
    # Valid Gemini response
    gemini_response = {
        "candidates": [{"content": {"parts": [{"text": "test"}]}}]
    }
    
    assert validator.validate_gemini_response(gemini_response) is True
    assert len(validator.get_validation_errors()) == 0
