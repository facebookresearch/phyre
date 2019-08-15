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
#ifndef THRIFT_BOX2D_CONVERSION_H
#define THRIFT_BOX2D_CONVERSION_H
#include <memory>

#include "Box2D/Box2D.h"
#include "gen-cpp/scene_types.h"
#include "image_to_box2d.h"

constexpr float PIXELS_IN_METER = 6.0;

struct Box2dData {
  enum ObjectType { GENERAL, USER, BOUNDING_BOX };
  size_t object_id;
  ObjectType object_type;
};

class b2WorldWithData : public b2World {
 public:
  using b2World::b2World;

  ~b2WorldWithData() {}

  Box2dData* CreateData() {
    _data.emplace_back(new Box2dData);
    return _data.back().get();
  }

 private:
  std::vector<std::unique_ptr<Box2dData>> _data;
};

std::unique_ptr<b2WorldWithData> convertSceneToBox2dWorld(
    const ::scene::Scene& scene);

std::unique_ptr<b2WorldWithData> convertSceneToBox2dWorld_with_bounding_boxes(
    const ::scene::Scene& scene);

::scene::Scene updateSceneFromWorld(const ::scene::Scene& scene,
                                    const b2WorldWithData& world);

std::vector<::scene::Body> convertInputToSceneBodies(
    const std::vector<::scene::IntVector>& input_points,
    const std::vector<::scene::Body>& scene_bodies, const unsigned int& height,
    const unsigned int& width);

::scene::Shape p2mShape(const ::scene::Shape& shape);

#endif  // THRIFT_BOX2D_CONVERSION_H
