import sys
import os
import pandas as pd
import numpy as np
import pytest
from unittest.mock import MagicMock, patch, Mock

# Add the tests directory to sys.path to allow importing visual_validation
sys.path.append(os.path.join(os.path.dirname(__file__)))

import visual_validation

def test_add_age_group():
    """Test that add_age_group correctly adds age groups."""
    # Create a test dataframe
    pop = pd.DataFrame({
        "age": [2, 7, 12, 17, 99, 101]
    })

    # Apply the function
    visual_validation.add_age_group(pop)

    # Check if column was added
    assert "age_group" in pop.columns

    # Check values
    # [0, 5), [5, 10), [10, 15), [15, 20), [95, 100), NaN (101 is out of bins)
    assert pop["age_group"].iloc[0] == pd.Interval(0, 5, closed='left')
    assert pop["age_group"].iloc[1] == pd.Interval(5, 10, closed='left')
    assert str(pop["age_group"].iloc[5]) == "nan"


@patch("pandas.Series.plot")
@patch("matplotlib.pyplot.show")
@patch("matplotlib.pyplot.subplots")
def test_validation_plots_structure(mock_subplots, mock_show, mock_series_plot):
    """
    Test the structure of validation_plots without running the full simulation
    or plotting. We mock the simulation and artifact.
    """
    # Mock figure and axes
    mock_fig = MagicMock()
    mock_ax = MagicMock()

    # subplots returns fig, axes_array
    # The code expects a 5x2 array of axes
    # We make sure it's a numpy array of objects
    axes_array = np.empty((5, 2), dtype=object)
    axes_array.fill(mock_ax)

    mock_subplots.return_value = (mock_fig, axes_array)

    # Mock Simulation
    mock_sim = MagicMock()

    # Create a mock population
    pop_size = 100
    cause = "oud_consistent"

    pop = pd.DataFrame({
        "age": np.random.randint(0, 100, pop_size),
        "sex": np.random.choice(["Male", "Female"], pop_size),
        "tracked": np.ones(pop_size),
        cause: np.random.choice([f"susceptible_to_{cause}", f"infected_with_{cause}"], pop_size),
        "cause_of_death": np.random.choice([cause, "other_cause"], pop_size),
        "susceptible_to_oud_consistent_event_count": np.random.randint(0, 2, pop_size)
    })

    mock_sim.get_population.return_value = pop

    # Mock Artifact
    mock_art = MagicMock()

    # Create mock artifact data
    ages = np.arange(0, 100, 5)
    data = []
    for sex in ["Male", "Female"]:
        for age in ages:
            data.append({
                "sex": sex,
                "age_start": age,
                "age_end": age + 5,
                "value": 0.01
            })

    # df_artifact_simple needs to be structured such that .loc[sex] returns something with age_start/age_end
    df_artifact_simple = pd.DataFrame(data).set_index("sex")

    # Ensure all load calls return this compatible structure
    mock_art.load.return_value = df_artifact_simple

    # Run the function with 1 year
    visual_validation.validation_plots(mock_sim, mock_art, 1)

    # Verify interactions
    mock_sim.run_for.assert_called_once()
    assert mock_sim.get_population.called
    assert mock_art.load.call_count >= 5 # It loads 5 different metrics
    assert mock_subplots.called
    assert mock_show.called

    # Verify that plotting was called
    assert mock_series_plot.called
