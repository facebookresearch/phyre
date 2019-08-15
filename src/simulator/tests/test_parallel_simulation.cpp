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
#include <gtest/gtest.h>
#include <cstdlib>

#include "creator.h"
#include "task_utils.h"

#include "gen-cpp/scene_types.h"
#include "gen-cpp/task_types.h"

const int kWidth = 256;
const int kHeight = 256;

using scene::Body;
using scene::Scene;
using task::Task;
using task::TaskSimulation;

int randint(int max) {
  // Generates integer in {0, 1, ..., max - 1}.
  return static_cast<int>((static_cast<double>(rand()) / RAND_MAX - 1e-6) *
                          max);
}

Scene CreateDemoScene(int seed, bool use_balls = false) {
  srand(seed);
  std::vector<Body> bodies;
  bodies.push_back(buildBox(50, 100, 20, 20));
  bodies.push_back(buildBox(350, 100, 20, 30, 120));

  for (int i = 0; i < 5 + randint(10); ++i) {
    if (use_balls) {
      bodies.push_back(
          buildCircle(20 + 37 * i, 200 + 15 * randint(2), 20 - randint(15)));
    } else {
      bodies.push_back(buildBox(20 + 37 * i, 200 + 15 * randint(2),
                                20 - randint(15), 20 - randint(15), i * 5));
    }
  }

  // Pendulum
  bodies.push_back(buildBox(20, 90, 175, 5));
  bodies.push_back(buildBox(100, 0, 5, 80, 0, false));

  Scene scene;
  scene.__set_width(kWidth);
  scene.__set_height(kHeight);
  scene.__set_bodies(bodies);
  return scene;
}

TEST(ParallelSimulationTest, CheckConsistency) {
  std::vector<Task> tasks;
  for (int i = 0; i < 10; ++i) {
    Task task;
    task.__set_scene(CreateDemoScene(i));
    task.__set_bodyId1(0);
    task.__set_bodyId2(1);
    task.__set_relationships(std::vector<::task::SpatialRelationship::type>{
        ::task::SpatialRelationship::RIGHT_OF});
    tasks.push_back(task);
  }

  const int maxSteps = 100;  // To make the test faster.
  std::vector<TaskSimulation> groundTruthSimulation;
  for (const Task& task : tasks) {
    groundTruthSimulation.push_back(simulateTask(task, maxSteps));
  }

  const std::vector<TaskSimulation> parallelSimulation =
      simulateTasksInParallel(tasks, /*numWorkers=*/3, maxSteps);

  for (size_t i = 0; i < tasks.size(); ++i) {
    ASSERT_EQ(groundTruthSimulation[i], parallelSimulation[i])
        << "Discrepancy at task " << i;
  }
}

TEST(ParallelSimulationTest, CheckConsistencyWithStride) {
  const int stride = 3;
  std::vector<Task> tasks;
  for (int i = 0; i < 10; ++i) {
    Task task;
    task.__set_scene(CreateDemoScene(i));
    task.__set_bodyId1(0);
    task.__set_bodyId2(1);
    task.__set_relationships(std::vector<::task::SpatialRelationship::type>{
        ::task::SpatialRelationship::RIGHT_OF});
    tasks.push_back(task);
  }

  const int maxSteps = 100;  // To make the test faster.
  std::vector<TaskSimulation> groundTruthSimulation;
  for (const Task& task : tasks) {
    groundTruthSimulation.push_back(simulateTask(task, maxSteps, stride));
  }

  const std::vector<TaskSimulation> parallelSimulation =
      simulateTasksInParallel(tasks, /*numWorkers=*/3, maxSteps, stride);

  for (size_t i = 0; i < tasks.size(); ++i) {
    ASSERT_EQ(groundTruthSimulation[i], parallelSimulation[i])
        << "Discrepancy at task " << i;
  }
}
