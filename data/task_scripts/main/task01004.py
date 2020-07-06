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
"""Gap"""
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
    slopeLeft = [300, 450]
    slopeRight = [200, 350]
    slopeWidth = [200, 300]
    ballXPos = [50, 150]
    ballYPos = [15, 50]
    gapWidth = [60, 200]
    supportX = [5, 25]
    supportY = [-5, 80]
    lidThick = [15, 40]

    flip_lr = rng.uniform(0, 1) < 0.5
    ## Make the slope
    sL = rng.uniform(slopeLeft[0], slopeLeft[1])
    sR = rng.uniform(slopeRight[0], slopeRight[1])
    sW = rng.uniform(slopeWidth[0], slopeWidth[1])
    slopeVerts = [[0.0, 0.0], [0.0, sL], [sW, sR], [sW, 0]]

    ## Make the gap
    gW = rng.uniform(gapWidth[0], gapWidth[1])
    strutSupportBox = [sW, 0, sW + gW, sR - 150]

    ## Make the support
    jitterX = rng.uniform(supportX[0], supportX[1])
    jitterY = rng.uniform(supportY[0], supportY[1])
    lidT = rng.uniform(lidThick[0], lidThick[1])
    supportBox = [
        sW + jitterX, sR + jitterY, sW + gW - jitterX, sR + jitterY + lidT
    ]

    ## Make the goal
    goalSegs = [[sW + gW, sR - 50], [sW + gW, 5], [550, 5], [550, sR - 50]]

    ## Find the ball position
    bX = rng.uniform(ballXPos[0], ballXPos[1])
    bY = sL * (sW - bX) / sW + sR
    bpos = [
        bX, bY +
        rng.uniform(ballYPos[0], np.min([ballYPos[1], vt.VT_SCALE - bY - 15]))
    ]

    ## Make the world getting into the container
    slopeVerts.reverse()

    if flip_lr:
        slopeVerts = vt.flip_left_right(slopeVerts)
        bpos = vt.flip_left_right(bpos)

    slope = C.add_convex_polygon(vt.convert_phyre_tools_vertices(slopeVerts),
                                 False)
    container, _ = vt.add_container(C,
                                    goalSegs,
                                    10,
                                    False,
                                    True,
                                    flip_lr=flip_lr)
    ball = C.add('dynamic ball',
                 30. / vt.VT_SCALE,
                 center_x=bpos[0] * C.scene.width / vt.VT_SCALE,
                 center_y=bpos[1] * C.scene.height / vt.VT_SCALE)
    strutBox = vt.add_box(C, strutSupportBox, False, flip_lr=flip_lr)
    support = vt.add_box(C, supportBox, True, flip_lr=flip_lr)

    C.update_task(body1=ball,
                  body2=container,
                  relationships=[C.SpatialRelationship.TOUCHING])

    C.set_meta(C.SolutionTier.VIRTUAL_TOOLS)
