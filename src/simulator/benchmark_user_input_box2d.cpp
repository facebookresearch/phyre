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
#include <cstdio>
#include <cstdlib>

#include <cmath>
#include <functional>
#include <iostream>
#include <memory>
#include <random>
#include <sstream>
#include <utility>
#include <vector>

#include <thrift/protocol/TBinaryProtocol.h>
#include <thrift/transport/TBufferTransports.h>

#include "creator.h"
#include "task_io.h"
#include "task_utils.h"

#include "gen-cpp/scene_types.h"
#include "thrift_box2d_conversion.h"
#include "utils/timer.h"

using ::apache::thrift::protocol::TBinaryProtocol;
using ::apache::thrift::transport::TMemoryBuffer;
using scene::Body;
using scene::IntVector;
using scene::Scene;

constexpr int kNumSteps = kMaxSteps;

const int kWidth = 256;
const int kHeight = 256;
const int kRetries = 3;
const int kUserObjectLimit = 10;

struct Measurement {
  double mean, stddev;
};

// Experiment is a benchmark for a single setup: scene + user input.
// Experiments contains several measurements for different types of simulation.
struct Experiment {
  std::string scene_name, input_name;
  int scene_objects, user_objects, user_points;
  std::vector<Measurement> measurements;
};

int randint(int max) {
  // Generates integer in {0, 1, ..., max - 1}.
  return static_cast<int>((static_cast<double>(rand()) / RAND_MAX - 1e-6) *
                          max);
}

Scene CreateScene(const std::vector<Body>& bodies) {
  Scene scene;
  scene.__set_width(kWidth);
  scene.__set_height(kHeight);
  scene.__set_bodies(bodies);
  return scene;
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

  return CreateScene(bodies);
}

inline Scene simulate(const Scene& scene, const int32_t num_steps) {
  auto world = convertSceneToBox2dWorld(scene);
  for (int32_t i = 0; i < num_steps; i++) {
    world->Step(kTimeStep, kVelocityIterations, kPositionIterations);
  }
  return updateSceneFromWorld(scene, *world);
}

Measurement timeIt(std::function<void()> callback, int retries) {
  std::vector<double> times;
  double total_time = 0;
  callback();
  for (int i = 0; i < retries; ++i) {
    SimpleTimer timer;
    callback();
    times.push_back(timer.GetSeconds());
    total_time += times.back();
  }
  const double mean = total_time / retries;
  double varsum = 0;
  for (double t : times) varsum += (t - mean) * (t - mean);
  const double stddev = std::sqrt(varsum / std::max(retries - 1, 1));
  return Measurement{mean, stddev};
}

Experiment runExperiment(const std::string& scene_name,
                         const std::string& input_name, const Scene& scene,
                         const std::vector<IntVector>& userInput) {
  std::cout << "## scene=" << scene_name << " input=" << input_name
            << std::endl;
  std::cout << "Scene has " << scene.bodies.size() << " objects" << std::endl;
  std::cout << "User input has " << userInput.size() << " points" << std::endl;
  Scene sceneWithUserInput = scene;
  {
    const auto userBodies = mergeUserInputIntoScene(
        userInput, scene.bodies, /*keep_space_around_bodies=*/true,
        /*allow_occlusions=*/false, scene.height, scene.width);
    sceneWithUserInput.__set_user_input_bodies(userBodies);
  }
  Scene sceneWithLimitedUserInput = scene;
  {
    const auto& allBodies = sceneWithUserInput.user_input_bodies;
    const std::vector<Body> bodies(
        allBodies.begin(),
        allBodies.begin() +
            std::min<size_t>(allBodies.size(), kUserObjectLimit));
    sceneWithLimitedUserInput.__set_user_input_bodies(bodies);
  }
  std::cout << "User input has " << sceneWithUserInput.user_input_bodies.size()
            << " objects" << std::endl;
  std::vector<Measurement> measurements;
  measurements.push_back(
      timeIt([=]() { simulate(scene, kNumSteps); }, kRetries));
  measurements.push_back(timeIt(
      [=]() {
        mergeUserInputIntoScene(userInput, scene.bodies,
                                /*keep_space_around_bodies=*/true,
                                /*allow_occlusions=*/false, scene.height,
                                scene.width);
      },
      kRetries));
  measurements.push_back(
      timeIt([=]() { simulate(sceneWithUserInput, kNumSteps); }, kRetries));
  measurements.push_back(timeIt(
      [=]() { simulate(sceneWithLimitedUserInput, kNumSteps); }, kRetries));
  measurements.push_back(
      timeIt([=]() { simulateScene(sceneWithLimitedUserInput, kNumSteps); },
             kRetries));

  Experiment experiment;
  experiment.scene_name = scene_name;
  experiment.input_name = input_name;
  experiment.measurements = measurements;
  experiment.scene_objects = scene.bodies.size();
  experiment.user_objects = sceneWithUserInput.user_input_bodies.size();
  experiment.user_points = userInput.size();

  printf("--->\t");
  for (const Measurement& m : measurements) {
    printf("%.3lfs +- %.1lf%%\t", m.mean,
           m.stddev / std::max(m.mean, 1e-6) * 100);
  }
  printf("\n");
  return experiment;
}

