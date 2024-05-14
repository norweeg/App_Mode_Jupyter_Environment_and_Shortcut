# App Mode Jupyter Environment and Shortcut

Adds a shortcut for running [JupyterLab](https://jupyter.org/) in a Chromium-based browser's "app" mode (i.e. The application takes up the full browser window and has no browser UI e.g. the address bar, as if Jupyter Lab were a native application) for an existing environment with Jupyter Lab installed or creating one for you.  

## Requirements

* An conda-based installation of [Anaconda](https://anaconda.org/), [Miniconda](https://docs.conda.io/en/latest/miniconda.html) or [Miniforge](https://github.com/conda-forge/miniforge).  Miniforge is recommended.
* [`menuinst`](https://conda.github.io/menuinst/) >= 2.0.0 must be installed in the `base` environment alongside `conda` or in whichever environment contains conda
* A Chromium-based browser
  * On Windows, [Google Chrome](https://www.google.com/chrome/), [Brave](https://brave.com/), and [Microsoft Edge](https://www.microsoft.com/en-us/edge) are supported. Preference will be given to the first one of these browsers found.  Microsoft Edge is guaranteed to be installed on Windows 10+ and is a fall-back if no other supported browser is found.
  * On MacOS, [Google Chrome](https://www.google.com/chrome/), [Microsoft Edge](https://www.microsoft.com/en-us/edge), [Brave](https://brave.com/), and [Chromium](https://www.chromium.org/getting-involved/download-chromium/) are preferred in that order.
  * On Linux, [Google Chrome](https://flathub.org/apps/com.google.Chrome), [Microsoft Edge](https://flathub.org/apps/com.microsoft.Edge), [Brave](https://flathub.org/apps/com.brave.Browser), and [Chromium](https://flathub.org/apps/org.chromium.Chromium) are supported and preferred in that order. If [flatpak](https://flatpak.org/) is installed and one of these browsers is installed with Flatpak (recommended), it will be preferred over any snap-installed or package manager-installed versions of any of these browsers.

## Setup

1. Clone or download this repository
2. From a terminal, activate your `base` conda environment (or whichever environment conda is installed in) 
3. Run `python ./setup_jupyter.py your_jupyter_env_name_here`

## Remove Shortcut

To remove the shortcut created by this script, run `python ./setup_jupyter.py --remove your_jupyter_env_name_here`

## FAQ

1. Why don't you support Mozilla Firefox or Safari?
    
    To my knowledge, neither have an "app-mode" like Chromium-based browsers do.  When/if they ever do, they will be supported.

2. Why am I being prompted for admin permissions?

    By default, `menuinst` tries to install/remove the shortcut from a system-level location. You can safely cancel/ignore that prompt(s) (it may prompt you multiple times) which will cause `menuinst` to fallback to a user-specific location instead. Unfortunately, there does not seem to be a way to have `menuinst` prefer to install/remove shortcuts for the current user rather than system-wide. 

3. What about other Chromium-based browsers?

    I added support for what I perceived to be the most popular Chromium-based browsers that I am familiar with in order of my perception of their popularity.  There's just so many of them and it seems like there's always new ones being released! Feel free to open a pull-request to add additional browsers.

4. What about dev/canary builds of the browsers?

    Supporting the dev/canary builds of every browser on every platform would greatly increase the complexity of this code for marginal gains. You should not be using those as your everyday browser and you probably have a stable version of that same browser installed anyway.

5. Why is support for MacOS so buggy?

    The last MacBook that I owned was a 2013 MacBook Air which now runs Linux. While I have attempted to support MacOS as best I can, I am working from my own recollection of using conda-based Python on MacOS combined with whatever I could find on google regarding the MacOS icon format and executing browsers from the CLI. I am not able to actually test this code on MacOS.  I welcome any bug reports (and, hopefully, a pull-request for a fix) for any bugs, especially ones affecting MacOS.

6. What about my existing JupyterLab configuration?

    The `jupyter_lab_config.py` used by the shortcut only sets values for `ServerApp.root_dir` and `ServerApp.browser`. If you have a custom `~/.jupyter/jupyter_lab_config.py` file, its contents are executed at the end of the shortcut's `jupyter_lab_config.py`, adding to or overriding any configuration values set by by it.

7. What is `nb_conda_kernels` and why does this script want to install it in my Jupyter environment.

    `nb_conda_kernels` allows JupyterLab to run kernels in **any** installed conda environment which has a Jupyter kernel (e.g. ipykernel for Python) installed in it without having to install Jupyter and all its dependencies into that conda environment.  It allows you to have a single version of JupyterLab installed in a single, purpose-made environment so you are not maintaining multiple JupyterLab versions or configurations. 

8. How should I update my Jupyter environment?

    That's up to you.  I will periodically run `conda update -n jupyter --all && conda update -n jupyter python` to update everything in my Jupyter environment (named `jupyter`). 
