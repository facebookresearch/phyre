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
#ifndef IMAGE_TO_BOX2D_H
#define IMAGE_TO_BOX2D_H

#include <utility>
#include <vector>

#include "gen-cpp/scene_types.h"

// Clean user input and convert to a list of Body objects.
// Balls are added first as is if they don't occlude with sceneBodies.
// Polygons are added as is if they don't occlude with sceneBodies and balls
// and are convex.
// Points are cleaned, vectorized and then added.
// Several steps of clearning are performed:
// - points outside of scene are removed;
// - points that are inside or close to the sceneBodies are removed;
// - points at the top of the very top of  scene are removed;
// - only points within kMaxUserObjects first connected components are kept.
// Returns true if all objects and points were converted, and false if some
// objects or points were removed.
bool mergeUserInputIntoScene(const ::scene::UserInput& userInput,
                             const std::vector<::scene::Body>& sceneBodies,
                             bool keepSpaceAroundBodies, bool allowOcclusions,
                             int height, int width,
                             std::vector<::scene::Body>* bodies);

inline std::vector<::scene::Body> mergeUserInputIntoScene(
    const ::scene::UserInput& userInput,
    const std::vector<::scene::Body>& sceneBodies, bool keepSpaceAroundBodies,
    bool allowOcclusions, int height, int width) {
  std::vector<::scene::Body> bodies;
  mergeUserInputIntoScene(userInput, sceneBodies, keepSpaceAroundBodies,
                          allowOcclusions, height, width, &bodies);
  return bodies;
}

inline std::vector<::scene::Body> mergeUserInputIntoScene(
    const std::vector<::scene::IntVector>& input_points,
    const std::vector<::scene::Body>& sceneBodies, bool keepSpaceAroundBodies,
    bool allowOcclusions, int height, int width) {
  ::scene::UserInput userInput;
  userInput.flattened_point_list.reserve(input_points.size() * 2);
  for (const auto& p : input_points) {
    userInput.flattened_point_list.push_back(p.x);
    userInput.flattened_point_list.push_back(p.y);
  }
  return mergeUserInputIntoScene(userInput, sceneBodies, keepSpaceAroundBodies,
                                 allowOcclusions, height, width);
}

::scene::Image render(const std::vector<::scene::Body>& sceneBodies,
                      const int height, const int width);

// Renders scene and user bodies from the scene.
::scene::Image render(const ::scene::Scene& scene);

// Renders scene and user bodies from the scene. The buffer has to have at
// least scene.width * scene.height elements.
void renderTo(const ::scene::Scene& scene, uint8_t* buffer);

bool isPointInsideBody(const ::scene::Vector& pPoint,
                       const ::scene::Body& pBody);

// Exposed for testing. Removes points that occludes with bodies in the scene.
std::vector<::scene::IntVector> cleanUpPoints(
    const std::vector<::scene::IntVector>& input_points,
    const std::vector<::scene::Body>& sceneBodies, const unsigned height,
    const unsigned width);

float wrapAngleRadians(float angle);
void featurizeScene(const ::scene::Scene& scene, float* buffer);
void featurizeBody(const ::scene::Body& body, int sceneHeight, int sceneWidth,
                   float* buffer);

#endif  // IMAGE_TO_BOX2D_H
