from pathlib import Path

import vivarium_nih_moud
from vivarium_nih_moud.constants import metadata

BASE_DIR = Path(vivarium_nih_moud.__file__).resolve().parent

ARTIFACT_ROOT = Path(
    f"/mnt/team/simulation_science/pub/models/{metadata.PROJECT_NAME}/artifacts/"
)
