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
#ifndef TASK_UTILS_H
#define TASK_UTILS_H

#include <vector>

#include "gen-cpp/scene_types.h"
#include "gen-cpp/task_types.h"

constexpr unsigned kObjectFeatureSize = 14;
constexpr unsigned kNumColors = 6;
constexpr unsigned kNumShapes = 4;
constexpr unsigned kFps = 60;
constexpr float kTimeStep = 1.0f / kFps;
constexpr unsigned kVelocityIterations = 15;
constexpr unsigned kPositionIterations = 20;
// For how many steps the task condition should be satisfied for a task to be
// considered as solved. Note, that if the task started from a solved solution,
// then it either has to remain in this state thougout the whole simulation or
// go through non-solved states.
constexpr unsigned kStepsForSolution = 3 * kFps;
// Default value for the miximum number of simulation steps.
constexpr unsigned kMaxSteps = 1000;

// Runs simulation for num_steps and returns every scene.
std::vector<::scene::Scene> simulateScene(const ::scene::Scene& scene,
                                          const int num_steps);

// Runs simulation for at most num_steps. The sumlation is stopped earlier if
// the task is in the solved state for at least kStepsForSolution steps.
// Returns every stride scene starting from the first one. Note, for big enough
// stride there is no guarantee that the last sscene in the solved state.
::task::TaskSimulation simulateTask(const ::task::Task& task,
                                    const int num_steps, const int stride = 1);

// Run simulation in parallel using worker pool of num_workers processes.
std::vector<::task::TaskSimulation> simulateTasksInParallel(
    const std::vector<::task::Task>& tasks, const int num_workers,
    const int num_steps, const int stride = 1);

#endif  // TASK_UTILS_H
