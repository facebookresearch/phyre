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

import phyre.creator as creator_lib
import numpy as np

__JAR_HEIGHT=np.linspace(0.15, 0.5, 5)
__BALL_SIZE=np.linspace(0.05, 0.1, 3)
__PIVOT_HEIGHT=np.linspace(0.05, 0.15, 3)

@creator_lib.define_task_template(
    jar_height=__JAR_HEIGHT,
    l_ball=__BALL_SIZE,
    r_ball=__BALL_SIZE,
    l_pivot=__PIVOT_HEIGHT,
    r_pivot=__PIVOT_HEIGHT,
    max_tasks=100,
    version="9"
)
def build_task(C, jar_height, l_ball, r_ball, l_pivot, r_pivot):
    if (l_ball == 0.1 or r_ball == 0.1) and jar_height >= 0.3:
        raise creator_lib.SkipTemplateParams

    # Create left lever and pivot.
    ball_size = l_ball
    pivot_l = C.add('static bar', 
        scale=l_pivot,
        angle=90.,
        bottom=0, 
        left=0.2*C.scene.width)
    lever_l = C.add('dynamic bar', 
        scale=0.3,
        bottom=pivot_l.top, 
        center_x=pivot_l.center_x)
    ball_l = C.add('dynamic ball', 
        scale=l_ball,
        left=lever_l.left,
        bottom=lever_l.top)
    counter_weight_l = C.add('dynamic ball', 
        scale=l_ball,
        right=lever_l.right,
        bottom=lever_l.top)
    
    # Create right lever and pivot.
    pivot_r = C.add('static bar', 
        scale=r_pivot,
        angle=90.,
        bottom=0, 
        right=0.8*C.scene.width)
    lever_r = C.add('dynamic bar', 
        scale=0.3,
        bottom=pivot_r.top, 
        center_x=pivot_r.center_x)
    counter_weight_r = C.add('dynamic ball', 
        scale=r_ball,
        left=lever_r.left,
        bottom=lever_r.top)
    ball_r= C.add('dynamic ball', 
        scale=r_ball,
        right=lever_r.right,
        bottom=lever_r.top)
    
    
    #Create a jar on a post with a backboard
    post = C.add('static bar', 
        scale=jar_height,
        angle=90.,
        bottom=0.0, 
        right=0.5*C.scene.width)
    jar = C.add('static jar', 
        scale=0.3,
        bottom=post.top, 
        center_x=0.5*C.scene.width)
    backboard = C.add('static bar', 
        scale=1.0,
        angle=90.,
        bottom=jar.top +0.2*C.scene.height, 
        right=0.5*C.scene.width)
    
    # Create task.
    C.update_task(
        body1=ball_l,
        body2=ball_r,
        relationships=[C.SpatialRelationship.TOUCHING])
    C.set_meta(C.SolutionTier.PRE_TWO_BALLS)
