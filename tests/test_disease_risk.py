import pytest
import pandas as pd
from unittest.mock import MagicMock

from vivarium_nih_moud.components.locations import DiseaseRisk, quarters_model

class MockBuilder:
    """Mock Builder class for testing."""
    
    def __init__(self, components=None):
        self.components = MockComponentManager(components)
        self.value = MockValueSystem()
        self.population = MockPopulationInterface()
        
class MockComponentManager:
    """Mock Component Manager for testing."""
    
    def __init__(self, components=None):
        self.components = components or {}
    
    def get_component(self, name):
        """Get a component by name."""
        return self.components.get(name)

class MockValueSystem:
    """Mock Value System for testing."""
    
    def register_value_producer(self, name, source, component, requires_columns=None):
        """Mock register_value_producer."""
        return source

class MockPopulationInterface:
    """Mock Population Interface for testing."""
    
    def get_view(self, columns, query_string=None):
        """Return a mock population view."""
        view = MagicMock()
        return view

def test_disease_risk_mapping():
    """Test that DiseaseRisk correctly maps disease states to risk categories."""
    # Setup test fixtures
    pop_size = 10
    
    # Create a test population with specified disease states
    pop = pd.DataFrame({
        'quarters': ['housed', 'unhoused', 'incarcerated', 'housed', 'unhoused',
                    'incarcerated', 'housed', 'unhoused', 'incarcerated', 'housed'],
        'tracked': pd.Series('tracked', index=range(pop_size)),
        'alive': pd.Series('alive', index=range(pop_size))
    }, index=range(pop_size))
    
    # Create the DiseaseRisk component
    disease_risk = DiseaseRisk(
        cause='quarters',
        cat1='unhoused',
        cat2='incarcerated',
        cat3='housed'
    )
    
    # Mock the disease model for the test
    disease_model = quarters_model()
    
    # Create a mock builder
    mock_components = {'disease_model.quarters': disease_model}
    builder = MockBuilder(mock_components)
    
    # Setup the disease risk component - don't actually call setup
    # Just set the required attributes directly
    disease_risk.disease_model = disease_model
    
    # Create a mock population view that returns our test data
    mock_view = MagicMock()
    mock_view.get = MagicMock(return_value=pop)
    disease_risk._population_view = mock_view
    
    # Test get_current_exposure directly
    exposure = disease_risk.get_current_exposure(pop.index)
    
    # Verify the mapping is correct
    expected = pd.Series(['cat3', 'cat1', 'cat2', 'cat3', 'cat1', 'cat2', 'cat3', 'cat1', 'cat2', 'cat3'], 
                         index=range(pop_size),
                         name='quarters_risk.exposure')
    pd.testing.assert_series_equal(exposure, expected)
import pandas as pd
import pytest
from unittest.mock import MagicMock, patch

from vivarium.interface.interactive import InteractiveContext
from vivarium.testing_utilities import TestPopulation, build_table



class MockDiseaseModel:
    """Mock disease model for testing"""
    def __init__(self, cause, states):
        self.cause = cause
        self.cause_type = "cause"
        self.states = states


class MockDiseaseState:
    """Mock disease state for testing"""
    def __init__(self, state_id):
        self.state_id = state_id


def mock_quarters_model():
    """Mock version of quarters_model that doesn't require an artifact"""
    cause = "quarters"
    housed = MockDiseaseState("housed")
    unhoused = MockDiseaseState("unhoused")
    incarcerated = MockDiseaseState("incarcerated")
    
    return MockDiseaseModel(
        cause=cause,
        states=[housed, unhoused, incarcerated],
    )


def test_disease_risk_without_artifact():
    """Test DiseaseRisk without requiring an artifact"""
    
    # Mock the component registry to return our mock disease model
    def mock_get_component(name):
        if name == "disease_model.quarters":
            return mock_quarters_model()
        return None
    
    # Create the DiseaseRisk component
    disease_risk = DiseaseRisk(
        cause='quarters',
        cat1='unhoused',
        cat2='incarcerated',
        cat3='housed'
    )
    
    # Manually set up the component
    disease_risk.disease_model = mock_quarters_model()
    
    # Create a fake population
    pop_size = 10
    pop = pd.DataFrame({
        'quarters': ['housed', 'unhoused', 'incarcerated', 'housed', 'unhoused',
                    'incarcerated', 'housed', 'unhoused', 'incarcerated', 'housed'],
    }, index=range(pop_size))
    
    # Create a mock population view
    mock_view = MagicMock()
    mock_view.get = MagicMock(return_value=pop)
    disease_risk._population_view = mock_view
    
    # Test the exposure mapping
    exposure = disease_risk.get_current_exposure(pop.index)
    
    # Create expected result
    mapping = {'unhoused': 'cat1', 'incarcerated': 'cat2', 'housed': 'cat3'}
    expected = pop['quarters'].map(mapping)
    expected.name = disease_risk.exposure_pipeline_name  # Set correct name
    
    # Verify the mapping is correct
    pd.testing.assert_series_equal(exposure, expected)
    
    # Test that exposure updates when disease state changes
    # Change some disease states
    pop.loc[0, 'quarters'] = 'unhoused'  # Change from housed to unhoused
    pop.loc[1, 'quarters'] = 'housed'    # Change from unhoused to housed
    
    # Get updated exposure
    updated_exposure = disease_risk.get_current_exposure(pop.index)
    
    # Update expected result
    updated_expected = pop['quarters'].map(mapping)
    updated_expected.name = disease_risk.exposure_pipeline_name
    
    # Verify the mapping is updated correctly
    pd.testing.assert_series_equal(updated_exposure, updated_expected)
    
    print("DiseaseRisk test without artifact passed successfully!")
