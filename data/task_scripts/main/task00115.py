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

"""Template task in which two sticks need to hit each other."""
import numpy as np
import phyre.creator as creator_lib


@creator_lib.define_task_template(
    search_params=dict(require_two_ball_solvable=True),
    stick_length=np.linspace(0.2, 0.5, 10),
    stick1_x=np.linspace(0.05, 0.95, 19),
    stick2_x=np.linspace(0.05, 0.95, 19),
    version='2',
)
def build_task(C, stick_length, stick1_x, stick2_x):

    # Sticks cannot be too close together or too far apart.
    if stick2_x <= stick1_x + 1.75 * stick_length:
        raise creator_lib.SkipTemplateParams
    if stick2_x > stick1_x + 2.5 * stick_length:
        raise creator_lib.SkipTemplateParams

    # Add two sticks.
    bar1 = C.add('dynamic bar', scale=stick_length) \
            .set_angle(90.) \
            .set_bottom(0.) \
            .set_left(stick1_x * C.scene.width)
    bar2 = C.add('dynamic bar', scale=stick_length) \
            .set_angle(90.) \
            .set_bottom(0.) \
            .set_left(stick2_x * C.scene.width)

    # Add horizontal bar that prevents massive balls from dropping.
    C.add('static bar', scale=1.0) \
     .set_left(0.) \
     .set_bottom((stick_length + 0.25) * C.scene.height)

    # Create task.
    C.update_task(
        body1=bar1, body2=bar2, relationships=[C.SpatialRelationship.TOUCHING])
    C.set_meta(C.SolutionTier.TWO_BALLS)