std::vector<IntVector> buildRandomInput(int seed, int n) {
  std::srand(seed);
  std::vector<IntVector> result;
  for (int i = 0; i < n; ++i) {
    int x = randint(kWidth);
    int y = randint(kHeight);
    result.push_back(getIntVector(x, y));
  }
  {
    std::sort(result.begin(), result.end(), cmpIntVector);
    auto it = std::unique(result.begin(), result.end());
    result.resize(std::distance(result.begin(), it));
  }
  return result;
}

int main(int argc, char** argv) {
  std::cout << "Total steps: " << kNumSteps << "\n";
  std::vector<IntVector> fullInput;
  for (int i = 0; i < kWidth * kHeight; ++i) {
    fullInput.push_back(getIntVector(i % kWidth, i / kWidth));
  }

  std::vector<std::pair<std::string, ::scene::Scene>> stdScenes = {
      {"empty", CreateScene({})},
      {"boxes", CreateDemoScene(0, false)},
      {"boxNballs", CreateDemoScene(0, true)}};

  std::vector<Experiment> experiments;
  for (int n : {20, 200, 500, 2000, 4000}) {
    for (const auto& s : stdScenes) {
      experiments.push_back(runExperiment(s.first, "random" + std::to_string(n),
                                          s.second, buildRandomInput(0, n)));
    }
  }
  experiments.push_back(
      runExperiment("empty", "full", CreateScene({}), fullInput));
  experiments.push_back(
      runExperiment("boxes", "full", CreateDemoScene(1), fullInput));
  const Scene scene48 =
      getTaskFromPath("src/simulator/tests/test_data/benchmark/task00048.bin")
          .scene;

  experiments.push_back(runExperiment("task48", "random2000", scene48,
                                      buildRandomInput(0, 2000)));
  experiments.push_back(runExperiment("task48", "full", scene48, fullInput));

  printf(
      "    scene\tobjs\tuser_input\tobjs\tpoints\tsim_scene\tvectorize"
      "\t  sim_all\tsim_all_%dobjs\tsim_intermid_%dobjs\n",
      kUserObjectLimit, kUserObjectLimit);
  for (const Experiment& experiment : experiments) {
    printf("%10s\t%d\t%10s\t%d\t%d\t%8.3lf\t%8.3lf\t%8.3lf\t%8.3lf\t%8.3lf\n",
           experiment.scene_name.c_str(), experiment.scene_objects,
           experiment.input_name.c_str(), experiment.user_objects,
           experiment.user_points, experiment.measurements[0].mean,
           experiment.measurements[1].mean, experiment.measurements[2].mean,
           experiment.measurements[3].mean, experiment.measurements[4].mean);
  }

  return 0;
}
