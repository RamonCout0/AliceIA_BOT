"""Discord Bot with Gemini integration."""

from datetime import datetime
from typing import Optional, Dict, Any

from alice.core.logger import Logger
from alice.core.error_handler import ErrorHandler
from alice.core.schema_validator import SchemaValidator
from alice.core.history_manager import HistoryManager, HistoryEntry


class DiscordBot:
    """Handles Discord chat integration using Google Gemini."""

    def __init__(
        self,
        config: Any,
        logger: Logger,
        error_handler: ErrorHandler,
        schema_validator: SchemaValidator,
        history_manager: HistoryManager
    ):
        """Initialize DiscordBot.
        
        Args:
            config: Configuration object
            logger: Logger instance
            error_handler: ErrorHandler instance
            schema_validator: SchemaValidator instance
            history_manager: HistoryManager instance
        """
        self.config = config
        self.logger = logger
        self.error_handler = error_handler
        self.schema_validator = schema_validator
        self.history_manager = history_manager
        
        # Discord settings
        self.discord_token = getattr(config, "discord_token", "")
        self.gemini_api_key = getattr(config, "gemini_api_key", "")
        self.gemini_timeout_ms = getattr(config, "gemini_timeout_ms", 30000)
        
        self.status = "disconnected"
        
        self.logger.info(
            "DiscordBot",
            "Discord bot initialized",
            {}
        )

    def send_message(self, channel_id: str, message: str) -> None:
        """Send message to Discord channel.
        
        Args:
            channel_id: Discord channel ID
            message: Message to send
        """
        try:
            # In a real implementation, this would send to Discord
            self.logger.info(
                "DiscordBot",
                f"Message sent to channel {channel_id}",
                {
                    "channel_id": channel_id,
                    "message_length": len(message),
                }
            )
        except Exception as error:
            self.logger.error(
                "DiscordBot",
                f"Failed to send message to channel {channel_id}",
                {
                    "channel_id": channel_id,
                    "error_type": type(error).__name__,
                    "error_message": str(error),
                }
            )

    def process_message(self, message: str) -> str:
        """Process message with Gemini and return response.
        
        Args:
            message: User message
            
        Returns:
            Response from Gemini
        """
        try:
            # Call Gemini API with retry logic
            response = self.error_handler.execute_with_retry(
                self._call_gemini_api,
                message,
                timeout_ms=self.gemini_timeout_ms
            )
            
            # Validate response
            if not self.schema_validator.validate_gemini_response(response):
                self.logger.error(
                    "DiscordBot",
                    "Invalid Gemini response",
                    {
                        "errors": self.schema_validator.get_validation_errors()[:3]
                    }
                )
                return "Sorry, I encountered an error processing your message."
            
            # Parse response
            reply = self._parse_response(response)
            
            # Add to history
            entry = HistoryEntry(
                timestamp=datetime.now().isoformat(),
                source="discord",
                content=f"User: {message}\nBot: {reply}"
            )
            self.history_manager.add_entry(entry)
            
            self.logger.info(
                "DiscordBot",
                "Message processed successfully",
                {
                    "message_length": len(message),
                    "reply_length": len(reply),
                }
            )
            
            return reply
            
        except Exception as error:
            self.logger.error(
                "DiscordBot",
                "Message processing failed",
                {
                    "error_type": type(error).__name__,
                    "error_message": str(error),
                }
            )
            return "Sorry, I encountered an error processing your message."

    def get_status(self) -> str:
        """Get current status.
        
        Returns:
            Current status (connected, disconnected, error)
        """
        return self.status

    def _call_gemini_api(self, message: str) -> Dict[str, Any]:
        """Call Gemini API with message.
        
        Args:
            message: User message
            
        Returns:
            API response
        """
        # In a real implementation, this would call the actual Gemini API
        # For now, return a mock response
        return {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": f"I received your message: {message}"
                            }
                        ]
                    }
                }
            ]
        }

    def _parse_response(self, response: Dict[str, Any]) -> str:
        """Parse Gemini API response.
        
        Args:
            response: Gemini API response
            
        Returns:
            Parsed response text
        """
        try:
            # Extract text from response
            candidates = response.get("candidates", [])
            if not candidates:
                return "No response generated"
            
            content = candidates[0].get("content", {})
            parts = content.get("parts", [])
            if not parts:
                return "No response generated"
            
            text = parts[0].get("text", "No response generated")
            return text
        except Exception as error:
            self.logger.error(
                "DiscordBot",
                "Failed to parse Gemini response",
                {
                    "error_type": type(error).__name__,
                    "error_message": str(error),
                }
            )
            return "Failed to parse response"
