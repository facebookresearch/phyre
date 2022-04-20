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
#include "task_io.h"

#include <fcntl.h>

#include <cstdio>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <memory>
#include <string>

#include <thrift/protocol/TBinaryProtocol.h>
#include <thrift/transport/TFDTransport.h>
#include "boost/filesystem.hpp"

#include "gen-cpp/shared_types.h"
#include "gen-cpp/task_types.h"
#include "utils/logger.h"

namespace {
using apache::thrift::protocol::TBinaryProtocol;
using apache::thrift::transport::TFDTransport;

const std::string kTaskNameLeftTemplate = "task";
const std::string kTaskNameRightTemplate = ":000.bin";
const std::string kTaskNameTemplate =
    kTaskNameLeftTemplate + "%05d" + kTaskNameRightTemplate;
}  // namespace

std::filesystem::path getTasksPath(const char* taskFolder) {
  const std::filesystem::path task_folder =
      std::filesystem::absolute(std::filesystem::path(taskFolder));
  if (!std::filesystem::exists(task_folder) ||
      !std::filesystem::exists(task_folder)) {
    throw std::runtime_error(
        "task_io is misconfigured. Make sure it's run from the root of the "
        "project,"
        " not from src");
  }
  return task_folder;
}

std::vector<int32_t> listTasks(const char* taskFolder) {
  const auto task_folder = getTasksPath(taskFolder);
  std::vector<int32_t> task_ids;
  std::cout << "Listing " << task_folder.native() << std::endl;
  for (const auto& entry : std::filesystem::directory_iterator(task_folder)) {
    if (entry.is_regular_file()) {
      std::cout << "Found " << entry.path() << std::endl;
      std::string s = entry.path().filename().native();
      s = s.substr(kTaskNameLeftTemplate.size());
      s = s.substr(0, s.size() - kTaskNameRightTemplate.size());
      task_ids.push_back(std::stoi(s));
      std::cout << "Task id: " << std::stoi(s) << std::endl;
    } else {
      std::cout << "Skipping " << entry.path() << std::endl;
    }
  }
  return task_ids;
}

task::Task getTaskFromId(const int32_t pTaskId, const char* taskFolder) {
  std::string filename;
  {
    char buff[100];
    snprintf(buff, sizeof(buff), kTaskNameTemplate.c_str(), pTaskId);
    filename = buff;
  }
  const auto task_folder = getTasksPath(taskFolder);
  const auto file_path = task_folder / filename;

  return getTaskFromPath(file_path.native());
}

task::Task getTaskFromPath(const std::string& file_path) {
  std::cout << "Reading " << file_path << std::endl;
  if (!std::filesystem::exists(file_path)) {
    shared::Error_message msg;
    msg.__set_errorMsg("File doesn't not exist");
    throw shared::Error_message(msg);
  }
  const int fd = open(file_path.c_str(), O_RDONLY);
  std::shared_ptr<TFDTransport> transport(
      new TFDTransport(fd, TFDTransport::CLOSE_ON_DESTROY));
  std::shared_ptr<TBinaryProtocol> protocol(new TBinaryProtocol(transport));
  task::Task task;
  task.read(protocol.get());
  return task;
}

void dumpInputPointsToFile(const std::vector<::scene::IntVector>& input_points,
                           const std::string& filename) {
  std::ofstream outFile(filename);
  int count = 0;
  for (const auto& pt : input_points) {
    outFile << pt.x << "," << pt.y << "\n";
    count++;
  }
  Logger::DEBUG() << count << " points written to file: " << filename << "\n";
}

std::vector<::scene::IntVector> readInputPointsFromFile(
    const std::string& filename) {
  std::vector<::scene::IntVector> points;
  std::ifstream inFile(filename);
  std::string line;
  std::string delimiter = ",";
  int count = 0;
  if (inFile.is_open()) {
    while (getline(inFile, line)) {
      size_t pos = 0;
      if ((pos = line.find(delimiter)) != std::string::npos) {
        ::scene::IntVector v;
        v.__set_x(std::stod(line.substr(0, pos)));
        v.__set_y(std::stod(line.substr(pos + 1, line.size())));
        points.push_back(v);
        count++;
      }
    }
    inFile.close();
  } else {
    Logger::ERROR(Color_value::RED)
        << "Unable to open test file: " << filename << "\n";
  }
  Logger::DEBUG() << "# Input points read from file:" << count << "\n";
  return points;
}
