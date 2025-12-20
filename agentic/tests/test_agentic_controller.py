import pytest
from unittest.mock import patch, MagicMock
from agentic.agentic_controller import AgenticSwarmController

@patch('agentic.agentic_controller.SimulationAPIClient')
@patch('agentic.agentic_controller.genai.GenerativeModel')
def test_agentic_controller_initialization(mock_genai_model, mock_api_client):
    # Mock the API client's health_check to return True
    mock_api_client.return_value.health_check.return_value = True
    
    try:
        controller = AgenticSwarmController()
        assert controller is not None
        assert controller.api_client is not None
        assert controller.model is not None
    except Exception as e:
        pytest.fail(f"AgenticSwarmController initialization failed with an exception: {e}")
