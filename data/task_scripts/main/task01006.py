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
"""Unbox"""
"""Template task in which you prevent something from falling so ball can roll into container."""
import numpy as np
import phyre.creator as creator_lib
import phyre.virtual_tools as vt


@creator_lib.define_task_template(
    seed=range(1000),
    version="2",
    search_params=dict(required_flags=['BALL:GOOD_STABLE'],
                       excluded_flags=['BALL:TRIVIAL'],
                       diversify_tier='ball'),
)
def build_task(C, seed):
    rng = np.random.RandomState(seed=seed)
    slopeLeft = [200, 400]
    slopeRight = [100, 190]
    slopeWidth = [100, 300]
    ballXPos = [30, 100]
    ballYPos = [15, 50]
    goalHeightMin = 60
    goalWidth = [80, 150]
    lidWidthExtra = [10, 50]
    lidThick = [8, 20]

    flip_lr = rng.uniform(0, 1) < 0.5
    ## Make the slope
    sL = rng.uniform(slopeLeft[0], slopeLeft[1])
    sR = rng.uniform(slopeRight[0], slopeRight[1])
    sW = rng.uniform(slopeWidth[0], slopeWidth[1])
    slopeVerts = [[0, 0], [0, sL], [sW, sR], [sW, 0]]

    ## Make the goal
    goalH = rng.uniform(goalHeightMin, sR)
    goalW = rng.uniform(goalWidth[0], goalWidth[1])
    goalL = sW
    goalR = sW + goalW
    goalVerts = [[goalL, goalH], [goalL, 5], [goalR, 5], [goalR, goalH]]

    ## Find the ball position
    bpos = [
        rng.uniform(ballXPos[0], ballXPos[1]),
        sL + min([rng.uniform(ballYPos[0], ballYPos[1]), vt.VT_SCALE - 15])
    ]

    ## Make the lid
    lidT = rng.uniform(lidThick[0], lidThick[1])
    lidExtent = rng.uniform(lidWidthExtra[0], lidWidthExtra[1])
    lidBbox = [goalL, goalH + 5, goalR + lidExtent, goalH + 5 + lidT]

    ## Make the world getting into the container
    slopeVerts.reverse()

    if flip_lr:
        slopeVerts = vt.flip_left_right(slopeVerts)
        bpos = vt.flip_left_right(bpos)

    slope = C.add_convex_polygon(vt.convert_phyre_tools_vertices(slopeVerts),
                                 False)
    container, _ = vt.add_container(C,
                                    goalVerts,
                                    10,
                                    False,
                                    True,
                                    flip_lr=flip_lr)
    ball = C.add('dynamic ball',
                 30. / vt.VT_SCALE,
                 center_x=bpos[0] * C.scene.width / vt.VT_SCALE,
                 center_y=bpos[1] * C.scene.height / vt.VT_SCALE)
    lid = vt.add_box(C, lidBbox, True, flip_lr=flip_lr)
    C.update_task(body1=ball,
                  body2=container,
                  relationships=[C.SpatialRelationship.TOUCHING])

    C.set_meta(C.SolutionTier.VIRTUAL_TOOLS)
