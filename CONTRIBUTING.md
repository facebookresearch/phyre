# Contributing to PHYRE

The project contains the set of tasks, interface to the simulator, and a
collections of baseline agents. While we would like to keep the API and set
of tasks stable for reproducibility reasons, we are welcome bug fixes and
performance improvements.

## Pull Requests
We actively welcome your pull requests.

1. Fork the repo and create your branch from `master`.
2. If you've added code that should be tested, add tests.
3. Ensure the test suite passes.
4. Make sure your code lints. Use `clang` and `yapf (version 0.28.0)` to automatically format your code.
5. If you haven't already, complete the Contributor License Agreement ("CLA").


## Contributor License Agreement ("CLA")
In order to accept your pull request, we need you to submit a CLA. You only need
to do this once to work on any of Facebook's open source projects.

Complete your CLA here: <https://code.facebook.com/cla>

## Issues
We use GitHub issues for general feature discussion, Q&A and public bugs tracking.
Please ensure your description is clear and has sufficient instructions to be able to
reproduce the issue or understand the problem.

Facebook has a [bounty program](https://www.facebook.com/whitehat/) for the safe
disclosure of security bugs. In those cases, please go through the process
outlined on that page and do not file a public issue.

## Coding Style
We try to follow the [Google style guide](http://google.github.io/styleguide/pyguide.html)
and use [YAPF](https://github.com/google/yapf) to automatically format our Python code.
For C++ code with use `clang-format`. You should run the
`scripts/clang_format.sh` script before you submit.

## License
By contributing to PHYRE, you agree that your contributions will be licensed
under the LICENSE file in the root directory of this source tree.
