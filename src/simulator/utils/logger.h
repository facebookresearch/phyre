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
#ifndef LOGGER_H
#define LOGGER_H

#include <iostream>
#include <mutex>
#include <string>
using namespace std;

enum LOG_LEVEL { ERROR = 0, INFO = 1, DEBUG = 2 };

// Color values for printing
enum Color_value {
  DEFAULT = 0,
  RED = 31,
  GREEN = 32,
  BLUE = 34,
  CYAN = 36,
  COLOR_END = -1
};

std::string getColorHexString(const Color_value& color);
LOG_LEVEL StrToLogLevel(const std::string& str);
std::string LogLevelToString(const LOG_LEVEL pLogLevel);

// Threadsafe implementation of Logging using Singleton design pattern
class Logger {
 private:
  static LOG_LEVEL mLogLevel;  // singleton
  // Allows to write in any outstream like cout or file
  static std::ostream* mOutStream;  // singleton
  static bool mColorEnabled;

  // default makes sure these methods are created by only compiler
  Logger() = default;
  ~Logger() = default;
  // Stop compiler from generating the auto-generated methods
  Logger(const Logger&) = delete;
  Logger& operator=(const Logger&) = delete;

 public:
  static void set_log_level(LOG_LEVEL pLogLevel = LOG_LEVEL::ERROR) {
    // "Block static" is the only instance and is thread safe in c++11
    //   Guaranteed to be lazy initialized
    //   Guaranteed that it will be destroyed correctly
    static LOG_LEVEL logLevel = pLogLevel;
    mLogLevel = logLevel;
  }

  static void set_outstream(std::ostream* pStream = &(std::cout)) {
    static std::ostream* outStream = pStream;
    mOutStream = outStream;
    if (outStream->rdbuf() != std::cout.rdbuf()) {
      mColorEnabled = false;
    }
  }

  static LOG_LEVEL get_log_level() { return mLogLevel; }

  class Error {
   private:
    Color_value mColor;

   public:
    Error() { mColor = Color_value::DEFAULT; }
    Error(const Color_value& color) { mColor = color; }
    template <typename T>
    Error& operator<<(const T& data) {
      if (LOG_LEVEL::ERROR <= mLogLevel) {
        if (mColorEnabled) {
          // Only display color values if printing on standard out
          *mOutStream << getColorHexString(mColor) << data
                      << getColorHexString(Color_value::COLOR_END);
        } else {
          *mOutStream << data;
        }
      }
      return *this;
    }
  };
  class Info {
   private:
    Color_value mColor;

   public:
    Info() { mColor = Color_value::DEFAULT; }
    Info(const Color_value& color) { mColor = color; }
    template <typename T>
    Info& operator<<(const T& data) {
      if (LOG_LEVEL::INFO <= mLogLevel) {
        if (mColorEnabled) {
          // Only display color values if printing on standard out
          *mOutStream << getColorHexString(mColor) << data
                      << getColorHexString(Color_value::COLOR_END);
        } else {
          *mOutStream << data;
        }
      }
      return *this;
    }
  };
  class Debug {
   private:
    Color_value mColor;

   public:
    Debug() { mColor = Color_value::DEFAULT; }
    Debug(const Color_value& color) { mColor = color; }
    template <typename T>
    Debug& operator<<(const T& data) {
      if (LOG_LEVEL::DEBUG <= mLogLevel) {
        if (mColorEnabled) {
          // Only display color values if printing on standard out
          *mOutStream << getColorHexString(mColor) << data
                      << getColorHexString(Color_value::COLOR_END);
        } else {
          *mOutStream << data;
        }
      }
      return *this;
    }
  };

 public:
  static Error ERROR() { return Error(); }
  static Error ERROR(const Color_value& color) { return Error(color); }
  static Info INFO() { return Info(); }
  static Info INFO(const Color_value& color) { return Info(color); }
  static Debug DEBUG() { return Debug(); }
  static Debug DEBUG(const Color_value& color) { return Debug(color); }
};

#endif  // LOGGER_H
