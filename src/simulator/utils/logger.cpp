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
#include "logger.h"

using namespace std;

LOG_LEVEL Logger::mLogLevel = LOG_LEVEL::ERROR;
std::ostream* Logger::mOutStream = &(std::cout);
bool Logger::mColorEnabled = true;

std::string getColorHexString(const Color_value& color) {
  switch (color) {
    case Color_value::RED:
      return "\033[1;31m";
    case Color_value::GREEN:
      return "\033[1;32m";
    case Color_value::CYAN:
      return "\033[1;34m";
    case Color_value::BLUE:
      return "\033[1;36m";
    case Color_value::COLOR_END:
      return "\033[0m";
    case Color_value::DEFAULT:
      return "";
    default:
      return "";
  }
}

std::string LogLevelToString(const LOG_LEVEL pLogLevel) {
  switch (pLogLevel) {
    case ERROR:
      return "ERROR";
    case INFO:
      return "INFO";
    case DEBUG:
      return "DEBUG";
    default:
      return "";
  }
}

LOG_LEVEL StrToLogLevel(const std::string& str) {
  if (str == "INFO" || str == "info") {
    return LOG_LEVEL::INFO;
  }
  if (str == "DEBUG" || str == "debug") {
    return LOG_LEVEL::DEBUG;
  }
  return LOG_LEVEL::ERROR;
}
