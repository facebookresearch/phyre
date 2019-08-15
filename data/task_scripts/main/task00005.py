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

"""Template task with a ball that should not fall into a jar."""
import phyre.creator as creator_lib

__JAR_XS = [val * 0.1 for val in range(2, 8)]
__JAR_YS = [val * 0.1 for val in range(0, 3)]
__JAR_SCALES = [val * 0.05 for val in range(3, 9)]
__BALL_YS = [val * 0.1 for val in range(7, 10)]


@creator_lib.define_task_template(
    jar_x=__JAR_XS,
    jar_y=__JAR_YS,
    jar_scale=__JAR_SCALES,
    ball_y=__BALL_YS,
    search_params=dict(
        required_flags=['BALL:GOOD_STABLE'],
        diversify_tier='ball'
    ),
    version='3')
def build_task(C, jar_x, jar_y, jar_scale, ball_y):

    # Add bottom wall.
    bottom_wall = C.add('static bar', scale=1.0, bottom=0., left=0.)

    # Add jar.
    jar = C.add('dynamic jar',
                scale=jar_scale,
                bottom=bottom_wall.top + jar_y * C.scene.height,
                left=jar_x * C.scene.width)
    if jar.left < 0. or jar.right > C.scene.width:
        raise creator_lib.SkipTemplateParams

    # Add ball that hovers over the jar.
    ball = C.add('dynamic ball',
                 scale=0.1,
                 bottom=ball_y * C.scene.height,
                 center_x=jar.left + jar.width / 2.)

    # Create assignment.
    C.update_task(body1=ball,
                  body2=bottom_wall,
                  relationships=[C.SpatialRelationship.TOUCHING])
    C.set_meta(C.SolutionTier.BALL)
