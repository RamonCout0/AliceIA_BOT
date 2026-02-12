"""Tests for History Manager."""

import pytest
import json
import os
import tempfile
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from hypothesis import given, strategies as st

from alice.core.history_manager import HistoryManager, HistoryEntry, HistoryFilter
from alice.core.logger import Logger


@pytest.fixture
def temp_dir():
    """Create temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        old_cwd = os.getcwd()
        os.chdir(tmpdir)
        yield tmpdir
        os.chdir(old_cwd)


@pytest.fixture
def mock_config():
    """Create mock config."""
    config = Mock()
    config.history_archive_days = 30
    return config


@pytest.fixture
def mock_logger():
    """Create mock logger."""
    return Mock(spec=Logger)


@pytest.fixture
def mock_error_handler():
    """Create mock error handler."""
    return Mock()


@pytest.fixture
def history_manager(mock_config, mock_logger, mock_error_handler, temp_dir):
    """Create HistoryManager instance."""
    return HistoryManager(mock_config, mock_logger, mock_error_handler)


class TestHistoryEntry:
    """Test HistoryEntry dataclass."""

    def test_create_entry(self):
        """Test creating a history entry."""
        now = datetime.now().isoformat()
        entry = HistoryEntry(
            timestamp=now,
            source="gameplay",
            content="test content"
        )
        
        assert entry.timestamp == now
        assert entry.source == "gameplay"
        assert entry.content == "test content"
        assert entry.metadata == {}

    def test_create_entry_with_metadata(self):
        """Test creating entry with metadata."""
        now = datetime.now().isoformat()
        metadata = {"key": "value"}
        entry = HistoryEntry(
            timestamp=now,
            source="discord",
            content="test",
            metadata=metadata
        )
        
        assert entry.metadata == metadata


class TestAddEntry:
    """Test adding entries to history."""

    def test_add_single_entry(self, history_manager):
        """Test adding a single entry."""
        now = datetime.now().isoformat()
        entry = HistoryEntry(
            timestamp=now,
            source="gameplay",
            content="test"
        )
        
        history_manager.add_entry(entry)
        
        assert len(history_manager.history) == 1
        assert history_manager.history[0] == entry

    def test_add_multiple_entries(self, history_manager):
        """Test adding multiple entries."""
        now = datetime.now().isoformat()
        
        for i in range(5):
            entry = HistoryEntry(
                timestamp=now,
                source="gameplay",
                content=f"test {i}"
            )
            history_manager.add_entry(entry)
        
        assert len(history_manager.history) == 5

    def test_add_entry_persists_to_disk(self, history_manager):
        """Test that adding entry persists to disk."""
        now = datetime.now().isoformat()
        entry = HistoryEntry(
            timestamp=now,
            source="gameplay",
            content="test"
        )
        
        history_manager.add_entry(entry)
        
        # Verify file exists
        assert os.path.exists("history.json")
        
        # Verify content
        with open("history.json", "r") as f:
            data = json.load(f)
        
        assert len(data) == 1
        assert data[0]["content"] == "test"


class TestQueryHistory:
    """Test querying history."""

    def test_get_all_history(self, history_manager):
        """Test getting all history."""
        now = datetime.now().isoformat()
        
        for i in range(3):
            entry = HistoryEntry(
                timestamp=now,
                source="gameplay",
                content=f"test {i}"
            )
            history_manager.add_entry(entry)
        
        result = history_manager.get_history()
        
        assert len(result) == 3

    def test_filter_by_source(self, history_manager):
        """Test filtering by source."""
        now = datetime.now().isoformat()
        
        # Add gameplay entries
        for i in range(2):
            entry = HistoryEntry(
                timestamp=now,
                source="gameplay",
                content=f"gameplay {i}"
            )
            history_manager.add_entry(entry)
        
        # Add discord entries
        for i in range(3):
            entry = HistoryEntry(
                timestamp=now,
                source="discord",
                content=f"discord {i}"
            )
            history_manager.add_entry(entry)
        
        # Filter by source
        filter_obj = HistoryFilter(source="gameplay")
        result = history_manager.get_history(filter_obj)
        
        assert len(result) == 2
        assert all(e.source == "gameplay" for e in result)

    def test_filter_by_content(self, history_manager):
        """Test filtering by content search."""
        now = datetime.now().isoformat()
        
        entries_data = [
            ("apple", "gameplay"),
            ("banana", "gameplay"),
            ("apple pie", "discord"),
        ]
        
        for content, source in entries_data:
            entry = HistoryEntry(
                timestamp=now,
                source=source,
                content=content
            )
            history_manager.add_entry(entry)
        
        # Filter by content
        filter_obj = HistoryFilter(content_search="apple")
        result = history_manager.get_history(filter_obj)
        
        assert len(result) == 2
        assert all("apple" in e.content.lower() for e in result)

    def test_filter_by_time_range(self, history_manager):
        """Test filtering by time range."""
        now = datetime.now()
        
        # Add entries at different times
        for i in range(3):
            timestamp = (now - timedelta(days=i)).isoformat()
            entry = HistoryEntry(
                timestamp=timestamp,
                source="gameplay",
                content=f"test {i}"
            )
            history_manager.add_entry(entry)
        
        # Filter by time range
        start = now - timedelta(days=1.5)
        end = now
        filter_obj = HistoryFilter(start_time=start, end_time=end)
        result = history_manager.get_history(filter_obj)
        
        assert len(result) == 2

    def test_combined_filters(self, history_manager):
        """Test combining multiple filters."""
        now = datetime.now()
        
        # Add mixed entries
        for i in range(5):
            timestamp = (now - timedelta(days=i)).isoformat()
            source = "gameplay" if i % 2 == 0 else "discord"
            content = f"apple {i}" if i < 3 else f"banana {i}"
            
            entry = HistoryEntry(
                timestamp=timestamp,
                source=source,
                content=content
            )
            history_manager.add_entry(entry)
        
        # Filter by source and content
        start = now - timedelta(days=3)
        filter_obj = HistoryFilter(
            source="gameplay",
            content_search="apple",
            start_time=start
        )
        result = history_manager.get_history(filter_obj)
        
        assert all(e.source == "gameplay" for e in result)
        assert all("apple" in e.content.lower() for e in result)


class TestArchival:
    """Test history archival."""

    def test_archive_old_entries(self, history_manager, mock_config):
        """Test archiving old entries."""
        mock_config.history_archive_days = 1
        
        now = datetime.now()
        
        # Add old entry
        old_time = (now - timedelta(days=2)).isoformat()
        old_entry = HistoryEntry(
            timestamp=old_time,
            source="gameplay",
            content="old"
        )
        history_manager.add_entry(old_entry)
        
        # Add recent entry
        recent_time = now.isoformat()
        recent_entry = HistoryEntry(
            timestamp=recent_time,
            source="gameplay",
            content="recent"
        )
        history_manager.add_entry(recent_entry)
        
        # Archive
        history_manager.archive_old_entries()
        
        # Verify old entry is archived
        assert len(history_manager.history) == 1
        assert history_manager.history[0].content == "recent"
        
        # Verify archive file exists
        assert os.path.exists("history_archive.json")

    def test_archive_preserves_recent_entries(self, history_manager, mock_config):
        """Test that archival preserves recent entries."""
        mock_config.history_archive_days = 1
        
        now = datetime.now()
        
        # Add entries - only the last one should be recent (within 1 day)
        for i in range(5):
            if i == 4:
                # Most recent entry (today)
                timestamp = now.isoformat()
            else:
                # Older entries (5, 4, 3, 2 days ago)
                days_ago = 5 - i
                timestamp = (now - timedelta(days=days_ago)).isoformat()
            
            entry = HistoryEntry(
                timestamp=timestamp,
                source="gameplay",
                content=f"entry {i}"
            )
            history_manager.add_entry(entry)
        
        # Archive
        history_manager.archive_old_entries()
        
        # Verify only recent entries remain (within 1 day)
        assert len(history_manager.history) >= 1
        for entry in history_manager.history:
            entry_time = datetime.fromisoformat(entry.timestamp)
            age_days = (now - entry_time).days
            assert age_days <= 1


class TestPersistence:
    """Test persistence and recovery."""

    def test_load_from_disk(self, mock_config, mock_logger, mock_error_handler, temp_dir):
        """Test loading history from disk."""
        # Create history file
        data = [
            {
                "timestamp": datetime.now().isoformat(),
                "source": "gameplay",
                "content": "test",
                "metadata": {}
            }
        ]
        
        with open("history.json", "w") as f:
            json.dump(data, f)
        
        # Load
        manager = HistoryManager(mock_config, mock_logger, mock_error_handler)
        
        assert len(manager.history) == 1
        assert manager.history[0].content == "test"

    def test_crash_recovery(self, history_manager):
        """Test recovery after crash."""
        now = datetime.now().isoformat()
        
        # Add entries
        for i in range(3):
            entry = HistoryEntry(
                timestamp=now,
                source="gameplay",
                content=f"test {i}"
            )
            history_manager.add_entry(entry)
        
        # Simulate crash by creating new manager
        new_manager = HistoryManager(
            history_manager.config,
            history_manager.logger,
            history_manager.error_handler
        )
        
        # Verify all entries recovered
        assert len(new_manager.history) == 3


# Property-based tests

def test_property_history_persistence_round_trip():
    """Property 2: History Persistence Round Trip.
    
    For any history entry added to the History_Manager, if the system is 
    restarted, querying the history should return an equivalent entry 
    without data loss.
    
    Validates: Requirements 2.2, 2.3
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        old_cwd = os.getcwd()
        os.chdir(tmpdir)
        
        try:
            config = Mock()
            config.history_archive_days = 30
            logger = Mock(spec=Logger)
            error_handler = Mock()
            
            # Create manager and add entry
            manager1 = HistoryManager(config, logger, error_handler)
            now = datetime.now().isoformat()
            entry = HistoryEntry(
                timestamp=now,
                source="gameplay",
                content="test content"
            )
            manager1.add_entry(entry)
            
            # Create new manager (simulating restart)
            manager2 = HistoryManager(config, logger, error_handler)
            
            # Verify entry is recovered
            assert len(manager2.history) == 1
            assert manager2.history[0].content == "test content"
            assert manager2.history[0].source == "gameplay"
        finally:
            os.chdir(old_cwd)


