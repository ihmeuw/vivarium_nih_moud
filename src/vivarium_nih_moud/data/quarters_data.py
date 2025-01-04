import numpy as np, pandas as pd

import utils

def generate_quarters_data(art, location: str, years):
    # copy metadata
    for key in [
        "cause.opioid_use_disorders.restrictions",
        "cause.opioid_use_disorders.disability_weight",
    ]:
        data = art.load(key)
        utils.write_or_replace(art, key.replace("opioid_use_disorders", "quarters"), data)

    # add stand-in data for rates
    data = utils.generate_constant_data(0.0)
    key = 'cause.quarters.cause_specific_mortality_rate'
    utils.write_or_replace(art, key, data)



if __name__ == "__main__":
    from vivarium import Artifact

    location = "Washington"
    years = [2021]
    art = Artifact("washington.hdf")
    generate_quarters_data(art, location, years)
