// Copyright (c) Facebook, Inc. and its affiliates.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
#ifndef CREATOR_H_
#define CREATOR_H_

#include "gen-cpp/scene_types.h"

bool cmpIntVector(const ::scene::IntVector& a, const ::scene::IntVector& b);

::scene::Vector getVector(float x, float y);

::scene::IntVector getIntVector(int x, int y);

// Angle is in radians.
::scene::Body buildBox(float x, float y, float width, float height,
                       float angle = 0, bool dynamic = true);

::scene::Body buildPolygon(float x, float y,
                           const std::vector<::scene::Vector>& vertices,
                           float angle = 0, bool dynamic = true);

::scene::Body buildCircle(float x, float y, float radius, bool dynamic = true);

#endif  // CREATOR_H_
