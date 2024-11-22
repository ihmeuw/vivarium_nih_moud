"""Modularized functions for building project data artifacts.

This module is an abstraction around the load portion of our artifact building ETL pipeline.
The intent is to be declarative so it's easy to see what is put into the artifact and how.
Some degree of verbosity/boilerplate is fine in the interest of transparency.

.. admonition::

   Logging in this module should be done at the ``debug`` level.

"""
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from loguru import logger
from vivarium.framework.artifact import Artifact, EntityKey

from ..constants import data_keys
from ..data import dismod_at, loader


def open_artifact(output_path: Path, location: str) -> Artifact:
    """Creates or opens an artifact at the output path.

    Parameters
    ----------
    output_path
        Fully resolved path to the artifact file.
    location
        Proper GBD location name represented by the artifact.

    Returns
    -------
        A new artifact.

    """
    if not output_path.exists():
        logger.debug(f"Creating artifact at {str(output_path)}.")
    else:
        logger.debug(f"Opening artifact at {str(output_path)} for appending.")

    artifact = Artifact(output_path)

    key = data_keys.METADATA_LOCATIONS
    if key not in artifact:
        artifact.write(key, [location])

    return artifact


def load_and_write_data(
    artifact: Artifact, key: str, location: str, years: Optional[str], replace: bool
):
    """Loads data and writes it to the artifact if not already present.

    Parameters
    ----------
    artifact
        The artifact to write to.
    key
        The entity key associated with the data to write.
    location
        The location associated with the data to load and the artifact to
        write to.
    replace
        Flag which determines whether to overwrite existing data

    """
    if key in artifact and not replace:
        logger.debug(f"Data for {key} already in artifact.  Skipping...")
    else:
        logger.debug(f"Loading data for {key} for location {location}.")
        # years is either a string we want to convert to an int, 'all', or None
        years = int(years) if years and years != "all" else years
        data = loader.get_data(key, location, years)
        if key not in artifact:
            logger.debug(f"Writing data for {key} to artifact.")
            artifact.write(key, data)
        else:  # key is in artifact, but should be replaced
            logger.debug(f"Replacing data for {key} in artifact.")
            artifact.replace(key, data)
    return artifact.load(key)


def write_data(artifact: Artifact, key: str, data: pd.DataFrame):
    """Writes data to the artifact if not already present.

    Parameters
    ----------
    artifact
        The artifact to write to.
    key
        The entity key associated with the data to write.
    data
        The data to write.

    """
    if key in artifact:
        logger.debug(f"Data for {key} already in artifact.  Skipping...")
    else:
        logger.debug(f"Writing data for {key} to artifact.")
        artifact.write(key, data)
    return artifact.load(key)


# TODO - writing and reading by draw is necessary if you are using
#        LBWSG data. Find the read function in utilities.py
def write_data_by_draw(artifact: Artifact, key: str, data: pd.DataFrame):
    """Writes data to the artifact on a per-draw basis. This is useful
    for large datasets like Low Birthweight Short Gestation (LBWSG).

    Parameters
    ----------
    artifact
        The artifact to write to.
    key
        The entity key associated with the data to write.
    data
        The data to write.

    """
    with pd.HDFStore(artifact.path, complevel=9, mode="a") as store:
        key = EntityKey(key)
        artifact._keys.append(key)
        store.put(f"{key.path}/index", data.index.to_frame(index=False))
        data = data.reset_index(drop=True)
        for c in data.columns:
            store.put(f"{key.path}/{c}", data[c])


def generate_consistent_moud_rates(art: Artifact, location: str, years: Optional[str]):
    """Generates consistent rates for MOUD data.

    Parameters
    ----------
    art
        The artifact to read from and write to.
    location
        The location associated with the data to load and the artifact to
        write to.
    years
        The years to load data for.

    """
    # TODO: check if the consistent rates are already in the artifact, and if so, skip rest of this function

    # copy metadata
    for key in [
        "cause.opioid_use_disorders.restrictions",
        "cause.opioid_use_disorders.disability_weight",
    ]:
        data = art.load(key)
        write_or_replace(art, key.replace("opioid_use_disorders", "oud_consistent"), data)
    assert 0

    ages = np.arange(0, 96, 5)
    years = np.array([2020, 2025])
    sexes = ["Male", "Female"]
    key = {
        "i": "cause.opioid_use_disorders.incidence_rate",
        "p": "cause.opioid_use_disorders.prevalence",
        "f": "cause.opioid_use_disorders.excess_mortality_rate",
        "m_all": "cause.all_causes.cause_specific_mortality_rate",
        "csmr_with": "cause.opioid_use_disorders.cause_specific_mortality_rate",
        "pop": "population.structure",
    }

    def oud_data(sex):
        df_data = pd.concat(
            [
                dismod_at.transform_to_data("p", art.load(key["p"]), sex, ages, [2021]),
                dismod_at.transform_to_data("i", art.load(key["i"]), sex, ages, [2021]),
                dismod_at.transform_to_data("f", art.load(key["f"]), sex, ages, [2021]),
                dismod_at.transform_to_data(
                    "m",
                    art.load(key["m_all"]) - art.load(key["csmr_with"]),
                    sex,
                    ages,
                    [2021],
                ),
            ]
        )
        return df_data

    def get_rates(model_dict, rate_type, year):
        df_out = []
        for model in model_dict.values():
            df_out.append(model.get_rate(rate_type, year))
        df_out = pd.concat(df_out)
        return df_out

    # fit model separately for Male and Female
    m = {}
    for sex in sexes:
        m[sex] = dismod_at.ConsistentModel(sex, ages, years)
        m[sex].fit(oud_data(sex))

    # store consistent rates in artifact
    for rate_type in "ipfr":
        # generate data for k
        df_out = get_rates(m, rate_type, 2020)
        # store generated data in artifact
        if rate_type != "r":
            rate_name = key[rate_type]
        else:
            rate_name = "cause.opioid_use_disorders.remission_rate"
        rate_name = rate_name.replace("opioid_use_disorders", "oud_consistent")
        write_or_replace(art, rate_name, df_out)

    # then do cause specific mortality rate
    df_out = get_rates(m, "p", 2020) * get_rates(m, "f", 2020)
    rate_name = "cause.oud_consistent.cause_specific_mortality_rate"
    write_or_replace(art, rate_name, df_out)


def write_or_replace(art, key, data):
    if key in art.keys:
        art.replace(key, data)
    else:
        art.write(key, data)
