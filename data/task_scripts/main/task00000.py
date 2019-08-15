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

"""Template task in which two balls should touch each other."""
import numpy as np
import phyre.creator as creator_lib


@creator_lib.define_task_template(
    ball1_x=np.linspace(0.05, 0.95, 19),
    ball2_x=np.linspace(0.05, 0.95, 19),
    ball1_r=np.linspace(0.06, 0.12, 3),
    ball2_r=np.linspace(0.06, 0.12, 3),
    height=np.linspace(0.2, 0.8, 5),
    search_params=dict(required_flags=['BALL:GOOD_STABLE']),
    version='2',
)
def build_task(C, ball1_x, ball2_x, ball1_r, ball2_r, height):

    # Task definition is symmetric.
    if ball2_x <= ball1_x:
        raise creator_lib.SkipTemplateParams

    # Add two balls.
    ball1 = C.add(
        'dynamic ball',
        scale=ball1_r,
        center_x=ball1_x * C.scene.width,
        bottom=height * C.scene.height)
    ball2 = C.add(
        'dynamic ball',
        scale=ball2_r,
        center_x=ball2_x * C.scene.width,
        bottom=height * C.scene.height)
    if (ball2.left - ball1.right) < max(ball1_r, ball2_r) * C.scene.width:
        raise creator_lib.SkipTemplateParams
    if ball1.left <= 0:
        raise creator_lib.SkipTemplateParams
    if ball2.right >= C.scene.width - 1:
        raise creator_lib.SkipTemplateParams

    # Create assignment:
    C.update_task(
        body1=ball1,
        body2=ball2,
        relationships=[C.SpatialRelationship.TOUCHING])
    C.set_meta(C.SolutionTier.BALL)
