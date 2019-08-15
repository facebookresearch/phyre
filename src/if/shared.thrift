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

namespace cpp shared

exception Error_message {
  1: i32 errorNo,
  2: string errorMsg
}

enum Color {
  WHITE = 0,

  BLACK = 6,
  GRAY = 5,

  GREEN = 2,
  BLUE = 3,
  PURPLE = 4,

  RED = 1,
  // Auxilary colors. Not used for task description.
  LIGHT_RED = 7,
}

// Colors with indices above won't be rendered.
const Color USER_BODY_COLOR = Color.RED