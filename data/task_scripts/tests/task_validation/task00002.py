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


@creator_lib.define_task
def build_task(C):
    b1 = C.add_box(50, 50).set_bottom(0).set_left(200)
    b2 = C.add_box(100, 50).set_bottom(0).set_left(50)
    C.update_task(body1=b1, body2=b2,
                  relationships=[C.SpatialRelationship.RIGHT_OF],
                  description="Is smaller box right of bigger box?")
