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

#include "creator.h"
#include "gen-cpp/task_types.h"
#include "task_io.h"
#include "task_utils.h"

const char* kTestTaskFolder = "src/simulator/tests/test_data/task_validation";

TEST(TaskTest, SimulateTasksWithEmptySolutions) {
  const std::vector<int32_t> taskIds = listTasks(kTestTaskFolder);

  for (const int32_t task_id : taskIds) {
    const task::Task task = getTaskFromId(task_id, kTestTaskFolder);
    const task::TaskSimulation taskSimulation = simulateTask(task, 1000);
    EXPECT_TRUE(taskSimulation.isSolution)
        << "The empty solutions wasn't correct for task " << task_id;
  }
}

TEST(TaskTest, SimulateTouchingRelation) {
  ::scene::Scene scene;
  scene.__set_height(7);
  scene.__set_width(6);
  // A two boxes. The second ball is on the right of the first one and falls
  // touching it.
  const std::vector<::scene::Body> bodies = {
      buildBox(0, 0, 1, 1, 0, false),
      buildBox(1, 2, 1, 1),
  };
  scene.__set_bodies(bodies);
  {
    ::task::Task task;
    task.__set_scene(scene);
    task.__set_bodyId1(0);
    task.__set_bodyId1(1);
    task.relationships.push_back(::task::SpatialRelationship::TOUCHING_BRIEFLY);
    const task::TaskSimulation taskSimulation = simulateTask(task, 1000);
    EXPECT_TRUE(taskSimulation.isSolution)
        << "The empty solutions is expected to be valid for TOUCHING_BRIEFLY";
  }
  {
    ::task::Task task;
    task.__set_scene(scene);
    task.__set_bodyId1(0);
    task.__set_bodyId1(1);
    task.relationships.push_back(::task::SpatialRelationship::TOUCHING);
    const task::TaskSimulation taskSimulation = simulateTask(task, 1000);
    EXPECT_TRUE(!taskSimulation.isSolution)
        << "The empty solutions is expected to be invalid for TOUCHING";
  }
}
