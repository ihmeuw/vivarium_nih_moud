# visual_test.py
import numpy as np, matplotlib.pyplot as plt, pandas as pd
import vivarium as vi

def add_age_group(pop):
    """
    Add an age group column to the population DataFrame.
    
    Parameters:
    pop (pandas.DataFrame): The population DataFrame.
    """
    pop['age_group'] = pd.cut(pop['age'], bins=np.arange(0,101,5), right=False)

def validation_plots(sim, art):
    """
    Create validation plots for incidence, prevalence, and cause-specific mortality rate (CSMR) over time.
    Plots males and females separately, with rows for each metric (incidence, prevalence, and CSMR).
    Adds artifact values to each plot for comparison.
    
    Parameters:
    sim (vivarium.framework.interactive_context.InteractiveContext): The simulation context.
    art (vivarium.framework.artifact.Artifact): The artifact object.
    """
    cause = 'oud_consistent'
    key_pt = f'person_time_{cause}'
    key_transition = f'transition_count_{cause}'

    years = 12*7/365
    # import pdb; pdb.set_trace()
    sim.run_for(pd.Timedelta(days=years*365))

    pop = sim.get_population()
    add_age_group(pop)

    df_pt = pop.groupby(['age_group', 'sex']).tracked.count() * years
    df_susceptible_pt = pop[pop[cause] == f'susceptible_to_{cause}'].groupby(['age_group', 'sex']).tracked.count() * years
    df_prevalent_cases = pop[pop[cause] != f'susceptible_to_{cause}'].groupby(['age_group', 'sex']).tracked.count()
    df_with_condition_pt = df_prevalent_cases * years
    df_deaths = pop[pop.cause_of_death == cause].groupby(['age_group', 'sex']).tracked.count() * years
    df_incident_cases = pop.groupby(['age_group', 'sex']).susceptible_to_oud_consistent_event_count.sum()
    df_remission_cases = pop.groupby(['age_group', 'sex']).susceptible_to_oud_consistent_event_count.sum()*0

    # Compute CSMR, Prevalence, and Incidence
    df_csmr = 100_000 * df_deaths / df_pt
    df_prevalence = 100_000 * df_prevalent_cases / df_pt
    df_incidence = 100_000 * df_incident_cases / df_susceptible_pt
    df_remission = 100_000 * df_remission_cases / df_with_condition_pt
    df_excess_mortality = 100_000 * df_deaths / df_with_condition_pt


    # Load artifact data
    df_art_csmr = art.load(f'cause.{cause}.cause_specific_mortality_rate')
    df_art_prevalence = art.load(f'cause.{cause}.prevalence')
    df_art_incidence = art.load(f'cause.{cause}.incidence_rate')
    df_art_remission = art.load(f'cause.{cause}.remission_rate')
    df_art_excess_mortality = art.load(f'cause.{cause}.excess_mortality_rate')

    # Set up the plotting grid: two columns (Males, Females), three rows (CSMR, Prevalence, Incidence)
    fig, axes = plt.subplots(5, 2, figsize=(14, 9), sharex=True)
    fig.suptitle(f'Validation Plots for {cause.capitalize()}', fontsize=16)
    metrics = [('Cause Specific Mortality Rate', df_csmr, df_art_csmr),
               ('Excess Mortality', df_excess_mortality, df_art_excess_mortality),
               ('Prevalence', df_prevalence, df_art_prevalence),
               ('Incidence', df_incidence, df_art_incidence),
               ('Remission', df_remission, df_art_remission),
              ]
    sexes = ['Male', 'Female']
    years = [2021]

    def age_x(age_group):
        return (age_group.left+age_group.right)/2

    for row, (metric_name, data, artifact_data) in enumerate(metrics):
        for col, sex in enumerate(sexes):
            ax = axes[row, col]
            for year in years:
                data_to_plot = data.unstack()
                data_to_plot.index = data_to_plot.index.map(age_x).astype(float)
                data_to_plot = data_to_plot.sort_index()
                t1 = data_to_plot
                t1[sex].plot(ax=ax, label=f'{year}', marker='o', linestyle='none')
            
            # Plot artifact data
            artifact_to_plot = artifact_data.loc[sex]*100_000
            artifact_to_plot.index = artifact_to_plot.eval('.5*(age_start+age_end)').astype(float)
            artifact_to_plot = artifact_to_plot.sort_index()
            artifact_mean = artifact_to_plot.mean(axis=1)
            artifact_mean.plot(ax=ax, label=f'Artifact {sex}', color=f'k', linestyle='-', alpha=.75)

            ax.set_title(f'{metric_name} ({sex})')
            ax.set_ylabel(f'{metric_name} (Per 100,000 PY)')
            ax.grid(True)
#             ax.set_yscale('log')
            ax.legend(loc='upper left')

    plt.xlabel('Age Group')
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    plt.show()

path = 'src/vivarium_nih_moud/model_specifications/model_spec.yaml'
sim = vi.InteractiveContext(path)

pop = sim.get_population()

artifact_path = sim.configuration.input_data.artifact_path
art = vi.Artifact(artifact_path)

validation_plots(sim, art)