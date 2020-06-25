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

include "shared.thrift"
include "scene.thrift"

namespace cpp task

typedef shared.Error_message Err_msg,

//SpatialRelationship between 2 TaskObjects
enum SpatialRelationship {
  NONE = 0,
  ABOVE = 1,
  BELOW = 2,
  LEFT_OF = 3,
  RIGHT_OF = 4,
  TOUCHING_BRIEFLY = 5,
  TOUCHING = 6,
  INSIDE = 7,
  NOT_TOUCHING = 8,
  NOT_INSIDE = 9,
}

// This is an atom of actual level database. The whole file is stored on disk.
struct Task {
  1: optional string taskId,
  2: required scene.Scene scene,
  3: required i32 bodyId1,
  4: optional i32 bodyId2,
  5: required list<SpatialRelationship> relationships,
  6: optional string description, //For visualization purpose
  7: optional list< scene.UserInput > solutions,
  8: optional scene.Shape phantomShape,
  9: optional string tier,
}

struct TaskCollection {
  1: optional list<Task> tasks,
}

// Return object from task simulation. Some fields may be missing for
// performance reaons depending on what type of simulation is requested.
struct TaskSimulation {
  // Whether the task was in solved states for 3 seconds.
  1: optional bool isSolution,
  // State of the Scene at each timestamp.
  2: optional list<scene.Scene> sceneList,
  // Whether the task was in solved state at this timestamp.
  3: optional list<bool> solvedStateList,
  // Number of steps simulation ran for. It matches sizes of the lists if
  // stride is 1.
  4: optional i32 stepsSimulated,
}

struct TaskSimulationWithMeta {
  1: optional TaskSimulation simulation,
  2: optional list<string> rendered_imgs,
}

struct Thumb {
  1: optional string img,
  2: optional string extra,
}

struct EvalData {
  1: optional i32 attempts_to_solve_ball,
  2: optional i32 attempts_to_solve_two_balls,
  3: optional i32 attempts_to_solve_ramp,

  7: optional i32 percent_ball,
  8: optional i32 percent_two_balls,
  9: optional i32 percent_ramp,

  4: optional scene.UserInput solution_ball,
  5: optional scene.UserInput solution_two_balls,
  6: optional scene.UserInput solution_ramp,

  10: optional string flag_ball,
  11: optional string flag_two_balls,
  12: optional string flag_ramp,

  13: optional list<string> known_solutions,

  14: optional i32 num_tasks,
}

struct TaskWithMeta {
  1: optional Task task,
  2: optional EvalData eval_data,
  3: optional string template_params,
  4: optional string text_eval_info,
  5: optional string rendered_img,
}


service TaskService {
  // Getters
  map<string, string> list_task_tier_map(1:string task_id_pattern),
  map<string, EvalData> load_evaluation_data(1:string task_id_pattern),
  TaskWithMeta get_task_from_id(1:string task_id) throws (1: Err_msg err),

  list<Thumb> get_task_thumbs(1:list<string> task_ids),

  // Simulate task by id with user input
  TaskSimulationWithMeta simulate_task_by_id(1:string task_id, 2:scene.UserInput user_input, 3:bool dilate),
  // simulate task with the last used user input
  TaskSimulationWithMeta simulate_task_with_last_input(1:Task task),

  void save_solution(1:string task_id, 2:scene.UserInput user_input),

  // Returns the last user input if any.
  scene.UserInput get_last_input(),

  // Returns a solution from an eval file.
  scene.UserInput get_eval_user_input(1:string task_id, 2:string tier_name),

  scene.Image render(1:scene.Scene scene),
}
