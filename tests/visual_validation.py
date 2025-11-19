# visual_validation.py
import argparse
import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import vivarium as vi


def add_age_group(pop):
    """
    Add an age group column to the population DataFrame.

    Parameters:
    pop (pandas.DataFrame): The population DataFrame.
    """
    pop["age_group"] = pd.cut(pop["age"], bins=np.arange(0, 101, 5), right=False)


def validation_plots(sim, art, years_to_run, output_file=None):
    """
    Create validation plots for incidence, prevalence, and cause-specific mortality rate (CSMR) over time.
    Plots males and females separately, with rows for each metric (incidence, prevalence, and CSMR).
    Adds artifact values to each plot for comparison.

    Parameters:
    sim (vivarium.framework.interactive_context.InteractiveContext): The simulation context.
    art (vivarium.framework.artifact.Artifact): The artifact object.
    years_to_run (float): The number of years to run the simulation.
    output_file (str, optional): If provided, save the plot to this file instead of showing it.
    """
    cause = "oud_consistent"

    # Run the simulation
    sim.run_for(pd.Timedelta(days=years_to_run * 365))

    pop = sim.get_population()
    add_age_group(pop)

    df_pt = pop.groupby(["age_group", "sex"]).tracked.count() * years_to_run

    df_susceptible_pt = (
        pop[pop[cause] == f"susceptible_to_{cause}"]
        .groupby(["age_group", "sex"])
        .tracked.count()
        * years_to_run
    )

    df_prevalent_cases = (
        pop[pop[cause] != f"susceptible_to_{cause}"]
        .groupby(["age_group", "sex"])
        .tracked.count()
    )

    df_with_condition_pt = df_prevalent_cases * years_to_run

    df_deaths = (
        pop[pop.cause_of_death == cause].groupby(["age_group", "sex"]).tracked.count()
        * years_to_run
    )

    df_incident_cases = pop.groupby(
        ["age_group", "sex"]
    ).susceptible_to_oud_consistent_event_count.sum()

    df_remission_cases = (
        pop.groupby(["age_group", "sex"]).susceptible_to_oud_consistent_event_count.sum() * 0
    )

    # Compute CSMR, Prevalence, and Incidence
    # Handle division by zero or missing data
    df_csmr = (100_000 * df_deaths / df_pt).fillna(0)
    df_prevalence = (100_000 * df_prevalent_cases / df_pt).fillna(0)
    df_incidence = (100_000 * df_incident_cases / df_susceptible_pt).fillna(0)
    df_remission = (100_000 * df_remission_cases / df_with_condition_pt).fillna(0)
    df_excess_mortality = (100_000 * df_deaths / df_with_condition_pt).fillna(0)

    # Load artifact data
    # Check if artifact has keys, if not mock or warn?
    # Assuming artifact is valid as per original code
    try:
        df_art_csmr = art.load(f"cause.{cause}.cause_specific_mortality_rate")
        df_art_prevalence = art.load(f"cause.{cause}.prevalence")
        df_art_incidence = art.load(f"cause.{cause}.incidence_rate")
        df_art_remission = art.load(f"cause.{cause}.remission_rate")
        df_art_excess_mortality = art.load(f"cause.{cause}.excess_mortality_rate")
    except Exception as e:
        print(f"Error: Could not load artifact data: {e}", file=sys.stderr)
        sys.exit(1)

    # Set up the plotting grid: two columns (Males, Females), three rows (CSMR, Prevalence, Incidence)
    fig, axes = plt.subplots(5, 2, figsize=(14, 9), sharex=True)
    fig.suptitle(f"Validation Plots for {cause.capitalize()}", fontsize=16)
    metrics = [
        ("Cause Specific Mortality Rate", df_csmr, df_art_csmr),
        ("Excess Mortality", df_excess_mortality, df_art_excess_mortality),
        ("Prevalence", df_prevalence, df_art_prevalence),
        ("Incidence", df_incidence, df_art_incidence),
        ("Remission", df_remission, df_art_remission),
    ]
    sexes = ["Male", "Female"]
    plot_years = [2021]

    def age_x(age_group):
        if isinstance(age_group, pd.Interval):
            return (age_group.left + age_group.right) / 2
        return np.nan

    for row, (metric_name, data, artifact_data) in enumerate(metrics):
        for col, sex in enumerate(sexes):
            ax = axes[row, col]
            for year in plot_years:
                if not data.empty:
                    # Check if sex exists in data
                    try:
                        data_to_plot = data.unstack()
                        if sex in data_to_plot.columns:
                            data_to_plot.index = data_to_plot.index.map(age_x).astype(float)
                            data_to_plot = data_to_plot.sort_index()
                            t1 = data_to_plot
                            t1[sex].plot(ax=ax, label=f"{year}", marker="o", linestyle="none")
                    except Exception:
                        pass  # Data might be missing for some groups in short sims

            # Plot artifact data
            if not artifact_data.empty and sex in artifact_data.index:
                artifact_to_plot = artifact_data.loc[sex] * 100_000
                artifact_to_plot.index = artifact_to_plot.eval(
                    ".5*(age_start+age_end)"
                ).astype(float)
                artifact_to_plot = artifact_to_plot.sort_index()
                artifact_mean = artifact_to_plot.mean(axis=1)
                artifact_mean.plot(
                    ax=ax, label=f"Artifact {sex}", color=f"k", linestyle="-", alpha=0.75
                )

            ax.set_title(f"{metric_name} ({sex})")
            ax.set_ylabel(f"{metric_name} (Per 100,000 PY)")
            ax.grid(True)
            #             ax.set_yscale('log')
            ax.legend(loc="upper left")

    plt.xlabel("Age Group")
    plt.tight_layout(rect=[0, 0, 1, 0.96])

    if output_file:
        print(f"Saving plot to {output_file}")
        plt.savefig(output_file)
    else:
        plt.show()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run visual validation.")
    parser.add_argument(
        "--artifact_path", type=str, help="Path to the artifact", default=None
    )
    parser.add_argument(
        "--years", type=float, default=12 * 7 / 365, help="Number of years to run simulation"
    )
    parser.add_argument(
        "--output", type=str, default=None, help="Output file for the plot (e.g. plot.png)"
    )
    parser.add_argument(
        "--run-sim", action="store_true", help="Run the simulation (requires artifact)"
    )

    args = parser.parse_args()

    if args.run_sim:
        path = "src/vivarium_nih_moud/model_specifications/model_spec.yaml"
        sim = vi.InteractiveContext(path)

        if args.artifact_path:
            # Override artifact path if provided
            # This might require config update depending on how InteractiveContext works
            # But here we just load artifact object separately as in original code
            pass

        # In the original code, artifact path comes from config
        artifact_path = args.artifact_path or sim.configuration.input_data.artifact_path

        try:
            art = vi.Artifact(artifact_path)
            validation_plots(sim, art, args.years, args.output)
        except FileNotFoundError:
            print(
                f"Error: Artifact not found at {artifact_path}. Please provide a valid path.",
                file=sys.stderr,
            )
            sys.exit(1)
    else:
        print("Skipping simulation run. Use --run-sim to run.")
