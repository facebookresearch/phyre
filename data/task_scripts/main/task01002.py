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
"""Catapult"""
"""Template task in which you prevent something from falling so ball can roll into container."""
import numpy as np
import phyre.creator as creator_lib
import phyre.virtual_tools as vt


@creator_lib.define_task_template(
    seed=range(1000),
    version="2",
    search_params=dict(
        max_search_tasks=250,
        required_flags=['BALL:GOOD_STABLE'],
        excluded_flags=['BALL:TRIVIAL'],
    ),
)
def build_task(C, seed):
    rng = np.random.RandomState(seed=seed)
    cataWidth = [200, 400]
    cataHeight = [30, 100]
    ballRad = [5, 15]
    strutWidth = [10, 50]
    strutHeight = [60, 200]
    goalWidth = [60, 150]
    goalHeight = [60, 180]
    cataThick = [5, 10]
    spacing = [25, 100]
    strutPlace = [0, 150]

    ## Define the features first
    cW = rng.uniform(cataWidth[0], cataWidth[1])
    cH = 20.
    bR = rng.uniform(ballRad[0], ballRad[1])
    sW = rng.uniform(strutWidth[0], strutWidth[1])
    sH = rng.uniform(strutHeight[0], strutHeight[1])
    gW = rng.uniform(goalWidth[0], goalWidth[1])
    gH = rng.uniform(goalHeight[0], goalHeight[1])
    cT = rng.uniform(cataThick[0], cataThick[1])
    sp = rng.uniform(spacing[0], spacing[1])
    stP = rng.uniform(strutPlace[0], strutPlace[1])
    stP = min([stP, cW / 2])

    flip_lr = rng.uniform(0, 1) < 0.5
    ## Then fit together
    cataCent = vt.VT_SCALE - gW - sp - cW / 2
    cataLeft = cataCent - cW / 2

    ## Make the world
    strut = vt.add_box(
        C, [cataCent - sW / 2 + stP, 0, cataCent + sW / 2 + stP, sH],
        False,
        flip_lr=flip_lr)
    cradle = vt.add_box(C, [cataLeft, 0, cataLeft + 10, sH],
                        False,
                        flip_lr=flip_lr)
    container, _ = vt.add_container(
        C, [[vt.VT_SCALE - gW, gH], [vt.VT_SCALE - gW, 5], [vt.VT_SCALE - 5, 5],
            [vt.VT_SCALE - 5, gH]],
        10,
        False,
        True,
        flip_lr=flip_lr)
    polys = [[[cataLeft, sH], [cataLeft, sH + cT], [cataLeft + cT, sH + cT],
              [cataLeft + cT, sH]],
             [[cataLeft, sH + cT], [cataLeft, sH + cH],
              [cataLeft + cT, sH + cH], [cataLeft + cT, sH + cT]],
             [[cataLeft + cT, sH], [cataLeft + cT, sH + cT],
              [cataLeft + cW, sH + cT], [cataLeft + cW, sH]]]
    for p in polys:
        p.reverse()

    if flip_lr:
        p = vt.flip_left_right(p)
        center_x = vt.flip_left_right(cataLeft + cT + bR + 30)
    else:
        center_x = cataLeft + cT + bR + 30
    converted_polylist = [
        vt.convert_phyre_tools_vertices(poly) for poly in polys
    ]
    catapult = C.add_multipolygons(polygons=converted_polylist, dynamic=True)

    ball = C.add('dynamic ball',
                 bR * 2. / vt.VT_SCALE,
                 center_x=center_x * C.scene.width / vt.VT_SCALE,
                 center_y=(sH + cT + bR) * C.scene.width / vt.VT_SCALE)
    C.update_task(body1=ball,
                  body2=container,
                  relationships=[C.SpatialRelationship.TOUCHING])

    C.set_meta(C.SolutionTier.VIRTUAL_TOOLS)
    '''pgw.addBox('Strut', [cataCent - sW/2 + stP, 0, cataCent + sW/2 + stP, sH], 'black', 0)
  pgw.addBox('Cradle', [cataLeft, 0, cataLeft+10, sH], 'black', 0)
  pgw.addContainer('Goal', [[DIMS[0]-gW, 5], [DIMS[0]-gW, gH], [DIMS[0]-5, gH], [DIMS[0]-5, 5]], 10, 'green', 'black', 0)
  pgw.addCompound('Catapult', [
    [[cataLeft, sH], [cataLeft, sH+cT], [cataLeft+cT, sH+cT], [cataLeft+cT, sH]],
    [[cataLeft, sH+cT], [cataLeft, sH+cH], [cataLeft+cT, sH+cH], [cataLeft+cT, sH+cT]],
    [[cataLeft+cT, sH], [cataLeft+cT, sH+cT], [cataLeft+cW, sH+cT], [cataLeft+cW, sH]]
  ], 'blue', 1)
  pgw.addBall('Ball', [cataLeft+cT+bR+30, sH+cT+bR], bR, 'red', 1)
  pgw.attachSpecificInGoal('Goal', 'Ball', 1)
  return pgw'''
