"""History Manager with persistence."""

import json
import os
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from alice.core.logger import Logger


@dataclass
class HistoryEntry:
    """Represents a history entry."""
    
    timestamp: str  # ISO format datetime
    source: str  # "gameplay" or "discord"
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HistoryFilter:
    """Filter for querying history."""
    
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    source: Optional[str] = None
    content_search: Optional[str] = None


class HistoryManager:
    """Manages conversation and gameplay history with persistence."""

    def __init__(self, config: Any, logger: Logger, error_handler: Any):
        """Initialize HistoryManager.
        
        Args:
            config: Configuration object
            logger: Logger instance
            error_handler: ErrorHandler instance
        """
        self.config = config
        self.logger = logger
        self.error_handler = error_handler
        self.history: List[HistoryEntry] = []
        self.history_file = "history.json"
        self.archive_file = "history_archive.json"
        
        # Load existing history from disk
        self.load_from_disk()

    def add_entry(self, entry: HistoryEntry) -> None:
        """Add entry and persist immediately.
        
        Args:
            entry: HistoryEntry to add
        """
        self.history.append(entry)
        self._persist_to_disk()
        
        self.logger.info(
            "HistoryManager",
            f"Added history entry from {entry.source}",
            {
                "source": entry.source,
                "content_length": len(entry.content),
                "total_entries": len(self.history),
            }
        )

    def get_history(self, filters: Optional[HistoryFilter] = None) -> List[HistoryEntry]:
        """Query history by timestamp, source, or content.
        
        Args:
            filters: HistoryFilter with optional criteria
            
        Returns:
            List of matching HistoryEntry objects
        """
        if filters is None:
            return self.history.copy()
        
        result = self.history.copy()
        
        # Filter by time range
        if filters.start_time:
            start_iso = filters.start_time.isoformat()
            result = [e for e in result if e.timestamp >= start_iso]
        
        if filters.end_time:
            end_iso = filters.end_time.isoformat()
            result = [e for e in result if e.timestamp <= end_iso]
        
        # Filter by source
        if filters.source:
            result = [e for e in result if e.source == filters.source]
        
        # Filter by content search
        if filters.content_search:
            search_lower = filters.content_search.lower()
            result = [e for e in result if search_lower in e.content.lower()]
        
        return result

    def archive_old_entries(self) -> None:
        """Archive entries older than configured threshold."""
        archive_days = getattr(self.config, "history_archive_days", 30)
        cutoff_time = datetime.now() - timedelta(days=archive_days)
        cutoff_iso = cutoff_time.isoformat()
        
        # Separate old and recent entries
        old_entries = []
        recent_entries = []
        
        for entry in self.history:
            # Parse entry timestamp and compare
            try:
                entry_time = datetime.fromisoformat(entry.timestamp)
                if entry_time < cutoff_time:
                    old_entries.append(entry)
                else:
                    recent_entries.append(entry)
            except ValueError:
                # If timestamp parsing fails, keep in recent
                recent_entries.append(entry)
        
        if old_entries:
            # Append old entries to archive file
            self._append_to_archive(old_entries)
            
            # Keep only recent entries in memory
            self.history = recent_entries
            self._persist_to_disk()
            
            self.logger.info(
                "HistoryManager",
                f"Archived {len(old_entries)} old entries",
                {
                    "archived_count": len(old_entries),
                    "remaining_count": len(recent_entries),
                    "archive_days": archive_days,
                }
            )

    def load_from_disk(self) -> None:
        """Load history from persistent storage."""
        if not os.path.exists(self.history_file):
            self.logger.info(
                "HistoryManager",
                "No history file found, starting with empty history",
                {}
            )
            return
        
        try:
            with open(self.history_file, "r") as f:
                data = json.load(f)
            
            self.history = [
                HistoryEntry(
                    timestamp=entry["timestamp"],
                    source=entry["source"],
                    content=entry["content"],
                    metadata=entry.get("metadata", {})
                )
                for entry in data
            ]
            
            self.logger.info(
                "HistoryManager",
                f"Loaded {len(self.history)} entries from disk",
                {"entry_count": len(self.history)}
            )
        except Exception as error:
            self.logger.error(
                "HistoryManager",
                "Failed to load history from disk",
                {
                    "error_type": type(error).__name__,
                    "error_message": str(error),
                }
            )
            self.history = []

    def _persist_to_disk(self) -> None:
        """Persist history to disk."""
        try:
            with open(self.history_file, "w") as f:
                data = [asdict(entry) for entry in self.history]
                json.dump(data, f, indent=2)
        except Exception as error:
            self.logger.error(
                "HistoryManager",
                "Failed to persist history to disk",
                {
                    "error_type": type(error).__name__,
                    "error_message": str(error),
                }
            )

    def _append_to_archive(self, entries: List[HistoryEntry]) -> None:
        """Append entries to archive file."""
        try:
            # Load existing archive
            archived = []
            if os.path.exists(self.archive_file):
                with open(self.archive_file, "r") as f:
                    archived = json.load(f)
            
            # Append new entries
            archived.extend([asdict(entry) for entry in entries])
            
            # Save archive
            with open(self.archive_file, "w") as f:
                json.dump(archived, f, indent=2)
        except Exception as error:
            self.logger.error(
                "HistoryManager",
                "Failed to append to archive",
                {
                    "error_type": type(error).__name__,
                    "error_message": str(error),
                }
            )
