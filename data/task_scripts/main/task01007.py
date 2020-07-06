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
"""Remove"""
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
    goalWidth = [100, 200]
    goalHeight = [80, 100]
    ballRad = [7, 12]
    slopeLeft = [40, 70]
    slopeRight = [5, 10]
    slopeWidth = [200, 275]
    slopeHeight = [380, 450]
    platformLeft = [300, 400]
    platformRight = [475, 500]
    platformHeight = [200, 250]
    blockSize = [30, 40]
    pWidth = 15  ## Platform Vertical Width

    flip_lr = rng.uniform(0, 1) < 0.5
    gW = rng.uniform(goalWidth[0], goalWidth[1])
    gH = rng.uniform(goalHeight[0], goalHeight[1])
    bR = rng.uniform(ballRad[0], ballRad[1])
    sL = rng.uniform(slopeLeft[0], slopeLeft[1])
    sR = rng.uniform(slopeRight[0], slopeRight[1])
    sW = rng.uniform(slopeWidth[0], slopeWidth[1])
    sH = rng.uniform(slopeHeight[0], slopeHeight[1])
    pL = rng.uniform(platformLeft[0], platformLeft[1])
    pR = rng.uniform(platformRight[0], platformRight[1])
    pH = rng.uniform(platformHeight[0], platformHeight[1])
    bS = rng.uniform(blockSize[0], blockSize[1])
    jitter = rng.uniform(0, pR - pL)
    ## Set params
    bLeft = (pR - pL) / 2 - bS / 2  ## Left bound of block

    slopeVerts = [[0, sH], [0, sH + sL], [sW, sH + sR], [sW, sH]]
    if flip_lr:
        slopeVerts = vt.flip_left_right(slopeVerts)
        blockXPos = vt.flip_left_right(pL + jitter)
        ballXPos = vt.flip_left_right(bR + 5)
    else:
        blockXPos = pL + jitter
        ballXPos = bR + 5

    ## Make the world
    slopeVerts.reverse()
    slope = C.add_convex_polygon(vt.convert_phyre_tools_vertices(slopeVerts),
                                 False)
    container, _ = vt.add_container(
        C, [[vt.VT_SCALE - 5 - gW, gH], [vt.VT_SCALE - 5 - gW, 0.0],
            [vt.VT_SCALE - 5, 0.0], [vt.VT_SCALE - 5, gH]],
        10,
        False,
        True,
        flip_lr=flip_lr)
    #block = vt.add_box(C, [pL, pH + pWidth, bS + pL, pH + pWidth + bS], True)
    block = C.add('dynamic ball',
                  bS / vt.VT_SCALE,
                  center_x=blockXPos * C.scene.width / vt.VT_SCALE,
                  bottom=(pH + pWidth) * C.scene.width / vt.VT_SCALE)
    platform = vt.add_box(C, [pL, pH, pR, pH + pWidth], False, flip_lr=flip_lr)
    ball = C.add('dynamic ball',
                 bR * 2 / vt.VT_SCALE,
                 center_x=ballXPos * C.scene.width / vt.VT_SCALE,
                 center_y=(sL + sH + bR) * C.scene.height / vt.VT_SCALE)

    C.update_task(body1=ball,
                  body2=container,
                  relationships=[C.SpatialRelationship.TOUCHING])

    C.set_meta(C.SolutionTier.VIRTUAL_TOOLS)
