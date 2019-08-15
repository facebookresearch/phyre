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

"""Template task with a ball that must fall on the other side of a jar."""
import phyre.creator as creator_lib

__JAR_XS = [val * 0.1 for val in range(3, 7)]
__JAR_SCALES = [val * 0.1 for val in range(2, 6)]
__BALL_XS = [val * 0.1 for val in range(2, 8)]
__BALL_YS = [val * 0.1 for val in range(5, 8)]


@creator_lib.define_task_template(
    jar_x=__JAR_XS, jar_scale=__JAR_SCALES, ball_x=__BALL_XS, ball_y=__BALL_YS, version='2')
def build_task(C, jar_x, jar_scale, ball_x, ball_y):

    # Add jar.
    jar = C.add('dynamic jar', scale=jar_scale) \
        .set_left(jar_x * C.scene.width) \
        .set_bottom(0.)
    if jar.left < 0. or jar.right > C.scene.width:
        raise creator_lib.SkipTemplateParams

    # Add ball that is not hovering over jar.
    ball = C.add('dynamic ball', scale=0.1) \
        .set_center_x(ball_x * C.scene.width) \
        .set_bottom(0.9 * C.scene.height)

    # Add a floor bar into two parts: target part and non-target part.
    if ball.left > jar.right:    # ball is right of jar
        bottom_wall = C.add('static bar', 1.0, bottom=0, right=jar.left)
        C.add('static bar', 1.0, bottom=0, left=bottom_wall.right)
    elif ball.right < jar.left:  # ball is left of jar
        bottom_wall = C.add('static bar', 1.0, bottom=0, left=jar.right)
        C.add('static bar', 1.0, bottom=0, right=bottom_wall.left)
    else:
        raise creator_lib.SkipTemplateParams

    jar.set_bottom(bottom_wall.top)

    # Create assignment.
    C.update_task(body1=ball,
                  body2=bottom_wall,
                  relationships=[C.SpatialRelationship.TOUCHING])
    C.set_meta(C.SolutionTier.PRE_TWO_BALLS)