def test_property_history_archival_preserves_recent():
    """Property 3: History Archival Preserves Recent Entries.
    
    For any History_Manager with entries spanning multiple days, when 
    archival is triggered at the size limit, all entries within the 
    configured recent threshold should remain in active history.
    
    Validates: Requirements 2.5
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        old_cwd = os.getcwd()
        os.chdir(tmpdir)
        
        try:
            config = Mock()
            config.history_archive_days = 1
            logger = Mock(spec=Logger)
            error_handler = Mock()
            
            manager = HistoryManager(config, logger, error_handler)
            now = datetime.now()
            
            # Add entries spanning multiple days
            for i in range(5):
                if i == 4:
                    # Most recent entry (today)
                    timestamp = now.isoformat()
                else:
                    # Older entries (5, 4, 3, 2 days ago)
                    days_ago = 5 - i
                    timestamp = (now - timedelta(days=days_ago)).isoformat()
                
                entry = HistoryEntry(
                    timestamp=timestamp,
                    source="gameplay",
                    content=f"entry {i}"
                )
                manager.add_entry(entry)
            
            # Archive
            manager.archive_old_entries()
            
            # Verify recent entries are preserved
            assert len(manager.history) >= 1
            for entry in manager.history:
                entry_time = datetime.fromisoformat(entry.timestamp)
                age_days = (now - entry_time).days
                assert age_days <= 1
        finally:
            os.chdir(old_cwd)


def test_property_history_query_correctness():
    """Property 4: History Query Correctness.
    
    For any set of history entries with different timestamps, sources, 
    and content, querying by timestamp should return only entries within 
    the specified range, querying by source should return only entries 
    from that source, and querying by content should return only entries 
    containing that content.
    
    Validates: Requirements 2.6
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        old_cwd = os.getcwd()
        os.chdir(tmpdir)
        
        try:
            config = Mock()
            config.history_archive_days = 30
            logger = Mock(spec=Logger)
            error_handler = Mock()
            
            manager = HistoryManager(config, logger, error_handler)
            now = datetime.now()
            
            # Add diverse entries
            entries_data = [
                (now - timedelta(days=2), "gameplay", "apple"),
                (now - timedelta(days=1), "discord", "banana"),
                (now, "gameplay", "apple pie"),
            ]
            
            for timestamp, source, content in entries_data:
                entry = HistoryEntry(
                    timestamp=timestamp.isoformat(),
                    source=source,
                    content=content
                )
                manager.add_entry(entry)
            
            # Test source filter
            filter_obj = HistoryFilter(source="gameplay")
            result = manager.get_history(filter_obj)
            assert all(e.source == "gameplay" for e in result)
            assert len(result) == 2
            
            # Test content filter
            filter_obj = HistoryFilter(content_search="apple")
            result = manager.get_history(filter_obj)
            assert all("apple" in e.content.lower() for e in result)
            assert len(result) == 2
            
            # Test time range filter
            start = now - timedelta(days=1.5)
            end = now
            filter_obj = HistoryFilter(start_time=start, end_time=end)
            result = manager.get_history(filter_obj)
            assert len(result) == 2
        finally:
            os.chdir(old_cwd)
