#!/usr/bin/env bash

set -e
set -u

DST=$HOME/src/phyre_building_root
module load anaconda3/2020.11


for version in 3.6 3.7 3.8 3.9; do
    vdst=$DST/py$version
    env_name="phyre_tmp_$version"
    if [ -d "$HOME/.conda/envs/$env_name" ]; then
        echo "ENV already exists $env_name"
    else
        conda create --yes -n $env_name python=$version
    fi

    source activate $env_name
    if [ $version = "3.6" ] || [ $version = "3.7" ]; then
        conda install -c conda-forge sed nodejs=12 thrift-cpp=0.11.0 wget pybind11=2.2.4 cmake boost=1.67.0 setuptools pip --yes
    else
        conda install -c conda-forge sed nodejs=12 thrift-cpp=0.11.0 wget pybind11=2.6 cmake boost=1.75 setuptools pip --yes
    fi

    pip install matplotlib tqdm ipywidgets yapf==0.28.0

    mkdir -p $vdst
    cd $vdst
    if [ -d "phyre" ]; then
        echo "repo exists"
    else
        git clone https://github.com/facebookresearch/phyre.git
    fi
    cd phyre
    git checkout readme
    git pull
    pip install -e src/python
    rm -rf src/python/dist
    cd src/python/ &&  python3 setup.py sdist bdist_wheel --plat-name manylinux1_x86_64 --python-tag cp${version//./}

    source deactivate
done


echo twine upload -r testpypi $DST/py*/phyre/src/python/dist/*whl
    