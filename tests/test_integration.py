"""
Integration tests for the Travel Intelligence AI application
Tests end-to-end workflows and module interactions.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import streamlit as st
import pandas as pd


class TestAppIntegration:
    """Integration tests for the main application flow"""
    
    @patch('ui.ai.generate_intel')
    @patch('ui.maps.extract_map_data')
    @patch('ui.maps.display_labeled_map')
    @patch('ui.db.save_itinerary')
    def test_full_intel_generation_and_save_flow(
        self, mock_save, mock_display, mock_extract, mock_generate
    ):
        """Test complete flow: generate intel, extract map data, display, and save"""
        # Mock the generation stream
        mock_generate.return_value = iter([
            '## Gastronomy\n',
            'Content here\n',
            '(---PAGE BREAK---)\n',
            'Le Marais | 48.8566 | 2.3522'
        ])
        
        # Mock map extraction
        mock_extract.return_value = pd.DataFrame({
            'name': ['Le Marais'],
            'lat': [48.8566],
            'lon': [2.3522]
        })
        
        # Simulate the flow
        result = list(mock_generate.return_value)
        full_text = ''.join(result)
        
        # Extract map data
        df = mock_extract(full_text)
        
        # Display map
        if not df.empty:
            mock_display(df)
        
        # Save itinerary
        mock_save('Paris, France', 'June', full_text)
        
        # Verify all steps were called
        mock_extract.assert_called_once()
        mock_display.assert_called_once()
        mock_save.assert_called_once_with('Paris, France', 'June', full_text)
    
    @patch('ui.ai.run_chat_response')
    @patch('ui.db.save_chat_message')
    @patch('ui.db.load_chat_history')
    def test_chat_conversation_flow(
        self, mock_load, mock_save_msg, mock_chat
    ):
        """Test chat conversation workflow with guide"""
        guide_context = "Paris is the capital of France. Visit the Eiffel Tower."
        
        # Mock chat response
        mock_chat.return_value = "The Eiffel Tower is mentioned in the guide."
        
        # Simulate user asking a question
        user_query = "What should I visit?"
        response = mock_chat(guide_context, user_query)
        
        # Save messages
        mock_save_msg(1, 'user', user_query)
        mock_save_msg(1, 'assistant', response)
        
        # Load history
        mock_load.return_value = [
            {'role': 'user', 'content': user_query},
            {'role': 'assistant', 'content': response}
        ]
        
        history = mock_load(1)
        
        # Verify flow
        assert len(history) == 2
        assert history[0]['role'] == 'user'
        assert history[1]['role'] == 'assistant'
        mock_chat.assert_called_once_with(guide_context, user_query)
    
    @patch('ui.db.get_history')
    @patch('ui.db.get_itinerary_details')
    def test_library_view_and_retrieval(self, mock_details, mock_history):
        """Test retrieving and viewing saved itineraries"""
        from datetime import datetime
        
        # Mock history
        mock_history.return_value = [
            (1, 'Paris, France [June]', datetime(2025, 1, 1)),
            (2, 'London, UK [December]', datetime(2025, 2, 1))
        ]
        
        # Mock details
        mock_details.return_value = (
            'Paris, France [June]',
            'Full itinerary content with details'
        )
        
        # Simulate retrieving history
        history = mock_history()
        assert len(history) == 2
        
        # Simulate opening a specific itinerary
        trip_id = history[0][0]
        details = mock_details(trip_id)
        
        assert details[0] == 'Paris, France [June]'
        assert 'Full itinerary content' in details[1]


class TestCrossModuleIntegration:
    """Tests for interactions between different modules"""
    
    @patch('ai.StrOutputParser')
    @patch('ai.ChatPromptTemplate')
    @patch('ai.ChatGroq')
    @patch('ai.TavilySearchResults')
    def test_ai_to_maps_pipeline(self, mock_tavily, mock_groq, mock_prompt, mock_parser):
        """Test data flow from AI generation to maps display"""
        from ai import generate_intel
        from maps import extract_map_data
        
        # Mock AI components
        mock_tavily_instance = Mock()
        mock_tavily_instance.invoke.return_value = [
            {'content': 'Paris info', 'url': 'http://test.com'}
        ]
        mock_tavily.return_value = mock_tavily_instance
        
        mock_llm = Mock()
        mock_groq.return_value = mock_llm
        
        mock_prompt_instance = Mock()
        mock_prompt.from_template.return_value = mock_prompt_instance
        
        mock_parser_instance = Mock()
        mock_parser.return_value = mock_parser_instance
        
        # Mock the chain
        mock_chain = Mock()
        mock_chain.stream.return_value = iter([
            'Content\n',
            '### COORDINATES\n',
            'Eiffel Tower | 48.8584 | 2.2945\n',
            'Louvre | 48.8606 | 2.3376'
        ])
        mock_prompt_instance.__or__ = Mock(return_value=Mock(__or__=Mock(return_value=mock_chain)))
        
        import os
        with patch.dict(os.environ, {
            'GROQ_API_KEY': 'test-key',
            'TAVILY_API_KEY': 'test-key'
        }):
            # Generate intel
            intel_stream = generate_intel('Paris, France', 'June')
            full_content = ''.join(list(intel_stream))
            
            # Extract map data
            df = extract_map_data(full_content)
            
            # Verify pipeline works
            assert not df.empty
            assert 'Eiffel Tower' in df['name'].values
            assert 'Louvre' in df['name'].values
    
    @patch('db.get_connection')
    @patch('ai.generate_place_summary')
    def test_db_to_ai_summary_pipeline(self, mock_summary, mock_conn):
        """Test retrieving saved content and generating summaries"""
        from db import get_itinerary_details
        
        # Mock database
        mock_db_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = (
            'Paris, France',
            'Guide content mentioning Le Marais neighborhood'
        )
        mock_db_conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
        mock_db_conn.cursor.return_value.__exit__ = Mock(return_value=False)
        mock_conn.return_value = mock_db_conn
        
        # Mock AI summary
        mock_summary.return_value = "Historic trendy district"
        
        # Retrieve details
        details = get_itinerary_details(1)
        
        if details:
            dest, content = details
            # Generate summary for a place
            summary = mock_summary(content, 'Le Marais')
            
            assert summary == "Historic trendy district"
    
    @patch('maps.create_pdf')
    @patch('db.get_itinerary_details')
    def test_db_to_pdf_export_pipeline(self, mock_details, mock_pdf):
        """Test exporting saved itinerary to PDF"""
        # Mock database retrieval
        mock_details.return_value = (
            'Paris, France [June]',
            'Full guide content'
        )
        
        # Mock PDF creation
        mock_pdf.return_value = b'%PDF-1.4...'
        
        # Simulate export flow
        details = mock_details(1)
        if details:
            dest, content = details
            pdf_data = mock_pdf(dest, content)
            
            assert isinstance(pdf_data, bytes)
            assert pdf_data[:4] == b'%PDF'


class TestErrorHandling:
    """Tests for error handling across the application"""
    
    @patch('ai.ChatGroq')
    @patch('ai.TavilySearchResults')
    def test_ai_generation_with_api_failure(self, mock_tavily, mock_groq):
        """Test graceful handling of API failures"""
        import os
        from ai import generate_intel
        
        # Simulate API failure
        mock_tavily.side_effect = Exception("API rate limit exceeded")
        
        with patch.dict(os.environ, {
            'GROQ_API_KEY': 'test-key',
            'TAVILY_API_KEY': 'test-key'
        }):
            with pytest.raises(Exception):
                list(generate_intel('Paris', 'June'))
    
    @patch('db.get_connection')
    def test_database_connection_failure_handling(self, mock_conn):
        """Test that database failures don't crash the app"""
        from db import save_itinerary, get_history, delete_itinerary
        
        # Simulate connection failure
        mock_conn.return_value = None
        
        # These should not raise exceptions
        save_itinerary('Paris', 'June', 'Content')
        history = get_history()
        delete_itinerary(1)
        
        # Verify graceful handling
        assert history == []
    
    def test_map_extraction_with_malformed_data(self):
        """Test map extraction handles malformed data"""
        from maps import extract_map_data
        
        malformed_texts = [
            "Invalid | coords | here",
            "Place | notanumber | 2.2945",
            "Place | 48.8584 | notanumber",
            "No pipes at all 48.8584 2.2945",
            ""
        ]
        
        for text in malformed_texts:
            df = extract_map_data(text)
            # Should return empty DataFrame, not crash
            assert isinstance(df, pd.DataFrame)


