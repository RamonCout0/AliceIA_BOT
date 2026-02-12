"""Vision Engine with Groq integration."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any

from alice.core.logger import Logger
from alice.core.error_handler import ErrorHandler
from alice.core.schema_validator import SchemaValidator


@dataclass
class GameplayDecision:
    """Represents a gameplay decision from vision analysis."""
    
    action: str  # e.g., "move_left", "attack", "use_item"
    parameters: Dict[str, Any]  # Action-specific parameters
    confidence: float  # 0.0 to 1.0
    reasoning: str  # Why this decision was made
    timestamp: datetime


class VisionEngine:
    """Analyzes screenshots using Groq/Llama Vision."""

    def __init__(
        self,
        config: Any,
        logger: Logger,
        error_handler: ErrorHandler,
        schema_validator: SchemaValidator
    ):
        """Initialize VisionEngine.
        
        Args:
            config: Configuration object
            logger: Logger instance
            error_handler: ErrorHandler instance
            schema_validator: SchemaValidator instance
        """
        self.config = config
        self.logger = logger
        self.error_handler = error_handler
        self.schema_validator = schema_validator
        
        # Groq API settings
        self.groq_api_key = getattr(config, "groq_api_key", "")
        self.groq_timeout_ms = getattr(config, "groq_timeout_ms", 30000)
        
        self.status = "idle"
        
        self.logger.info(
            "VisionEngine",
            "Vision engine initialized",
            {}
        )

    def analyze_screenshot(self, screenshot: bytes) -> Optional[GameplayDecision]:
        """Analyze screenshot and return decision.
        
        Args:
            screenshot: Screenshot bytes
            
        Returns:
            GameplayDecision or None if analysis fails
        """
        self.status = "analyzing"
        
        try:
            # Call Groq API with retry logic
            response = self.error_handler.execute_with_retry(
                self._call_groq_api,
                screenshot,
                timeout_ms=self.groq_timeout_ms
            )
            
            # Validate response
            if not self.schema_validator.validate_groq_response(response):
                self.logger.error(
                    "VisionEngine",
                    "Invalid Groq response",
                    {
                        "errors": self.schema_validator.get_validation_errors()[:3]
                    }
                )
                self.status = "idle"
                return None
            
            # Parse response into GameplayDecision
            decision = self._parse_response(response)
            
            self.logger.info(
                "VisionEngine",
                f"Screenshot analyzed: {decision.action}",
                {
                    "action": decision.action,
                    "confidence": decision.confidence,
                }
            )
            
            self.status = "idle"
            return decision
            
        except Exception as error:
            self.logger.error(
                "VisionEngine",
                "Screenshot analysis failed",
                {
                    "error_type": type(error).__name__,
                    "error_message": str(error),
                }
            )
            self.status = "error"
            return None

    def get_status(self) -> str:
        """Get current status.
        
        Returns:
            Current status (idle, analyzing, error)
        """
        return self.status

    def _call_groq_api(self, screenshot: bytes) -> Dict[str, Any]:
        """Call Groq API with screenshot.
        
        Args:
            screenshot: Screenshot bytes
            
        Returns:
            API response
        """
        # In a real implementation, this would call the actual Groq API
        # For now, return a mock response
        return {
            "choices": [
                {
                    "message": {
                        "content": "move_left"
                    }
                }
            ],
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 50
            },
            "model": "llama-2-vision"
        }

    def _parse_response(self, response: Dict[str, Any]) -> GameplayDecision:
        """Parse Groq API response into GameplayDecision.
        
        Args:
            response: Groq API response
            
        Returns:
            GameplayDecision
        """
        # Extract content from response
        content = response["choices"][0]["message"]["content"]
        
        # Parse action and parameters from content
        # In a real implementation, this would parse the actual response
        action = content.split()[0] if content else "idle"
        
        return GameplayDecision(
            action=action,
            parameters={},
            confidence=0.8,
            reasoning="Analyzed screenshot using Groq Vision",
            timestamp=datetime.now()
        )
