"""
Unit tests for the database module (db.py)
Tests database operations with mocked psycopg connections.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock, call
import os
from db import (
    get_connection,
    save_itinerary,
    update_itinerary,
    delete_itinerary,
    get_history,
    get_itinerary_details,
    save_chat_message,
    load_chat_history
)


def create_mock_db_connection():
    """Helper to create a properly mocked database connection"""
    mock_conn = Mock()
    mock_cursor = Mock()
    mock_conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__exit__ = Mock(return_value=False)
    return mock_conn, mock_cursor


class TestGetConnection:
    """Test suite for database connection management"""
    
    @patch('db.psycopg.connect')
    def test_connection_success(self, mock_connect):
        """Test successful database connection"""
        mock_conn = Mock()
        mock_connect.return_value = mock_conn
        
        with patch.dict(os.environ, {'DATABASE_URL': 'postgresql://test'}):
            result = get_connection()
            
            assert result == mock_conn
            mock_connect.assert_called_once_with('postgresql://test', sslmode='require')
    
    def test_connection_missing_url(self):
        """Test connection returns None when DATABASE_URL is missing"""
        with patch.dict(os.environ, {}, clear=True):
            result = get_connection()
            assert result is None
    
    @patch('db.psycopg.connect')
    def test_connection_failure(self, mock_connect):
        """Test connection returns None on exception"""
        mock_connect.side_effect = Exception("Connection failed")
        
        with patch.dict(os.environ, {'DATABASE_URL': 'postgresql://test'}):
            result = get_connection()
            assert result is None


class TestSaveItinerary:
    """Test suite for save_itinerary function"""
    
    @patch('db.get_connection')
    def test_save_itinerary_success(self, mock_get_conn):
        """Test successful itinerary save"""
        mock_conn, mock_cursor = create_mock_db_connection()
        mock_get_conn.return_value = mock_conn
        
        with patch('streamlit.toast'):
            save_itinerary('Paris, France', 'June', 'Test itinerary content')
        
        # Verify SQL execution
        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args
        assert 'INSERT INTO saved_itineraries' in call_args[0][0]
        assert call_args[0][1] == ('Paris, France [June]', 0, 'Test itinerary content')
        
        # Verify commit and close
        mock_conn.commit.assert_called_once()
        mock_conn.close.assert_called_once()
    
    @patch('db.get_connection')
    def test_save_itinerary_no_connection(self, mock_get_conn):
        """Test save_itinerary handles no connection gracefully"""
        mock_get_conn.return_value = None
        
        # Should not raise exception
        save_itinerary('Paris', 'June', 'Content')
    
    @patch('db.get_connection')
    def test_save_itinerary_toast_exception(self, mock_get_conn):
        """Test that toast exceptions are caught"""
        mock_conn, mock_cursor = create_mock_db_connection()
        mock_get_conn.return_value = mock_conn
        
        with patch('streamlit.toast', side_effect=Exception("Streamlit not available")):
            # Should not raise exception
            save_itinerary('Paris', 'June', 'Content')


class TestUpdateItinerary:
    """Test suite for update_itinerary function"""
    
    @patch('db.get_connection')
    def test_update_itinerary_success(self, mock_get_conn):
        """Test successful itinerary update"""
        mock_conn, mock_cursor = create_mock_db_connection()
        mock_get_conn.return_value = mock_conn
        
        with patch('streamlit.toast'):
            update_itinerary(123, 'Updated content')
        
        # Verify SQL execution
        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args
        assert 'UPDATE saved_itineraries' in call_args[0][0]
        assert call_args[0][1] == ('Updated content', 123)
        
        mock_conn.commit.assert_called_once()
        mock_conn.close.assert_called_once()
    
    @patch('db.get_connection')
    def test_update_itinerary_no_connection(self, mock_get_conn):
        """Test update handles no connection gracefully"""
        mock_get_conn.return_value = None
        
        # Should not raise exception
        update_itinerary(123, 'Content')


class TestDeleteItinerary:
    """Test suite for delete_itinerary function"""
    
    @patch('db.get_connection')
    def test_delete_itinerary_success(self, mock_get_conn):
        """Test successful itinerary deletion"""
        mock_conn, mock_cursor = create_mock_db_connection()
        mock_get_conn.return_value = mock_conn
        
        with patch('streamlit.toast'):
            delete_itinerary(456)
        
        # Verify SQL execution
        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args
        assert 'DELETE FROM saved_itineraries' in call_args[0][0]
        assert call_args[0][1] == (456,)
        
        mock_conn.commit.assert_called_once()
        mock_conn.close.assert_called_once()
    
    @patch('db.get_connection')
    def test_delete_itinerary_no_connection(self, mock_get_conn):
        """Test delete handles no connection gracefully"""
        mock_get_conn.return_value = None
        
        # Should not raise exception
        delete_itinerary(456)


class TestGetHistory:
    """Test suite for get_history function"""
    
    @patch('db.get_connection')
    def test_get_history_success(self, mock_get_conn):
        """Test successful retrieval of itinerary history"""
        from datetime import datetime
        mock_conn, mock_cursor = create_mock_db_connection()
        mock_cursor.fetchall.return_value = [
            (1, 'Paris, France [June]', datetime(2025, 1, 1)),
            (2, 'London, UK [December]', datetime(2025, 2, 1))
        ]
        mock_get_conn.return_value = mock_conn
        
        result = get_history()
        
        assert len(result) == 2
        assert result[0][0] == 1
        assert result[0][1] == 'Paris, France [June]'
        mock_cursor.execute.assert_called_once()
        assert 'ORDER BY created_at DESC' in mock_cursor.execute.call_args[0][0]
    
    @patch('db.get_connection')
    def test_get_history_no_connection(self, mock_get_conn):
        """Test get_history returns empty list with no connection"""
        mock_get_conn.return_value = None
        
        result = get_history()
        assert result == []
    
    @patch('db.get_connection')
    def test_get_history_empty_database(self, mock_get_conn):
        """Test get_history with empty database"""
        mock_conn, mock_cursor = create_mock_db_connection()
        mock_cursor.fetchall.return_value = []
        mock_get_conn.return_value = mock_conn
        
        result = get_history()
        assert result == []


class TestGetItineraryDetails:
    """Test suite for get_itinerary_details function"""
    
    @patch('db.get_connection')
    def test_get_itinerary_details_success(self, mock_get_conn):
        """Test successful retrieval of itinerary details"""
        mock_conn, mock_cursor = create_mock_db_connection()
        mock_cursor.fetchone.return_value = ('Paris, France', 'Detailed itinerary content')
        mock_get_conn.return_value = mock_conn
        
        result = get_itinerary_details(123)
        
        assert result == ('Paris, France', 'Detailed itinerary content')
        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args
        assert 'SELECT destination, itinerary_text' in call_args[0][0]
        assert call_args[0][1] == (123,)
    
    @patch('db.get_connection')
    def test_get_itinerary_details_no_connection(self, mock_get_conn):
        """Test get_itinerary_details returns None with no connection"""
        mock_get_conn.return_value = None
        
        result = get_itinerary_details(123)
        assert result is None
    
    @patch('db.get_connection')
    def test_get_itinerary_details_not_found(self, mock_get_conn):
        """Test get_itinerary_details when ID not found"""
        mock_conn, mock_cursor = create_mock_db_connection()
        mock_cursor.fetchone.return_value = None
        mock_get_conn.return_value = mock_conn
        
        result = get_itinerary_details(999)
        assert result is None


class TestSaveChatMessage:
    """Test suite for save_chat_message function"""
    
    @patch('db.get_connection')
    def test_save_chat_message_success(self, mock_get_conn):
        """Test successful chat message save"""
        mock_conn, mock_cursor = create_mock_db_connection()
        mock_get_conn.return_value = mock_conn
        
        save_chat_message(123, 'user', 'Hello, what should I visit?')
        
        # Verify SQL execution
        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args
        assert 'INSERT INTO trip_chats' in call_args[0][0]
        assert call_args[0][1] == (123, 'user', 'Hello, what should I visit?')
        
        mock_conn.commit.assert_called_once()
        mock_conn.close.assert_called_once()
    
    @patch('db.get_connection')
    def test_save_chat_message_assistant(self, mock_get_conn):
        """Test saving assistant message"""
        mock_conn, mock_cursor = create_mock_db_connection()
        mock_get_conn.return_value = mock_conn
        
        save_chat_message(123, 'assistant', 'You should visit the Eiffel Tower.')
        
        call_args = mock_cursor.execute.call_args
        assert call_args[0][1] == (123, 'assistant', 'You should visit the Eiffel Tower.')
    
    @patch('db.get_connection')
    def test_save_chat_message_no_connection(self, mock_get_conn):
        """Test save_chat_message handles no connection gracefully"""
        mock_get_conn.return_value = None
        
        # Should not raise exception
        save_chat_message(123, 'user', 'Test message')


class TestLoadChatHistory:
    """Test suite for load_chat_history function"""
    
    @patch('db.get_connection')
    def test_load_chat_history_success(self, mock_get_conn):
        """Test successful loading of chat history"""
        mock_conn, mock_cursor = create_mock_db_connection()
        mock_cursor.fetchall.return_value = [
            ('user', 'Hello'),
            ('assistant', 'Hi there!'),
            ('user', 'Tell me about Paris')
        ]
        mock_get_conn.return_value = mock_conn
        
        result = load_chat_history(123)
        
        assert len(result) == 3
        assert result[0] == {'role': 'user', 'content': 'Hello'}
        assert result[1] == {'role': 'assistant', 'content': 'Hi there!'}
        assert result[2] == {'role': 'user', 'content': 'Tell me about Paris'}
        
        # Verify SQL query
        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args
        assert 'ORDER BY created_at ASC' in call_args[0][0]
        assert call_args[0][1] == (123,)
    
    @patch('db.get_connection')
    def test_load_chat_history_no_connection(self, mock_get_conn):
        """Test load_chat_history returns empty list with no connection"""
        mock_get_conn.return_value = None
        
        result = load_chat_history(123)
        assert result == []
    
    @patch('db.get_connection')
    def test_load_chat_history_empty(self, mock_get_conn):
        """Test load_chat_history with no messages"""
        mock_conn, mock_cursor = create_mock_db_connection()
        mock_cursor.fetchall.return_value = []
        mock_get_conn.return_value = mock_conn
        
        result = load_chat_history(123)
        assert result == []


# Integration-style tests
class TestDatabaseIntegration:
    """Integration tests for database operations"""
    
    @patch('db.get_connection')
    def test_full_itinerary_lifecycle(self, mock_get_conn):
        """Test complete lifecycle: save, update, retrieve, delete"""
        mock_conn, mock_cursor = create_mock_db_connection()
        mock_get_conn.return_value = mock_conn
        
        with patch('streamlit.toast'):
            # Save
            save_itinerary('Paris', 'June', 'Original content')
            assert mock_cursor.execute.call_count == 1
            
            # Update
            update_itinerary(1, 'Updated content')
            assert mock_cursor.execute.call_count == 2
            
            # Delete
            delete_itinerary(1)
            assert mock_cursor.execute.call_count == 3
        
        # Verify all operations committed
        assert mock_conn.commit.call_count == 3
    
    @patch('db.get_connection')
    def test_chat_conversation_flow(self, mock_get_conn):
        """Test saving and loading a complete chat conversation"""
        mock_conn, mock_cursor = create_mock_db_connection()
        mock_get_conn.return_value = mock_conn
        
        # Save multiple messages
        save_chat_message(1, 'user', 'First question')
        save_chat_message(1, 'assistant', 'First answer')
        save_chat_message(1, 'user', 'Second question')
        
        # Verify three inserts
        assert mock_cursor.execute.call_count == 3
        
        # Mock loading the conversation
        mock_cursor.fetchall.return_value = [
            ('user', 'First question'),
            ('assistant', 'First answer'),
            ('user', 'Second question')
        ]
        
        history = load_chat_history(1)
        assert len(history) == 3
        assert history[0]['role'] == 'user'
        assert history[1]['role'] == 'assistant'