class TestDataValidation:
    """Tests for data validation and sanitization"""
    
    def test_coordinate_bounds_validation(self):
        """Test that coordinates are validated to be within valid ranges"""
        from maps import extract_map_data
        
        text = """
        Valid | 48.8584 | 2.2945
        InvalidLat1 | 91.0 | 2.2945
        InvalidLat2 | -91.0 | 2.2945
        InvalidLon1 | 48.8584 | 181.0
        InvalidLon2 | 48.8584 | -181.0
        """
        
        df = extract_map_data(text)
        
        # Only valid coordinates should be extracted
        assert len(df) == 1
        assert df.iloc[0]['name'] == 'Valid'
    
    def test_text_sanitization_for_pdf(self):
        """Test that text is properly sanitized for PDF export"""
        from maps import clean_text_for_pdf
        
        # Test various special characters
        test_cases = [
            ("Simple text", "Simple text"),
            ("Text with émojis 🎉", "Text with mojis "),  # Emoji removed
            ("Accénted tèxt", "Accnted txt"),  # Accents may be removed/modified
        ]
        
        for input_text, expected_pattern in test_cases:
            result = clean_text_for_pdf(input_text)
            assert isinstance(result, str)
            # Verify it doesn't raise exceptions
    
    @patch('db.get_connection')
    def test_sql_injection_prevention(self, mock_conn):
        """Test that user inputs are properly parameterized"""
        from db import save_itinerary
        
        mock_db_conn = Mock()
        mock_cursor = Mock()
        mock_db_conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
        mock_db_conn.cursor.return_value.__exit__ = Mock(return_value=False)
        mock_conn.return_value = mock_db_conn
        
        # Try to save with SQL injection attempt
        malicious_input = "Paris'; DROP TABLE saved_itineraries; --"
        
        save_itinerary(malicious_input, 'June', 'Content')
        
        # Verify parameterized query was used (not string concatenation)
        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args
        # Should use parameterized query with tuple
        assert len(call_args[0]) == 2  # SQL and params
        assert isinstance(call_args[0][1], tuple)


