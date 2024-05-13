# App Mode Jupyter Environment and Shortcut

Adds a shortcut for running Jupyter Lab in a Chromium-based browser's "app" mode (i.e. The application takes up the full browser window and has no browser UI e.g. the address bar, as if Jupyter Lab were a native application) for an existing environment with Jupyter Lab installed or creating one for you.  

## Requirements

* An conda-based installation of [Anaconda](https://anaconda.org/), [Miniconda](https://docs.conda.io/en/latest/miniconda.html) or [Miniforge](https://github.com/conda-forge/miniforge).  Miniforge is recommended.
* [`menuinst`](https://conda.github.io/menuinst/) >= 2.0.0 must be installed in the `base` environment alongside `conda`

## Setup

1. Clone or download this repository
2. From a terminal active in your `base` conda environment (or whichever environment conda is installed in), execute `python ./setup_jupyter.py --name your_jupyter_env_name_here`

