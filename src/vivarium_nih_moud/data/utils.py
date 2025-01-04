import numpy as np, pandas as pd

def generate_constant_data(data_value):
    ages = np.linspace(0, 100, 11, endpoint=True)
    years = [2021]
    sexes = ['Male', 'Female']
    data = []
    for age in ages:
        for year in years:
            for sex in sexes:
                data.append({
                    'age_start': age,
                    'age_end': age+10,
                    'year_start': year,
                    'year_end': year+1,
                    'sex': sex,
                    'value': data_value
                })
    data = pd.DataFrame(data)
    return data.set_index(['sex', 'age_start', 'age_end', 'year_start', 'year_end'])
