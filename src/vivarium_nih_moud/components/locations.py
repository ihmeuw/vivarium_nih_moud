from typing import Dict, Callable

import numpy as np
import pandas as pd

from vivarium.framework.engine import Builder
from vivarium_public_health.disease.state import BaseDiseaseState

from .conditions import RiskDiseaseModel

class HousingState(BaseDiseaseState):
    def __init__(self, state_id: str, allow_self_transition: bool = True):
        super().__init__(state_id, allow_self_transition)

    def add_rate_transition(self, output_state):
        rate = f'quarters.{self.state_id}_to_{output_state.state_id}.transition_rate' # key for this transition rate in the artifact
        get_data_functions={
            'transition_rate': lambda builder, i, o: builder.data.load(rate)
        }
        return super().add_rate_transition(output_state, get_data_functions)

def quarters_model():
    cause = 'quarters'

    housed = HousingState('housed')
    unhoused = HousingState('unhoused')
    incarcerated = HousingState('incarcerated')

    housed.add_rate_transition(unhoused)
    housed.add_rate_transition(incarcerated)

    unhoused.add_rate_transition(housed)
    unhoused.add_rate_transition(incarcerated)

    incarcerated.add_rate_transition(housed)
    incarcerated.add_rate_transition(unhoused)

    return RiskDiseaseModel(
        cause,
        initial_state=housed,
        states=[housed, unhoused, incarcerated],
    )