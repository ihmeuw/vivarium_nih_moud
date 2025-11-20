import jax.numpy as jnp
import numpyro
from numpyro import distributions as dist


def add_age_smoothness_factors(
    knot_val_dict, name, sigma_first=0.2, sigma_second=0.1, EPS=1e-8
):
    """Add first- and second-difference smoothness priors along age."""
    vals = knot_val_dict[name]  # shape (n_age, n_year)

    # Work on the log scale to respect positivity and relative changes.
    log_vals = jnp.log(vals + EPS)

    # First differences along age (axis 0).
    d1 = jnp.diff(log_vals, axis=0)  # shape (n_age-1, n_year)

    # Second differences along age: diff of first differences.
    d2 = jnp.diff(d1, axis=0)  # shape (n_age-2, n_year)

    # Penalize both sets of differences toward 0.
    numpyro.factor(
        f"{name}_age_first_diff",
        dist.Normal(0.0, sigma_first).log_prob(d1).sum(),
    )
    numpyro.factor(
        f"{name}_age_second_diff",
        dist.Normal(0.0, sigma_second).log_prob(d2).sum(),
    )


def add_age_monotone_increasing_factor(
    knot_val_dict: dict[str, jnp.ndarray],
    name: str,
    sigma: float = 0.1,
    use_log: bool = True,
    EPS=1e-8,
):
    """
    Encourage the age-pattern of `knot_val_dict[name]` to be non-decreasing
    in age (axis=0), for each year independently.

    Monotonicity is enforced on the log scale by default:
        log(vals(age+1)) - log(vals(age)) >= 0

    Any negative differences are penalized quadratically.

    Parameters
    ----------
    name : str
        Key in knot_val_dict.
    knot_val_dict : dict[str, jnp.ndarray]
        Dict of parameter fields, each shape (n_age, n_year).
    sigma : float
        Strength/scale of the penalty. Smaller = stronger belief that
        the curve is monotone increasing.
    use_log : bool
        If True, impose monotonicity on log(vals); otherwise on vals.
    """
    vals = knot_val_dict[name]  # shape (n_age, n_year)

    if use_log:
        vals = jnp.log(vals + EPS)

    # First differences along age: age_{a+1} - age_a
    diffs = jnp.diff(vals, axis=0)  # shape (n_age-1, n_year)

    # Amount of violation: how far below zero each difference is.
    # If diffs >= 0 → violations = 0 (no penalty)
    # If diffs < 0  → violations = -diffs > 0
    violations = jnp.maximum(-diffs, 0.0)

    # Simple quadratic penalty: ~ Normal(0, sigma) on violations,
    # but without bothering with constants.
    penalty = -0.5 * jnp.square(violations / sigma).sum()

    numpyro.factor(f"{name}_age_monotone_increasing", penalty)


def add_rate_ordering_factor(
    knot_val_dict: dict[str, jnp.ndarray],
    larger_name: str,
    smaller_name: str,
    sigma: float = 0.1,
    use_log: bool = True,
    margin: float = 0.0,
    EPS=1e-8,
):
    """
    Encourage knot_val_dict[larger_name] >= knot_val_dict[smaller_name]
    (optionally on the log scale), pointwise over age & year.

    Any violations are penalized quadratically.

    Parameters
    ----------
    larger_name : str
        Key for the field that should be >= the other (e.g. "f_severe").
    smaller_name : str
        Key for the field that should be <= the other (e.g. "f_mild").
    knot_val_dict : dict[str, jnp.ndarray]
        Dict of parameter fields, each shape (n_age, n_year).
    sigma : float
        Scale of the penalty. Smaller = stronger belief in the inequality.
    use_log : bool
        If True, apply inequality in log-space (i.e., multiplicative order).
    margin : float
        Optional strictness margin in the same scale you’re working in:
        - If use_log=True, margin is in log units (e.g. log(1.1) for 10%).
        - If use_log=False, margin is in raw units.
        The prior then prefers larger >= smaller + margin.
    """
    a = knot_val_dict[larger_name]
    b = knot_val_dict[smaller_name]

    if use_log:
        a = jnp.log(a + EPS)
        b = jnp.log(b + EPS)

    # We want: a >= b + margin
    diffs = a - (b + margin)  # shape (n_age, n_year)

    # Violations where a < b + margin
    violations = jnp.maximum(-diffs, 0.0)

    # Quadratic penalty on violations
    penalty = -0.5 * jnp.square(violations / sigma).sum()

    numpyro.factor(f"{larger_name}_ge_{smaller_name}", penalty)
