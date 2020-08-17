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
import numpy as np
import phyre.creator as creator_lib
import phyre.virtual_tools as vt


@creator_lib.define_task_template(
    seed=range(1000),
    version="1",
    search_params=dict(max_search_tasks=300,
                       required_flags=['BALL:GOOD_STABLE'],
                       excluded_flags=['BALL:TRIVIAL'],
                       diversify_tier='ball'),
)
def build_task(C, seed):
    rng = np.random.RandomState(seed=seed)

    blockRange = [2, 6]
    stackHeight = 3
    tableHeight = [50, 200]
    blockSize = [15, 40]
    maxTabWid = 150
    tableX = [10, 400]

    flip_lr = rng.uniform(0, 1) < 0.5
    bSize = rng.uniform(blockSize[0], blockSize[1])
    tHeight = rng.uniform(tableHeight[0], tableHeight[1])

    ## Make the stacks
    stackSizes = [rng.randint(blockRange[0], blockRange[1])]
    lastSize = stackSizes[0]
    for i in range(1, stackHeight):
        lastSize = rng.randint(0, lastSize)
        if lastSize == 0:
            break
        stackSizes.append(lastSize)

    blockIdxs = []
    for i in range(0, len(stackSizes)):
        for j in range(0, stackSizes[i]):
            blockIdxs.append(str(i) + '_' + str(j))

    blockToHit = blockIdxs[rng.randint(0, len(blockIdxs))]

    baseWidth = stackSizes[0] * bSize
    tWidth = rng.uniform(baseWidth - bSize, maxTabWid)
    tPos = rng.uniform(tableX[0], tableX[1])

    floor = vt.add_box(C, [0, 0, vt.VT_SCALE, 10], False, flip_lr=flip_lr)
    table = vt.add_box(C, [tPos, 10, tPos + tWidth, tHeight],
                       False,
                       flip_lr=flip_lr)

    baseH = tHeight
    for i in range(0, len(stackSizes)):
        stackN = stackSizes[i]
        stackWid = stackN * bSize
        baseX = tPos + tWidth / 2 - stackWid / 2
        for j in range(0, stackN):
            blockExt = [baseX, baseH, baseX + bSize, baseH + bSize]
            if str(i) + '_' + str(j) == blockToHit:
                goal = True
            else:
                goal = False

            blockID = vt.add_box(C, blockExt, True, flip_lr=flip_lr)
            if goal:
                goalBlock = blockID
            baseX += bSize
        baseH += bSize

    C.update_task(body1=goalBlock,
                  body2=floor,
                  relationships=[C.SpatialRelationship.TOUCHING])

    C.set_meta(C.SolutionTier.VIRTUAL_TOOLS)
