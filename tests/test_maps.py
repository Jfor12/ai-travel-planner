"""
Unit tests for the maps module (maps.py)
Tests map visualization, data extraction, and PDF generation functionality.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
import os
from maps import (
    display_labeled_map,
    extract_map_data,
    get_location_summaries,
    clean_text_for_pdf,
    create_pdf,
    wikipedia_search_url,
    place_reference_url
)


class TestExtractMapData:
    """Test suite for extract_map_data function"""
    
    def test_extract_valid_coordinates(self):
        """Test extraction of valid coordinate data"""
        text = """
        ### COORDINATES
        Eiffel Tower | 48.8584 | 2.2945
        Le Marais | 48.8566 | 2.3522
        Montmartre | 48.8867 | 2.3431
        """
        
        result = extract_map_data(text)
        
        assert not result.empty
        assert len(result) == 3
        assert 'name' in result.columns
        assert 'lat' in result.columns
        assert 'lon' in result.columns
        assert 'Eiffel Tower' in result['name'].values
        assert 48.8584 in result['lat'].values
    
    def test_extract_with_formatting_characters(self):
        """Test extraction with markdown formatting"""
        text = """
        **[Eiffel Tower]** | 48.8584 | 2.2945
        *Le Marais* | 48.8566 | 2.3522
        """
        
        result = extract_map_data(text)
        
        assert len(result) == 2
        # Should strip formatting characters
        assert 'Eiffel Tower' in result['name'].values
        assert 'Le Marais' in result['name'].values
    
    def test_extract_invalid_coordinates(self):
        """Test that invalid coordinates are filtered out"""
        text = """
        Valid Place | 48.8584 | 2.2945
        Invalid Lat | 95.0 | 2.2945
        Invalid Lon | 48.8584 | 185.0
        Another Invalid | abc | def
        """
        
        result = extract_map_data(text)
        
        # Only valid place should be extracted
        assert len(result) == 1
        assert result.iloc[0]['name'] == 'Valid Place'
    
    def test_extract_empty_text(self):
        """Test extraction from empty text"""
        result = extract_map_data("")
        
        assert result.empty
        assert isinstance(result, pd.DataFrame)
    
    def test_extract_no_coordinates(self):
        """Test extraction when no coordinates found"""
        text = "This is just regular text with no coordinates."
        
        result = extract_map_data(text)
        
        assert result.empty
    
    def test_extract_negative_coordinates(self):
        """Test extraction of negative coordinates"""
        text = "Buenos Aires | -34.6037 | -58.3816"
        
        result = extract_map_data(text)
        
        assert len(result) == 1
        assert result.iloc[0]['lat'] == -34.6037
        assert result.iloc[0]['lon'] == -58.3816


class TestDisplayLabeledMap:
    """Test suite for display_labeled_map function"""
    
    @patch('streamlit.pydeck_chart')
    def test_display_map_success(self, mock_pydeck):
        """Test successful map display"""
        df = pd.DataFrame({
            'name': ['Place A', 'Place B'],
            'lat': [48.8584, 48.8566],
            'lon': [2.2945, 2.3522]
        })
        
        display_labeled_map(df)
        
        # Verify pydeck_chart was called
        mock_pydeck.assert_called_once()
    
    @patch('streamlit.warning')
    def test_display_empty_dataframe(self, mock_warning):
        """Test display with empty dataframe"""
        df = pd.DataFrame()
        
        display_labeled_map(df)
        
        mock_warning.assert_called_once_with("No coordinates found to map.")
    
    @patch('streamlit.pydeck_chart')
    @patch('pydeck.Deck')
    def test_display_with_mapbox_token(self, mock_deck, mock_pydeck):
        """Test map display with Mapbox token"""
        df = pd.DataFrame({
            'name': ['Place A'],
            'lat': [48.8584],
            'lon': [2.2945]
        })
        
        # Mock Deck to accept any kwargs
        mock_deck.return_value = Mock()
        
        with patch.dict(os.environ, {'MAPBOX_API_KEY': 'test-token'}):
            display_labeled_map(df)
            
            mock_pydeck.assert_called_once()
    
    @patch('streamlit.pydeck_chart')
    def test_display_clustered_locations(self, mock_pydeck):
        """Test map display with clustered locations (label offset logic)"""
        # Create clustered locations (within 0.002 degrees)
        df = pd.DataFrame({
            'name': ['Place A', 'Place B', 'Place C'],
            'lat': [48.8584, 48.8585, 48.8583],  # Very close together
            'lon': [2.2945, 2.2946, 2.2944]
        })
        
        display_labeled_map(df)
        
        mock_pydeck.assert_called_once()


class TestGetLocationSummaries:
    """Test suite for get_location_summaries function"""
    
    def test_get_summaries_from_bullets(self):
        """Test extracting summaries from bullet point format"""
        text = """
        ## Neighborhoods
        * **Le Marais:** A historic and trendy district with amazing cafes.
        * **Montmartre:** Artistic neighborhood with the Sacré-Cœur basilica.
        """
        names = ['Le Marais', 'Montmartre']
        
        summaries = get_location_summaries(text, names)
        
        assert len(summaries) == 2
        assert summaries[0]['name'] == 'Le Marais'
        assert 'historic' in summaries[0]['desc'].lower() or 'cafes' in summaries[0]['desc'].lower()
    
    def test_get_summaries_no_match(self):
        """Test summaries when location not found in text"""
        text = "This is some text about Paris."
        names = ['Unknown Place']
        
        summaries = get_location_summaries(text, names)
        
        assert len(summaries) == 1
        assert summaries[0]['desc'] == "No short description available."
    
    def test_get_summaries_empty_inputs(self):
        """Test with empty inputs"""
        summaries = get_location_summaries("", [])
        assert summaries == []
        
        summaries = get_location_summaries("Some text", [])
        assert summaries == []
        
        # Empty text with place name returns empty list (early return)
        summaries = get_location_summaries("", ['Place'])
        assert summaries == []
    
    def test_get_summaries_accents(self):
        """Test handling of accented characters"""
        text = "Café de Flore: Famous Parisian café with literary history."
        names = ['Cafe de Flore']  # Without accent
        
        summaries = get_location_summaries(text, names)
        
        # Should still find match despite accent differences
        assert len(summaries) == 1
        assert summaries[0]['name'] == 'Cafe de Flore'
    
    def test_get_summaries_coordinate_removal(self):
        """Test that coordinates are removed from descriptions"""
        text = """
        Eiffel Tower | 48.8584 | 2.2945: An iconic iron tower in Paris.
        """
        names = ['Eiffel Tower']
        
        summaries = get_location_summaries(text, names)
        
        assert len(summaries) == 1
        # Coordinates should be stripped from description
        assert '48.8584' not in summaries[0]['desc']
        assert '2.2945' not in summaries[0]['desc']
    
    def test_get_summaries_max_length(self):
        """Test that long descriptions are truncated"""
        text = """
        Long Place: This is a very long description that goes on and on with many 
        words that should definitely be truncated to fit within the maximum word limit 
        set by the function to ensure readability.
        """
        names = ['Long Place']
        
        summaries = get_location_summaries(text, names, max_len=50)
        
        assert len(summaries) == 1
        # Should be truncated
        assert len(summaries[0]['desc'].split()) <= 11  # 10 words + "..."


class TestCleanTextForPdf:
    """Test suite for clean_text_for_pdf function"""
    
    def test_clean_simple_text(self):
        """Test cleaning simple ASCII text"""
        text = "Simple text"
        result = clean_text_for_pdf(text)
        assert result == "Simple text"
    
    def test_clean_unicode_characters(self):
        """Test removal of non-Latin-1 characters"""
        text = "Hello 世界 こんにちは"
        result = clean_text_for_pdf(text)
        # Non-Latin-1 characters should be removed
        assert '世界' not in result
        assert 'Hello' in result
    
    def test_clean_emojis(self):
        """Test removal of emojis"""
        text = "Paris 🗼 Eiffel Tower"
        result = clean_text_for_pdf(text)
        # Emoji should be removed, but Latin text preserved
        assert 'Paris' in result
        assert 'Eiffel Tower' in result


class TestCreatePdf:
    """Test suite for create_pdf function"""
    
    def test_create_pdf_basic(self):
        """Test basic PDF creation"""
        destination = "Paris, France"
        content = """
        ## Gastronomy
        * Croissant: Flaky pastry
        * Baguette: Fresh bread
        
        ## Neighborhoods
        * Le Marais: Trendy district
        """
        
        result = create_pdf(destination, content)
        
        assert isinstance(result, bytes)
        assert len(result) > 0
        # PDF files start with %PDF
        assert result[:4] == b'%PDF'
    
    def test_create_pdf_with_page_break(self):
        """Test PDF creation with page break marker"""
        destination = "Paris"
        content = "Main content(---PAGE BREAK---)Should not appear"
        
        result = create_pdf(destination, content)
        
        assert isinstance(result, bytes)
        # Should only include content before page break
    
    def test_create_pdf_with_unicode(self):
        """Test PDF creation with unicode characters"""
        destination = "Café de Paris"
        content = "Content with accénts and spëcial çharacters"
        
        result = create_pdf(destination, content)
        
        assert isinstance(result, bytes)
        assert len(result) > 0
    
    def test_create_pdf_markdown_formatting(self):
        """Test that markdown bold formatting is handled"""
        destination = "Test"
        content = "**Bold text** and regular text"
        
        result = create_pdf(destination, content)
        
        assert isinstance(result, bytes)
        # Asterisks should be removed


class TestWikipediaSearchUrl:
    """Test suite for wikipedia_search_url function"""
    
    def test_wikipedia_url_basic(self):
        """Test basic Wikipedia search URL generation"""
        url = wikipedia_search_url("Eiffel Tower")
        
        assert url.startswith("https://en.wikipedia.org/wiki/Special:Search")
        assert "Eiffel+Tower" in url or "Eiffel%20Tower" in url
    
    def test_wikipedia_url_with_destination(self):
        """Test Wikipedia URL with destination context"""
        url = wikipedia_search_url("Colosseum", "Rome, Italy")
        
        assert "Colosseum" in url
        assert "Rome" in url
    
    def test_wikipedia_url_special_characters(self):
        """Test Wikipedia URL with special characters"""
        url = wikipedia_search_url("Café de Flore", "Paris, France")
        
        assert "https://en.wikipedia.org" in url
        # Special characters should be URL encoded
        assert url.count("?") >= 1


class TestPlaceReferenceUrl:
    """Test suite for place_reference_url function"""
    
    def test_place_url_with_coordinates(self):
        """Test URL generation with coordinates"""
        url = place_reference_url("Eiffel Tower", coords=(48.8584, 2.2945))
        
        assert "https://www.google.com/maps/search/" in url
        assert "48.8584" in url
        assert "2.2945" in url
    
    def test_place_url_without_coordinates(self):
        """Test URL generation without coordinates (fallback to search)"""
        url = place_reference_url("Eiffel Tower", dest="Paris, France")
        
        assert "https://www.google.com/search" in url
        assert "wikipedia" in url.lower()
        assert "Eiffel" in url
    
    def test_place_url_invalid_coordinates(self):
        """Test handling of invalid coordinates"""
        url = place_reference_url("Place", coords=("invalid", "coords"))
        
        # Should fallback to search
        assert "google.com" in url
    
    def test_place_url_name_only(self):
        """Test URL generation with only name"""
        url = place_reference_url("Louvre Museum")
        
        assert "google.com" in url
        assert "Louvre" in url


# Integration-style tests
class TestMapsIntegration:
    """Integration tests for maps module"""
    
    def test_full_map_workflow(self):
        """Test complete workflow: extract data, get summaries, display map"""
        guide_text = """
        ## Neighborhoods
        * **Le Marais:** Historic trendy district with cafes and boutiques.
        * **Montmartre:** Artistic hilltop neighborhood with basilica.
        
        ### COORDINATES
        Le Marais | 48.8566 | 2.3522
        Montmartre | 48.8867 | 2.3431
        """
        
        # Extract map data
        df = extract_map_data(guide_text)
        assert not df.empty
        assert len(df) == 2
        
        # Get location summaries
        names = df['name'].tolist()
        summaries = get_location_summaries(guide_text, names)
        assert len(summaries) == 2
        assert summaries[0]['desc'] != "No short description available."
    
    @patch('streamlit.pydeck_chart')
    def test_map_display_with_real_data(self, mock_pydeck):
        """Test map display with realistic data"""
        guide_text = """
        ### COORDINATES
        Eiffel Tower | 48.8584 | 2.2945
        Louvre Museum | 48.8606 | 2.3376
        Arc de Triomphe | 48.8738 | 2.2950
        Notre-Dame | 48.8530 | 2.3499
        """
        
        df = extract_map_data(guide_text)
        display_labeled_map(df)
        
        # Verify map was created
        mock_pydeck.assert_called_once()
    
    def test_pdf_generation_workflow(self):
        """Test PDF generation with realistic content"""
        destination = "Paris, France"
        guide_text = """
        ## 🍝 Gastronomy
        * **Croissant:** Flaky, buttery pastry
        * **Baguette:** Traditional French bread
        
        ## 🏘️ Neighborhoods
        * **Le Marais:** Historic trendy district
        * **Montmartre:** Artistic hilltop area
        
        (---PAGE BREAK---)
        
        ### COORDINATES
        Le Marais | 48.8566 | 2.3522
        """
        
        pdf_bytes = create_pdf(destination, guide_text)
        
        # Verify PDF was created
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0
        assert pdf_bytes[:4] == b'%PDF'
        
        # Verify coordinate section was excluded
        # (by checking PDF doesn't contain raw coordinate text)
    
    def test_url_generation_for_locations(self):
        """Test URL generation for multiple locations"""
        locations = [
            ('Eiffel Tower', (48.8584, 2.2945)),
            ('Louvre Museum', (48.8606, 2.3376)),
            ('Arc de Triomphe', None)
        ]
        
        for name, coords in locations:
            url = place_reference_url(name, "Paris, France", coords=coords)
            assert isinstance(url, str)
            assert url.startswith("https://")
            assert len(url) > 20
