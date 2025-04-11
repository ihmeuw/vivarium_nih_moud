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
                         name='quarters')
    pd.testing.assert_series_equal(exposure, expected)

import pandas as pd
import pytest
from vivarium.interface.interactive import InteractiveContext
from vivarium.testing_utilities import TestPopulation

from vivarium_public_health.risks import RiskEffect
from vivarium_nih_moud.components.locations import DiseaseRisk, quarters_model


def test_disease_risk_functional():
    """Functional test for DiseaseRisk within a Vivarium simulation."""
    # Initialize a simple simulation with the components
    sim = InteractiveContext(
        components=[
            TestPopulation(),
            quarters_model(),
            DiseaseRisk(
                cause='quarters',
                cat1='unhoused',
                cat2='incarcerated',
                cat3='housed'
            ),
            # Add a risk effect component to test the integration - use proper format
            RiskEffect('risk_factor.quarters_risk', 'cause.test_disease.incidence_rate')
        ],
        configuration={
            # Configuration for the test population
            'population': {
                'population_size': 100  # Smaller for faster tests
            },
            # Configuration for the risk effect
            'risk_effect.quarters_risk_on_cause.test_disease.incidence_rate': {
                'data_sources': {
                    'relative_risk': 1.0,  # Simple placeholder for test
                    'population_attributable_fraction': 0.0
                },
                # Add needed configuration to avoid data loading errors
                'data_source_parameters': {
                    'relative_risk': {},
                }
            }
        }
    )
    
    # Get initial population
    pop = sim.get_population()
    
    # Force set known disease states to ensure predictable test conditions
    # Distribute states evenly across the population
    pop_size = len(pop)
    housed_count = pop_size // 3
    unhoused_count = pop_size // 3
    incarcerated_count = pop_size - housed_count - unhoused_count
    
    disease_states = ['housed'] * housed_count + ['unhoused'] * unhoused_count + ['incarcerated'] * incarcerated_count
    pop['quarters'] = disease_states
    
    # Update the population with our assigned disease states
    quarters_view = sim.population.get_view(['quarters'])
    quarters_view.update(pop[['quarters']])
    
    # Get the risk exposure from the exposure pipeline
    exposure = sim.get_value('quarters_risk.exposure')(pop.index)
    
    # Verify mapping is working
    mapping = {'unhoused': 'cat1', 'incarcerated': 'cat2', 'housed': 'cat3'}
    expected = pop['quarters'].map(mapping)
    
    # Test that the exposure mapping is correct
    pd.testing.assert_series_equal(exposure, expected, check_names=False)
    
    # Verify all values are valid
    assert not exposure.isna().any(), "Some exposure values are NA"
    
    # Test a simpler case with just the mapping functionality
    # instead of running simulation steps, which might require more configuration
    
    # Take samples to change housing states
    sample_size = min(5, pop_size // 10)
    
    # Get indices for each housing state
    housed_idx = pop[pop['quarters'] == 'housed'].index[:sample_size]
    unhoused_idx = pop[pop['quarters'] == 'unhoused'].index[:sample_size]
    incarcerated_idx = pop[pop['quarters'] == 'incarcerated'].index[:sample_size]
    
    # Change housing states in a cycle: housed→unhoused→incarcerated→housed
    pop.loc[housed_idx, 'quarters'] = 'unhoused'
    pop.loc[unhoused_idx, 'quarters'] = 'incarcerated'
    pop.loc[incarcerated_idx, 'quarters'] = 'housed'
    
    # Update the population
    quarters_view.update(pop[['quarters']])
    
    # Get updated exposure
    updated_exposure = sim.get_value('quarters_risk.exposure')(pop.index)
    
    # Calculate expected updated mapping
    updated_expected = pop['quarters'].map(mapping)
    
    # Check specifically for the individuals whose states were changed
    changed_idx = pd.Index(list(housed_idx) + list(unhoused_idx) + list(incarcerated_idx))
    pd.testing.assert_series_equal(
        updated_exposure.loc[changed_idx], 
        updated_expected.loc[changed_idx],
        check_names=False
    )
    
    print("DiseaseRisk functional test passed successfully!")