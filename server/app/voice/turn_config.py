"""Turn-handling constants shared by the LiveKit worker and the audio simulator's timing model.

Owned here so the simulator models exactly what production runs.
"""

from typing import Literal

MIN_ENDPOINTING_S = 0.5
MAX_ENDPOINTING_S = 1.6
MIN_INTERRUPTION_S = 0.2
INTERRUPTION_MODE: Literal["adaptive", "vad"] = "adaptive"
