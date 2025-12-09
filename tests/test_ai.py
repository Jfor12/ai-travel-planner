"""
Unit tests for the AI module (ai.py)
Tests the core LLM-powered functionality including intel generation and chat responses.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import os
from ai import generate_intel, run_chat_response, run_gen_response, generate_place_summary


class TestGenerateIntel:
    """Test suite for the generate_intel function"""
    
    @patch('ai.ChatGroq')
    @patch('ai.TavilySearchResults')
    def test_generate_intel_success(self, mock_tavily, mock_groq):
        """Test successful intel generation with valid inputs"""
        # Setup mocks
        mock_tavily_instance = Mock()
        mock_tavily_instance.invoke.return_value = [
            {'content': 'Test content 1', 'url': 'http://test1.com'},
            {'content': 'Test content 2', 'url': 'http://test2.com'}
        ]
        mock_tavily.return_value = mock_tavily_instance
        
        mock_llm = Mock()
        mock_chain = Mock()
        mock_chain.stream.return_value = iter(['Test ', 'response ', 'chunk'])
        mock_groq.return_value = mock_llm
        
        # Set environment variables
        with patch.dict(os.environ, {
            'GROQ_API_KEY': 'test-key',
            'TAVILY_API_KEY': 'test-key'
        }):
            result = generate_intel('Paris, France', 'June')
            
            # Verify it returns an iterator
            assert hasattr(result, '__iter__')
            
            # Verify Tavily was called with search query
            mock_tavily_instance.invoke.assert_called_once()
            call_args = mock_tavily_instance.invoke.call_args[0][0]
            assert 'Paris, France' in call_args
            assert 'June' in call_args
    
    def test_generate_intel_missing_api_keys(self):
        """Test that missing API keys raise RuntimeError"""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(RuntimeError, match="Missing API keys"):
                next(generate_intel('Paris, France', 'June'))
    
    @patch('ai.ChatGroq')
    @patch('ai.TavilySearchResults')
    def test_generate_intel_custom_model_params(self, mock_tavily, mock_groq):
        """Test intel generation with custom model and temperature"""
        mock_tavily_instance = Mock()
        mock_tavily_instance.invoke.return_value = []
        mock_tavily.return_value = mock_tavily_instance
        
        mock_llm = Mock()
        mock_chain = Mock()
        mock_chain.stream.return_value = iter(['Test'])
        mock_groq.return_value = mock_llm
        
        with patch.dict(os.environ, {
            'GROQ_API_KEY': 'test-key',
            'TAVILY_API_KEY': 'test-key'
        }):
            result = generate_intel(
                'London, UK', 
                'December',
                model_name='custom-model',
                temperature=0.7
            )
            
            # Verify ChatGroq was called with custom params
            mock_groq.assert_called_once()
            call_kwargs = mock_groq.call_args[1]
            assert call_kwargs['model_name'] == 'custom-model'
            assert call_kwargs['temperature'] == 0.7


class TestRunChatResponse:
    """Test suite for the run_chat_response function"""
    
    @patch('ai.StrOutputParser')
    @patch('ai.ChatPromptTemplate')
    @patch('ai.ChatGroq')
    def test_chat_response_success(self, mock_groq, mock_prompt, mock_parser):
        """Test successful chat response generation"""
        # Setup mocks
        mock_llm = Mock()
        mock_groq.return_value = mock_llm
        
        mock_prompt_instance = Mock()
        mock_prompt.from_template.return_value = mock_prompt_instance
        
        mock_parser_instance = Mock()
        mock_parser.return_value = mock_parser_instance
        
        # Mock the chain
        mock_chain = Mock()
        mock_chain.invoke.return_value = "This is a test response"
        mock_prompt_instance.__or__ = Mock(return_value=Mock(__or__=Mock(return_value=mock_chain)))
        
        with patch.dict(os.environ, {'GROQ_API_KEY': 'test-key'}):
            guide_context = "Paris is the capital of France."
            user_query = "What is the capital?"
            
            result = run_chat_response(guide_context, user_query)
            
            # Verify response is returned
            assert isinstance(result, str)
            mock_groq.assert_called_once()
    
    @patch('ai.ChatGroq')
    def test_chat_response_with_custom_params(self, mock_groq):
        """Test chat response with custom model parameters"""
        mock_llm = Mock()
        mock_groq.return_value = mock_llm
        
        with patch.dict(os.environ, {'GROQ_API_KEY': 'test-key'}):
            with patch('ai.ChatPromptTemplate.from_template'):
                with patch('ai.StrOutputParser'):
                    run_chat_response(
                        "Test guide",
                        "Test query",
                        model_name='custom-chat-model',
                        temperature=0.9
                    )
                    
                    call_kwargs = mock_groq.call_args[1]
                    assert call_kwargs['model_name'] == 'custom-chat-model'
                    assert call_kwargs['temperature'] == 0.9


class TestRunGenResponse:
    """Test suite for the run_gen_response function"""
    
    @patch('ai.StrOutputParser')
    @patch('ai.ChatPromptTemplate')
    @patch('ai.ChatGroq')
    def test_gen_response_success(self, mock_groq, mock_prompt, mock_parser):
        """Test successful generation response"""
        # Setup mocks
        mock_llm = Mock()
        mock_groq.return_value = mock_llm
        
        mock_prompt_instance = Mock()
        mock_prompt.from_template.return_value = mock_prompt_instance
        
        mock_parser_instance = Mock()
        mock_parser.return_value = mock_parser_instance
        
        # Mock the chain
        mock_chain = Mock()
        mock_chain.invoke.return_value = "Generated summary"
        mock_prompt_instance.__or__ = Mock(return_value=Mock(__or__=Mock(return_value=mock_chain)))
        
        with patch.dict(os.environ, {'GROQ_API_KEY': 'test-key'}):
            result = run_gen_response("Guide content", "Summarize this")
            
            assert isinstance(result, str)
            mock_groq.assert_called_once()
    
    def test_gen_response_missing_api_key(self):
        """Test that missing API key returns empty string"""
        with patch.dict(os.environ, {}, clear=True):
            result = run_gen_response("Guide", "Query")
            assert result == ""


class TestGeneratePlaceSummary:
    """Test suite for the generate_place_summary function"""
    
    @patch('ai.run_gen_response')
    def test_place_summary_success(self, mock_gen_response):
        """Test successful place summary generation"""
        mock_gen_response.return_value = "A famous landmark in Paris"
        
        result = generate_place_summary("Paris guide content", "Eiffel Tower")
        
        assert result == "A famous landmark in Paris"
        mock_gen_response.assert_called_once()
    
    @patch('ai.run_gen_response')
    def test_place_summary_too_long(self, mock_gen_response):
        """Test that long summaries are truncated"""
        long_text = " ".join(["word"] * 20)
        mock_gen_response.return_value = long_text
        
        result = generate_place_summary("Guide", "Place")
        
        # Should be truncated to 15 words
        assert len(result.split()) <= 16  # 15 words + "..."
        assert result.endswith("...")
    
    @patch('ai.run_gen_response')
    def test_place_summary_not_found(self, mock_gen_response):
        """Test when place is not mentioned in guide"""
        mock_gen_response.return_value = "not in this specific briefing"
        
        result = generate_place_summary("Guide", "Unknown Place")
        
        assert result == "No short description available."
    
    @patch('ai.run_gen_response')
    def test_place_summary_exception_handling(self, mock_gen_response):
        """Test exception handling returns fallback message"""
        mock_gen_response.side_effect = Exception("API error")
        
        result = generate_place_summary("Guide", "Place")
        
        assert result == "No short description available."
    
    @patch('ai.run_gen_response')
    def test_place_summary_multiline_response(self, mock_gen_response):
        """Test that multiline responses only use first line"""
        mock_gen_response.return_value = "First line description\nSecond line\nThird line"
        
        result = generate_place_summary("Guide", "Place")
        
        assert result == "First line description"
        assert "\n" not in result


# Integration-style tests
class TestAIModuleIntegration:
    """Integration tests for the AI module"""
    
    @patch('ai.StrOutputParser')
    @patch('ai.ChatPromptTemplate')
    @patch('ai.ChatGroq')
    @patch('ai.TavilySearchResults')
    def test_full_intel_generation_flow(self, mock_tavily, mock_groq, mock_prompt, mock_parser):
        """Test the complete flow from search to streaming response"""
        # Setup comprehensive mocks
        mock_tavily_instance = Mock()
        mock_tavily_instance.invoke.return_value = [
            {'content': 'Paris has amazing food culture', 'url': 'http://food.com'},
            {'content': 'Le Marais is a trendy neighborhood', 'url': 'http://neighborhoods.com'},
            {'content': 'June weather is warm and pleasant', 'url': 'http://weather.com'}
        ]
        mock_tavily.return_value = mock_tavily_instance
        
        mock_llm = Mock()
        mock_groq.return_value = mock_llm
        
        mock_prompt_instance = Mock()
        mock_prompt.from_template.return_value = mock_prompt_instance
        
        mock_parser_instance = Mock()
        mock_parser.return_value = mock_parser_instance
        
        # Mock the chain
        response_chunks = [
            '## 🍝 Gastronomy\n',
            '* **Croissant:** Flaky pastry\n',
            '(---PAGE BREAK---)\n',
            '### COORDINATES\n',
            'Le Marais | 48.8566 | 2.3522'
        ]
        mock_chain = Mock()
        mock_chain.stream.return_value = iter(response_chunks)
        mock_prompt_instance.__or__ = Mock(return_value=Mock(__or__=Mock(return_value=mock_chain)))
        
        with patch.dict(os.environ, {
            'GROQ_API_KEY': 'test-key',
            'TAVILY_API_KEY': 'test-key'
        }):
            result = generate_intel('Paris, France', 'June')
            collected = list(result)
            
            # Verify all chunks were returned
            assert len(collected) == len(response_chunks)
            assert collected[0] == '## 🍝 Gastronomy\n'
            
            # Verify search was called
            mock_tavily_instance.invoke.assert_called_once()
