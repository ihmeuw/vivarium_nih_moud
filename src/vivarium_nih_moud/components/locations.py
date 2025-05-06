from typing import Callable, Dict, List, Optional

import numpy as np
import pandas as pd

from vivarium import Component
from vivarium.framework.engine import Builder
from vivarium.framework.population import SimulantData
from vivarium.framework.values import Pipeline

from vivarium_public_health.disease import DiseaseModel
from vivarium_public_health.disease.state import BaseDiseaseState
from vivarium_public_health.utilities import EntityString

from .conditions import RiskDiseaseModel


class HousingState(BaseDiseaseState):
    def __init__(self, state_id: str, allow_self_transition: bool = True):
        super().__init__(state_id, allow_self_transition)

    def add_rate_transition(self, output_state):
        rate = f"quarters.{self.state_id}_to_{output_state.state_id}.transition_rate"  # key for this transition rate in the artifact
        get_data_functions = {
            "transition_rate": lambda builder, i, o: builder.data.load(rate)
        }
        return super().add_rate_transition(output_state, get_data_functions)


class DiseaseRisk(Component):
    """A component that maps disease states to risk exposure categories.
    
    This component creates a risk-like exposure pipeline where the values
    come from the state of a disease model rather than from propensity scores.
    It allows disease states to be directly used as risk exposure categories.
    
    The mapping from disease states to risk categories is provided at initialization,
    with disease states as values and risk categories as keys.
    """
    
    def __init__(self, cause: str, **state_mapping):
        """
        Parameters
        ----------
        cause : str
            The name of the disease cause that this risk will follow.
        **state_mapping
            Keyword arguments mapping risk categories to disease states.
            For example: cat1='unhoused', cat2='incarcerated', cat3='housed'
        """
        super().__init__()
        self.cause = EntityString(f"cause.{cause}")
        # Use proper EntityString format for risk name
        self.risk = EntityString(f"risk_factor.{cause}_risk")
        self.exposure_pipeline_name = f"{self.risk.name}.exposure"
        
        self.state_mapping = state_mapping
        # Create reverse mapping from disease state to risk category
        self.reverse_mapping = {v: k for k, v in state_mapping.items()}
    
    @property
    def columns_required(self) -> List[str]:
        """Columns required by this component."""
        return [self.cause.name]
    
    def setup(self, builder: Builder) -> None:
        """Set up the component."""
        # Get the disease model component
        self.disease_model = builder.components.get_component(f"disease_model.{self.cause.name}")
        if not isinstance(self.disease_model, DiseaseModel):
            raise ValueError(f"No disease model found for cause {self.cause.name}")
        
        # Check that all mapped states exist in the disease model
        for state_name in self.state_mapping.values():
            if state_name not in [state.state_id for state in self.disease_model.states]:
                raise ValueError(f"State {state_name} not found in disease model {self.cause.name}")
        
        # Register the exposure pipeline
        self.exposure = builder.value.register_value_producer(
            self.exposure_pipeline_name,
            source=self.get_current_exposure,
            component=self,
            requires_columns=[self.cause.name],
        )
    
    def get_current_exposure(self, index: pd.Index) -> pd.Series:
        """Map disease state to risk exposure category."""
        population = self.population_view.get(index)
        
        # Map disease states to risk categories
        exposure = population[self.cause.name].map(self.reverse_mapping)
        
        # Set a proper name for the exposure Series
        exposure.name = self.exposure_pipeline_name
        
        return exposure


def quarters_model():
    cause = "quarters"

    housed = HousingState("housed")
    unhoused = HousingState("unhoused")
    incarcerated = HousingState("incarcerated")

    housed.add_rate_transition(unhoused)
    housed.add_rate_transition(incarcerated)

    unhoused.add_rate_transition(housed)
    unhoused.add_rate_transition(incarcerated)

    incarcerated.add_rate_transition(housed)
    incarcerated.add_rate_transition(unhoused)

    return DiseaseModel(
        cause,
        initial_state=housed,
        states=[housed, unhoused, incarcerated],
    )


def quarters_risk():
    """Create a risk based on the quarters disease model."""
    return DiseaseRisk(
        cause='quarters', 
        cat1='unhoused', 
        cat2='incarcerated', 
        cat3='housed'
    )

class SimpleRiskEffect(Component):
    """A simple risk effect component that applies a multiplicative relative risk."""
    
    def __init__(self, risk_name: str, affected_pipeline_name: str):
        """
        Parameters
        ----------
        risk_name : str
            The name of the risk factor.
        affected_pipeline_name : str
            The name of the pipeline that is affected by the risk.
        """
        super().__init__()
        self.risk = EntityString(f"risk_factor.{risk_name}")
        self.affected_pipeline_name = affected_pipeline_name
        
    def setup(self, builder: Builder) -> None:
        """Set up the component."""
        # Get the risk exposure pipeline
        self.risk_exposure_pipeline = builder.value.get_value(
            self.risk.name + ".exposure"
        )
        self.affected_pipeline = builder.value.get_value(
            self.affected_pipeline_name
        )
        
        # Add modified to the risk effect pipeline
        self.risk_effect = builder.value.register_value_modifier(
            self.affected_pipeline_name,
            modifier=self.apply_risk_effect,
            component=self,
            requires_columns=[self.risk.name],
        )
        #     f"{self.risk.name}.effect",
        #     source=self.apply_risk_effect,
        #     component=self,
        #     # requires_columns=[self.cause.name],
        #     # required_resources=
        # )

    def apply_risk_effect(self, index: pd.Index, pipeline_value) -> pd.Series:
        """Apply the risk effect to the affected pipeline."""
        # Get the risk exposure
        risk_exposure = self.risk_exposure_pipeline(index)
        # breakpoint()
        # Apply the risk effect (multiplicative relative risk)
        pipeline_value[risk_exposure == 'cat1'] *= 0.10
        pipeline_value[risk_exposure == 'cat2'] *= 10
        return pipeline_value