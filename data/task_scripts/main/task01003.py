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
"""Falling"""
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
    containerHeight = [50, 100]
    containerBottom = [50, 150]
    containerOverhangL = [10, 25]
    containerOverhangR = [10, 25]
    containerElevation = [10, 300]
    containerX = [30, (vt.VT_SCALE - 150 - 55)]
    ballRadius = [7, 15]

    flip_lr = rng.uniform(0, 1) < 0.5
    cH = rng.uniform(containerHeight[0], containerHeight[1])
    cB = rng.uniform(containerBottom[0], containerBottom[1])
    cOL = rng.uniform(containerOverhangL[0], containerOverhangL[1])
    cOR = rng.uniform(containerOverhangR[0], containerOverhangR[1])
    cE = rng.uniform(containerElevation[0], containerElevation[1])
    cX = rng.uniform(containerX[0], containerX[1])
    bR = rng.uniform(ballRadius[0], ballRadius[1])

    ## Get bottom left coordinate of container, coordinates of ball
    xBottom = cX
    yBottom = cE - cH / 2
    xBall = cB / 2 + cX
    yBall = yBottom + 8 + bR

    if flip_lr:
        xBall = vt.flip_left_right(xBall)

    ## Make the world
    container, _ = vt.add_container(
        C, [[xBottom - cOL, yBottom + cH], [xBottom, yBottom],
            [xBottom + cB, yBottom], [xBottom + cB + cOR, yBottom + cH]],
        7,
        True,
        False,
        flip_lr=flip_lr)
    floor = vt.add_box(C, [0., 0., vt.VT_SCALE, 7.], False, flip_lr=flip_lr)
    ball = C.add('dynamic ball',
                 bR * 2. / vt.VT_SCALE,
                 center_x=xBall * C.scene.width / vt.VT_SCALE,
                 center_y=yBall * C.scene.height / vt.VT_SCALE)
    # Create assignment:
    C.update_task(body1=ball,
                  body2=floor,
                  relationships=[C.SpatialRelationship.TOUCHING])
    C.set_meta(C.SolutionTier.VIRTUAL_TOOLS)
    '''
  var pgw = new PGWorld(DIMS, GRAVITY)
  pgw.addContainer('Container', [[xBottom-cOL, yBottom+cH], [xBottom, yBottom], [xBottom+cB, yBottom], [xBottom+cB+cOR, yBottom+cH]], 7, null, 'blue')
  pgw.addBoxGoal('Floor', [0, 0, 600, 7], 'green')
  pgw.addBall('Ball', [xBall, yBall], bR, 'red')
  pgw.attachSpecificInGoal('Floor', 'Ball', 1)

  return pgw'''