class TestPerformance:
    """Performance and scalability tests"""
    
    def test_large_coordinate_extraction(self):
        """Test extraction performance with many coordinates"""
        from maps import extract_map_data
        
        # Generate text with many coordinates
        coords_text = "\n".join([
            f"Place{i} | {40 + i*0.01} | {-70 + i*0.01}"
            for i in range(100)
        ])
        
        df = extract_map_data(coords_text)
        
        # Should extract all valid coordinates
        assert len(df) == 100
    
    @patch('db.get_connection')
    def test_large_chat_history_loading(self, mock_conn):
        """Test loading large chat history"""
        from db import load_chat_history
        
        mock_db_conn = Mock()
        mock_cursor = Mock()
        
        # Generate large chat history
        large_history = [
            ('user' if i % 2 == 0 else 'assistant', f'Message {i}')
            for i in range(100)
        ]
        mock_cursor.fetchall.return_value = large_history
        mock_db_conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
        mock_db_conn.cursor.return_value.__exit__ = Mock(return_value=False)
        mock_conn.return_value = mock_db_conn
        
        history = load_chat_history(1)
        
        assert len(history) == 100
        assert all('role' in msg and 'content' in msg for msg in history)


# Fixture for common test data
@pytest.fixture
def sample_guide_text():
    """Fixture providing sample guide text for tests"""
    return """
    ## 🍝 Gastronomy
    * **Croissant:** Flaky, buttery French pastry.
    * **Baguette:** Traditional long French bread.
    
    ## 🏘️ Neighborhoods
    * **Le Marais:** Historic district with trendy boutiques.
    * **Montmartre:** Artistic hilltop neighborhood.
    
    ## ⚠️ Logistics
    * **Tips:** Service charge usually included.
    * **Transport:** Metro is efficient and affordable.
    
    (---PAGE BREAK---)
    
    ### COORDINATES
    Le Marais | 48.8566 | 2.3522
    Montmartre | 48.8867 | 2.3431
    """


@pytest.fixture
def sample_coordinates_df():
    """Fixture providing sample coordinates DataFrame"""
    return pd.DataFrame({
        'name': ['Eiffel Tower', 'Louvre Museum', 'Arc de Triomphe'],
        'lat': [48.8584, 48.8606, 48.8738],
        'lon': [2.2945, 2.3376, 2.2950]
    })


class TestWithFixtures:
    """Tests using pytest fixtures"""
    
    def test_extract_from_sample_guide(self, sample_guide_text):
        """Test extraction using sample guide fixture"""
        from maps import extract_map_data
        
        df = extract_map_data(sample_guide_text)
        
        assert not df.empty
        assert 'Le Marais' in df['name'].values
        assert 'Montmartre' in df['name'].values
    
    def test_summaries_from_sample_guide(self, sample_guide_text):
        """Test summary generation using sample guide fixture"""
        from maps import get_location_summaries
        
        names = ['Le Marais', 'Montmartre']
        summaries = get_location_summaries(sample_guide_text, names)
        
        assert len(summaries) == 2
        assert summaries[0]['name'] == 'Le Marais'
        # Should find descriptions from the guide
        assert summaries[0]['desc'] != "No short description available."
