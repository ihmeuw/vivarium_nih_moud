import numpy as np
import pandas as pd


def write_or_replace(art, key, data):
    if key in art.keys:
        # import pdb; pdb.set_trace()
        art.replace(key, data)
    else:
        art.write(key, data)


def generate_constant_data(data_value):
    ages = [20]
    years = [2021]
    sexes = ["Male", "Female"]
    data = []
    for age in ages:
        for year in years:
            for sex in sexes:
                data.append(
                    {
                        "age_start": age,
                        "age_end": age + 5,
                        "year_start": year,
                        "year_end": year + 1,
                        "sex": sex,
                    }
                )
                for i in range(1_000):
                    data[-1][f"draw_{i}"] = np.clip(
                        data_value + np.random.uniform(0, 0.1), 0, 1
                    )
    data = pd.DataFrame(data)
    return data.set_index(["sex", "age_start", "age_end", "year_start", "year_end"])
