# Copyright (c) Facebook, Inc. and its affiliates.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Docker file to build phyre on a clean conda.
# Usage:
# docker build -t phyre -f Dockerfile ./ && docker run -i -t -p 30303:30303 phyre
FROM ubuntu:bionic-20190612

ENV PATH /opt/conda/bin:$PATH
ENV PATH /opt/conda/envs/phyre/bin:$PATH
ENV LANG=C.UTF-8 LC_ALL=C.UTF-8

SHELL ["/bin/bash", "-c"]

RUN apt-get update && apt-get install build-essential wget git --yes && apt-get clean

# Installing conda.
RUN wget --quiet https://repo.anaconda.com/miniconda/Miniconda3-4.7.10-Linux-x86_64.sh -O ~/anaconda.sh && \
    mkdir ~/.conda && \
    /bin/bash ~/anaconda.sh -b -p /opt/conda && \
    rm ~/anaconda.sh && \
    ln -s /opt/conda/etc/profile.d/conda.sh /etc/profile.d/conda.sh && \
    echo ". /opt/conda/etc/profile.d/conda.sh" >> ~/.bashrc && \
    echo "conda activate base" >> ~/.bashrc && \
    find /opt/conda/ -follow -type f -name '*.a' -delete && \
    find /opt/conda/ -follow -type f -name '*.js.map' -delete && \
    /opt/conda/bin/conda clean -afy

# Clonning the repo.
ADD / /phyre

# cd /phyre
WORKDIR /phyre

# Installing conda.
RUN conda env create -f env.yml && conda init bash

# Installing the package
RUN apt-get update && apt-get install git --yes && apt-get clean
RUN . /opt/conda/etc/profile.d/conda.sh && conda activate phyre && pip install -e src/python

# Run test.
RUN make test

# Making phyre activated by default.
RUN echo "conda activate phyre" >> ~/.bashrc

# Expose default viz port.
EXPOSE 30303

# Default comand is to run the viz.
CMD python -m phyre.server --port 30303
