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

    # Keys that will be loaded into the artifact. must have a colon type declaration
    PREVALENCE: TargetString = TargetString("cause.opioid_use_disorders.prevalence")
    INCIDENCE_RATE: TargetString = TargetString("cause.opioid_use_disorders.incidence_rate")
    REMISSION_RATE: TargetString = TargetString("cause.opioid_use_disorders.remission_rate")
    DISABILITY_WEIGHT: TargetString = TargetString(
        "cause.opioid_use_disorders.disability_weight"
    )
    EMR: TargetString = TargetString("cause.opioid_use_disorders.excess_mortality_rate")
    CSMR: TargetString = TargetString(
        "cause.opioid_use_disorders.cause_specific_mortality_rate"
    )
    RESTRICTIONS: TargetString = TargetString("cause.opioid_use_disorders.restrictions")

    # Useful keys not for the artifact - distinguished by not using the colon type declaration
    RAW_DISEASE_PREVALENCE = TargetString("sequela.raw_disease.prevalence")
    RAW_DISEASE_INCIDENCE_RATE = TargetString("sequela.raw_disease.incidence_rate")

    @property
    def name(self):
        return "oud"

    @property
    def log_name(self):
        return "oud"


OUD = __OUD()

MAKE_ARTIFACT_KEY_GROUPS = [
    POPULATION,
    OUD,
]
