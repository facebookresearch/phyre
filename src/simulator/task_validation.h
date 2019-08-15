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
#ifndef TASK_VALIDATION_H
#define TASK_VALIDATION_H

#include "gen-cpp/task_types.h"
#include "thrift_box2d_conversion.h"

bool isTaskInSolvedState(const ::task::Task& task,
                         const b2WorldWithData& world);

#endif  // TASK_VALIDATION_H
