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

import enum

import phyre.interface.shared.ttypes as shared_if
import phyre.interface.shared.constants as shared_constants

SCENE_WIDTH: int = 256
"""Width of scene during simulation in pixels.
"""
SCENE_HEIGHT: int = 256
"""Height of scene during simulation in pixels.
"""


def color_to_name(color_id):
    return shared_if.Color._VALUES_TO_NAMES[color_id].lower()


def color_to_id(color_name):
    return shared_if.Color._NAMES_TO_VALUES[color_name.upper()]


# Dynamic states, colors, and types that an object can have.
DYNAMIC_VALUES = frozenset(['dynamic', 'static'])

ROLE_TO_COLOR_ID = dict(
    BACKGROUND=color_to_id('white'),
    USER_BODY=shared_constants.USER_BODY_COLOR,
    STATIC=color_to_id('black'),
    STATIC_OBJECT=color_to_id('purple'),
    DYNAMIC=color_to_id('gray'),
    DYNAMIC_SUBJECT=color_to_id('blue'),
    DYNAMIC_OBJECT=color_to_id('green'),
)

STATIC_COLOR_IDS = {
    ROLE_TO_COLOR_ID['STATIC'], ROLE_TO_COLOR_ID['STATIC_OBJECT']
}
DYNAMIC_COLOR_IDS = {
    ROLE_TO_COLOR_ID['DYNAMIC'],
    ROLE_TO_COLOR_ID['DYNAMIC_OBJECT'],
    ROLE_TO_COLOR_ID['DYNAMIC_SUBJECT'],
}

# Standard objects that could be created by name and scale.
FACTORY_OBJECT_TYPES = frozenset([
    'ball',
    'bar',
    'box',
    'jar',
    'standingsticks',
])

ALL_OBJECT_TYPES = frozenset(
    list(FACTORY_OBJECT_TYPES) + [
        'poly',
        'compound',
        'left-wall',
        'right-wall',
        'top-wall',
        'bottom-wall',
    ])


@enum.unique
class SolutionTier(enum.IntEnum):
    # Main tiers.
    BALL = enum.auto()
    TWO_BALLS = enum.auto()
    RAMP = enum.auto()
    # WIP tasks for main tiers.
    PRE_BALL = enum.auto()
    PRE_TWO_BALLS = enum.auto()
    PRE_RAMP = enum.auto()
    # Vaguely classified.
    SINGLE_OBJECT = enum.auto()
    GENERAL = enum.auto()
    # From Tools Challenge.
    VIRTUAL_TOOLS = enum.auto()


NUM_COLORS: int = len(ROLE_TO_COLOR_ID)
"""Number of different colors used for objects in phyre simulations.
"""
