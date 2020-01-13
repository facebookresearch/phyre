# Copyright (c) Facebook, Inc. and its affiliates.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from typing import Tuple

from phyre import action_mappers as _action_mappers
from phyre.creator.constants import NUM_COLORS, SCENE_HEIGHT, SCENE_WIDTH
from phyre.metrics import get_fold, list_eval_setups, eval_setup_to_action_tier, Evaluator, MAIN_EVAL_SETUPS, MAX_TEST_ATTEMPTS
from phyre.action_simulator import initialize_simulator, ActionSimulator, SimulationStatus
from phyre.objects_util import featurized_objects_vector_to_raster
from phyre.simulation import FeaturizedObjects, Simulation
from phyre.simulation_cache import SimulationCache, get_default_100k_cache
from phyre.vis import observations_to_float_rgb, observations_to_uint8_rgb

ACTION_TIERS: Tuple[str] = tuple(sorted(_action_mappers.MAIN_ACITON_MAPPERS))
"""List of action tiers in phyre.
"""
