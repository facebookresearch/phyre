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
#ifndef UTILS_TIMER_H
#define UTILS_TIMER_H
#include <chrono>

struct SimpleTimer {
  SimpleTimer() { start = std::chrono::steady_clock::now(); }

  double GetSeconds() {
    const auto finish = std::chrono::steady_clock::now();
    const auto counts =
        std::chrono::duration_cast<std::chrono::milliseconds>(finish - start)
            .count();
    const double seconds = static_cast<double>(counts) / 1000;
    start = finish;
    return seconds;
  }

  std::chrono::time_point<std::chrono::steady_clock> start;
};

#endif  // UTILS_TIMER_H
