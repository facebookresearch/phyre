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
#ifndef TASK_IO_H
#define TASK_IO_H

#include <filesystem>
#include <string>
#include <vector>

#include "gen-cpp/shared_types.h"
#include "gen-cpp/task_types.h"

constexpr char kTaskFolder[] = "data/generated_tasks";

std::filesystem::path getTasksPath(const char* taskFolder);

std::vector<int32_t> listTasks(const char* taskFolder = kTaskFolder);

task::Task getTaskFromId(const int32_t pTaskId,
                         const char* taskFolder = kTaskFolder);

task::Task getTaskFromPath(const std::string& file_path);

void dumpInputPointsToFile(const std::vector<::scene::IntVector>& input_points,
                           const std::string& filename);

std::vector<::scene::IntVector> readInputPointsFromFile(
    const std::string& filename);

#endif  // TASK_IO_H
