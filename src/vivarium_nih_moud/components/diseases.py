import numpy as np
import pandas as pd
from vivarium_public_health.disease import (
    DiseaseModel,
    DiseaseState,
    RateTransition,
    SusceptibleState,
)
from vivarium_public_health.risks.data_transformations import (
    get_exposure_post_processor,
)
from vivarium_public_health.utilities import EntityString


class RiskDiseaseModel(DiseaseModel):
    def setup(self, builder):
        super(DiseaseModel, self).setup(builder)

        self.state_to_risk_category_map = builder.configuration[
            self.state_column
        ].state_to_risk_category_map.to_dict()  # FIXME: is to_dict right?  why is it needed?

        # FIXME: I'm not sure why the next three lines are needed; I copy-pasted them from the LTBI class BetterDiseaseModel
        self.configuration_age_start = builder.configuration.population.initialization_age_min
        self.configuration_age_end = builder.configuration.population.initialization_age_max
        self.randomness = builder.randomness.get_stream(f"{self.state_column}_initial_states")

        # create a pipeline for a risk exposure based on disease model state
        self.exposure = builder.value.register_value_producer(
            f"{self.state_column}.exposure",
            source=self.get_current_exposure,
            requires_columns=[self.state_column],
            preferred_post_processor=get_exposure_post_processor(
                builder, EntityString(f"risk_factor.{self.state_column}")
            ),
        )

    def get_current_exposure(self, index: pd.Index) -> pd.Series:
        pop = self.population_view.get(index)
        exposure = pop[self.state_column].map(self.state_to_risk_category_map)

        return exposure


def moud_model():
    """
    Goal: Create an MOUD disease model to match this D2 diagram,
    where with_condition can be used as a risk exposure
    https://play.d2lang.com/?script=dM5BCgIxDIXhfU-RC3iBLrxKqW3EBzPJ0KS4EO8uIjgdndll8X_h6QJFTd04VZi2ys0iPQKRdSu8OC4TB6I7_JaKSoVDJRCpJG-cfWbxsM3pdP7pI0EKKkvh1LL_P3yT4UOkxjPMoHLcjwsifc8EgSP7YMdyb9xqrxlTb3wENxNXZb0UNvuoZ3gFAAD__w%3D%3D&

        opioid_use_disorders: {
          susceptible
          with_condition
          on_treatment

          susceptible -> with_condition: incidence_rate
          with_condition -> susceptible: remission_rate
          with_condition -> on_treatment: treatment_initiation_rate
          on_treatment -> with_condition: treatment_failure_rate
          on_treatment -> susceptible: treatment_success_rate
        }

    """
    cause = "opioid_use_disorders"

    # start with SIS version of minimal OUD model
    susceptible = SusceptibleState(cause, allow_self_transition=True)
    with_condition = DiseaseState("with_condition", allow_self_transition=True)
    with_condition.has_excess_mortality = True

    susceptible.add_rate_transition(with_condition)
    with_condition.add_rate_transition(susceptible)

    # add treatment compartment and transitions to and from it
    on_treatment = DiseaseState("on_treatment", allow_self_transition=True)
    on_treatment.has_excess_mortality = False  # TODO: figure out if this is really necessary
    with_condition.add_rate_transition(
        on_treatment,
        get_data_functions={
            "transition_rate": lambda builder, state_1, state_2,: builder.data.load(
                f"cause.opioid_use_disorders.treatment_initiation_rate"
            )
        },
    )
    on_treatment.add_rate_transition(
        with_condition,
        get_data_functions={
            "transition_rate": lambda builder, state_1, state_2,: builder.data.load(
                f"cause.opioid_use_disorders.treatment_failure_rate"
            )
        },
    )
    on_treatment.add_rate_transition(
        susceptible,
        get_data_functions={
            "transition_rate": lambda builder, state_1, state_2,: builder.data.load(
                f"cause.opioid_use_disorders.treatment_success_rate"
            )
        },
    )

    return RiskDiseaseModel(
        cause, initial_state=susceptible, states=[susceptible, with_condition, on_treatment]
    )
