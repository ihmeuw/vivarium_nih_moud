from typing import Dict, Callable

import numpy as np
import pandas as pd

from vivarium.framework.engine import Builder
from vivarium_public_health.disease.state import BaseDiseaseState

from .conditions import RiskDiseaseModel

class HousingState(BaseDiseaseState):
    def __init__(self, state_id: str, allow_self_transition: bool = False):
        super().__init__(state_id, allow_self_transition)

    def add_rate_transition(self, output_state, get_data_functions: Dict[str, Callable] = None, **kwargs):
        """Override parent's add_rate_transition to remove disease-specific assumptions"""
        if get_data_functions is None:
            def default_rate_function(builder, input_state, output_state):
                # Create a DataFrame with the required structure
                return pd.DataFrame({
                    'sex': ['Male', 'Female'],
                    'age_start': [0, 0],
                    'age_end': [125, 125],
                    'year_start': [1990, 1990],
                    'year_end': [2100, 2100],
                    'value': [0.0, 0.0],
                })
            
            get_data_functions = {
                'transition_rate': default_rate_function
            }
        return super().add_rate_transition(output_state, get_data_functions, **kwargs)

    def setup(self, builder: Builder) -> None:
        """Simplified setup without disease-specific components"""
        super().setup(builder)
        self.clock = builder.time.clock()

def quarters_model():
    cause = 'quarters'

    housed = HousingState('housed', allow_self_transition=True)
    unhoused = HousingState('unhoused', allow_self_transition=True)
    incarcerated = HousingState('incarcerated', allow_self_transition=True)

    housed.add_rate_transition(unhoused)
    unhoused.add_rate_transition(incarcerated)

    return RiskDiseaseModel(
        cause,
        initial_state=housed,
        states=[housed, unhoused, incarcerated],
    )