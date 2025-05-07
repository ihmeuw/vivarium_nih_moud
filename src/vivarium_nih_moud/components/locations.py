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
    """A simple risk effect component that applies a multiplicative relative risk for categorical exposures."""
    
    CONFIGURATION_DEFAULTS = {
        "effect_of_risk_on_target": {
            "relative_risk": {
                "cat1": 2.0,
                "cat2": 1.0,
            }
        }
    }

    @property
    def configuration_defaults(self) -> Dict[str, Dict]:
        """Return configuration defaults for this component."""
        return {self.config_name: self.CONFIGURATION_DEFAULTS["effect_of_risk_on_target"]}

    @property
    def columns_required(self):
        """Declare columns required by this component."""
        # This ensures we tell Vivarium we need the risk exposure column
        return ["quarters", f"{self.risk.name}_exposure"]  

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

        self.config_name = f"effect_of_{self.risk.name}_on_{self.affected_pipeline_name}".replace('.transition_rate', '')

        self.paf_calculated = False
        self.paf_value = 0.0
        
    def setup(self, builder: Builder) -> None:
        """Set up the component."""
        # Get configuration values for relative risk
        self.relative_risk_mapping = builder.configuration[self.config_name]["relative_risk"].to_dict()

        # Get the risk exposure pipeline
        self.risk_exposure_pipeline = builder.value.get_value(
            f"{self.risk.name}.exposure"
        )

        # Add modifier to the risk effect pipeline
        builder.value.register_value_modifier(
            self.affected_pipeline_name,
            modifier=self.apply_risk_effect,
            requires_values=[f"{self.risk.name}.exposure"]
        )

    def calculate_paf(self, s_relative_risk: pd.Series) -> None:
        """
        Calculate the population attributable fraction (PAF) at the start of the simulation.
        
        PAF = 1-1/E[RR]
        """
        # breakpoint()
        assert not s_relative_risk.isnull().any(), f"Relative risk series contains NaN values, check config {self.config_name}.relative_risk for missing categories."
        if s_relative_risk.std() == 0:
            return # not yet initialized
        # FIXME: this does not run for long enough to get to steady state
        expected_rr = s_relative_risk.mean()
        self.paf_value = 1 - 1 / expected_rr
        
        print(f"Calculated PAF for {self.risk.name} effect on {self.affected_pipeline_name}: {self.paf_value}")
        self.paf_calculated = True


    def apply_risk_effect(self, index: pd.Index, s_pipeline_value: pd.Series) -> pd.Series:
        """Apply the risk effect to the affected pipeline."""
        s_relative_risk = self.get_relative_risk(index)
        # also find the PAF, so that the rate stays calibrated at the population level
        if not self.paf_calculated:
            self.calculate_paf(s_relative_risk)
    
        s_paf = pd.Series(self.paf_value, index=index)

        # apply the relative risk to the affected pipeline
        s_pipeline_value *= (1-s_paf) * s_relative_risk
        return s_pipeline_value
    
    def get_relative_risk(self, index: pd.Index) -> pd.Series:
        # start with a pd.Series of the risk exposure levels
        s_risk_exposure = self.risk_exposure_pipeline(index)
        
        # use this to find a pd.Series of relative risk multipliers
        s_relative_risk = s_risk_exposure.map(self.relative_risk_mapping)
        return s_relative_risk
