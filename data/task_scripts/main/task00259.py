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

"""Template task in which to sticks need to hit each other."""

import phyre.creator as creator_lib
import numpy as np

@creator_lib.define_task_template(
    search_params=dict(require_two_ball_solvable=True),
    dist1 = np.linspace(0.05, 0.3, 4),
    dist2 = np.linspace(0.05, 0.3, 4),
    bar1_height = np.linspace(0.08, 0.12, 3),
    bar2_height = np.linspace(0.08, 0.12, 3),
    version="2")
def build_task(C, dist1, dist2, bar1_height, bar2_height):
    # Add two sticks.
    margin=0.2
    bar1 = C.add('dynamic bar', scale=0.4) \
            .set_angle(90.) \
            .set_bottom(0.) \
            .set_left(margin*C.scene.width)
    bar2 = C.add('dynamic bar', scale=0.4) \
            .set_angle(90.) \
            .set_bottom(0.) \
            .set_left((1-margin)*C.scene.width)

    # Add small bar for target bar to vault over
    C.add('static bar', scale=bar1_height) \
        .set_angle(90.) \
        .set_bottom(0.) \
        .set_left((dist1+margin)*C.scene.width)

    # Add small bar for target bar to vault over
    C.add('static bar', scale=bar2_height) \
        .set_angle(90.) \
        .set_bottom(0.) \
        .set_left( (1-(dist2+margin))*C.scene.width)


    # Create task.
    C.update_task(body1=bar1,
                  body2=bar2,
                  relationships=[C.SpatialRelationship.TOUCHING])
    C.set_meta(C.SolutionTier.PRE_TWO_BALLS)
