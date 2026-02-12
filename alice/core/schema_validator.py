"""Schema Validator for API response validation."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ValidationError

from alice.core.logger import Logger


class GroqResponseModel(BaseModel):
    """Pydantic model for Groq API response."""
    
    choices: List[Dict[str, Any]]
    usage: Dict[str, int]
    model: str


class GeminiResponseModel(BaseModel):
    """Pydantic model for Google Gemini API response."""
    
    candidates: List[Dict[str, Any]]
    usageMetadata: Optional[Dict[str, int]] = None


class SchemaValidator:
    """Validates API responses against defined schemas."""

    def __init__(self, logger: Logger):
        """Initialize SchemaValidator.
        
        Args:
            logger: Logger instance
        """
        self.logger = logger
        self.validation_errors: List[str] = []

    def validate_groq_response(self, response: Dict[str, Any]) -> bool:
        """Validate Groq API response.
        
        Args:
            response: Response from Groq API
            
        Returns:
            True if valid, False otherwise
        """
        self.validation_errors = []
        
        try:
            GroqResponseModel(**response)
            return True
        except ValidationError as error:
            self.validation_errors = [str(e) for e in error.errors()]
            self.logger.error(
                "SchemaValidator",
                "Groq response validation failed",
                {
                    "error_count": len(self.validation_errors),
                    "errors": self.validation_errors[:3],  # Log first 3 errors
                }
            )
            return False

    def validate_gemini_response(self, response: Dict[str, Any]) -> bool:
        """Validate Google Gemini API response.
        
        Args:
            response: Response from Gemini API
            
        Returns:
            True if valid, False otherwise
        """
        self.validation_errors = []
        
        try:
            GeminiResponseModel(**response)
            return True
        except ValidationError as error:
            self.validation_errors = [str(e) for e in error.errors()]
            self.logger.error(
                "SchemaValidator",
                "Gemini response validation failed",
                {
                    "error_count": len(self.validation_errors),
                    "errors": self.validation_errors[:3],  # Log first 3 errors
                }
            )
            return False

    def validate(self, response: Dict[str, Any], schema: BaseModel) -> bool:
        """Generic validation against schema.
        
        Args:
            response: Response to validate
            schema: Pydantic model to validate against
            
        Returns:
            True if valid, False otherwise
        """
        self.validation_errors = []
        
        try:
            schema(**response)
            return True
        except ValidationError as error:
            self.validation_errors = [str(e) for e in error.errors()]
            self.logger.error(
                "SchemaValidator",
                "Response validation failed",
                {
                    "schema": schema.__name__,
                    "error_count": len(self.validation_errors),
                    "errors": self.validation_errors[:3],
                }
            )
            return False

    def get_validation_errors(self) -> List[str]:
        """Get detailed error messages about validation failures.
        
        Returns:
            List of error messages
        """
        return self.validation_errors
