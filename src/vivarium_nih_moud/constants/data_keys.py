from typing import NamedTuple

from vivarium_public_health.utilities import TargetString

#############
# Data Keys #
#############

METADATA_LOCATIONS = "metadata.locations"


class __Population(NamedTuple):
    LOCATION: str = "population.location"
    STRUCTURE: str = "population.structure"
    AGE_BINS: str = "population.age_bins"
    DEMOGRAPHY: str = "population.demographic_dimensions"
    TMRLE: str = "population.theoretical_minimum_risk_life_expectancy"
    ACMR: str = "cause.all_causes.cause_specific_mortality_rate"

    @property
    def name(self):
        return "population"

    @property
    def log_name(self):
        return "population"


POPULATION = __Population()


class __OUD(NamedTuple):
    PREVALENCE: str = "cause.opioid_use_disorders.prevalence"
    INCIDENCE_RATE: str = "cause.opioid_use_disorders.incidence_rate"
    REMISSION_RATE: str = "cause.opioid_use_disorders.remission_rate"
    DISABILITY_WEIGHT: str = "cause.opioid_use_disorders.disability_weight"
    EMR_COMO: str = "cause.opioid_use_disorders.excess_mortality_rate_como"
    EMR_DISMOD: str = "cause.opioid_use_disorders.excess_mortality_rate_dismod"
    CSMR: str = "cause.opioid_use_disorders.cause_specific_mortality_rate"
    RESTRICTIONS: str = "cause.opioid_use_disorders.restrictions"

    @property
    def name(self):
        return "oud"

    @property
    def log_name(self):
        return "oud"


OUD = __OUD()


class __MOUD(NamedTuple):
    PREVALENCE: str = "cause.moud.prevalence"
    INCIDENCE_RATE: str = "cause.moud.incidence_rate"
    REMISSION_RATE: str = "cause.moud.remission_rate"
    DISABILITY_WEIGHT: str = "cause.moud.disability_weight"
    EMR_COMO: str = "cause.moud.excess_mortality_rate_como"
    EMR_DISMOD: str = "cause.moud.excess_mortality_rate_dismod"
    CSMR: str = "cause.moud.cause_specific_mortality_rate"
    RESTRICTIONS: str = "cause.moud.restrictions"

    @property
    def name(self):
        return "moud"

    @property
    def log_name(self):
        return "moud"


MOUD = __MOUD()


class __OUD_CONSISTENT(NamedTuple):
    PREVALENCE: str = "cause.oud_consistent.prevalence"
    INCIDENCE_RATE: str = "cause.oud_consistent.incidence_rate"
    REMISSION_RATE: str = "cause.oud_consistent.remission_rate"
    DISABILITY_WEIGHT: str = "cause.oud_consistent.disability_weight"
    EXCESS_MORTALITY_RATE: str = "cause.oud_consistent.excess_mortality_rate"
    CSMR: str = "cause.oud_consistent.cause_specific_mortality_rate"
    RESTRICTIONS: str = "cause.oud_consistent.restrictions"

    TREATMENT_INITIATION_RATE: str = "cause.oud_consistent.treatment_initiation_rate"
    TREATMENT_SUCCESS_RATE: str = "cause.oud_consistent.treatment_success_rate"
    TREATMENT_FAILURE_RATE: str = "cause.oud_consistent.treatment_failure_rate"
    TREATMENT_RATIO: str = "cause.oud_consistent.treatment_ratio"
    ODE_ERRORS: str = "cause.oud_consistent.ode_errors"

    @property
    def name(self):
        return "oud_consistent"

    @property
    def log_name(self):
        return "oud_consistent"


OUD_CONSISTENT = __OUD_CONSISTENT()


MAKE_ARTIFACT_KEY_GROUPS = [
    POPULATION,
    OUD,
]
