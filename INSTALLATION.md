# Installation via pip

 The simplest way to install PHYRE is via pip. As PHYRE requires Python version 3.6, we recommend installing PHYRE inside a virtual environment, e.g. using [Conda](https://docs.conda.io/en/latest/).

 We provide PHYRE as a pip package for Linux for python version 3.6, 3.7, 3.8, and 3.9.

```(bash)
conda create -n phyre python=3.6  # Or other version.
conda activate phyre
pip install phyre
```

  To check that the installation was successful, run `python -m phyre.server` and open http://localhost:30303. That should start a local demo server.

 # Installation from Source
The recommended way to install and compile PHYRE from source is by using a [Conda](https://docs.conda.io/en/latest/) package manager.


We provide an `env.yml` file that will create a new conda environment with all the dependencies for python=3.6.

 ```(bash)
git clone https://github.com/facebookresearch/phyre.git
cd phyre
conda env create -f env.yml
source activate phyre
pip install -e src/python
```

If you want to install phyre into existing conda environment or would like to use a different version of python than 3.6, you can install the required dependecies manually. Below is an example for python 3.9. 

```(bash)
conda create --yes -n phyre python=3.9
source activate phyre
conda install -c conda-forge sed nodejs=12 thrift-cpp=0.11.0 wget pybind11=2.6 cmake boost=1.75 setuptools pip --yes
pip install matplotlib tqdm ipywidgets yapf==0.28.0

git clone https://github.com/facebookresearch/phyre.git
cd phyre
pip install -e src/python
```

  To check that the installation was successful, run `python -m phyre.server` and open http://localhost:30303. That should start a local demo server.


 # Installation on Docker
We provide a [Dockerfile](Dockerfile) that builds the package in a controlled environment that we used to convey all the experiments for the paper.
While PHYRE is deterministic given an input and binary, due differences in floating point arithmetic across compilers, PHYRE simulations may vary slightly across platforms. [For more details.](https://github.com/erincatto/Box2D/wiki/FAQ#is-box2d-deterministic) In practice, the result of a simulation for a given action on a task is likely to differ across platforms < 0.001% of the time. For maximum consistency, we provide a Dockerfile that mirrors the environment used to train the baselines in the PHYRE paper (link) and produce the solutions and simulation cache distributed with PHYRE.

 You can build the docker image as follows:
```(bash)
git clone https://github.com/facebookresearch/phyre.git
cd phyre
docker build -t phyre -f Dockerfile ./
docker run -it phyre /bin/bash
```
