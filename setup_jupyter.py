#!/bin/env python
import logging
import platform

from argparse import ArgumentParser
from json import JSONDecodeError, loads
from os import PathLike, environ, linesep
from pathlib import Path
from shutil import copy
from subprocess import CalledProcessError, run
from sys import argv, stderr, stdout
from tempfile import TemporaryDirectory
from typing import Union
from urllib.parse import urlparse

from requests import get
from requests.exceptions import RequestException

LOGGER = logging.getLogger(__name__)

class OperationCancelled(Exception):
    pass


def get_current_prefix() -> Path:
    try:
        current_prefix = Path(environ["CONDA_PREFIX"])
    except KeyError:
        try:
            # I vaguely recall MacOS prefixing the conda environment variables with _ for some stupid reason
            current_prefix = Path(environ["_CONDA_PREFIX"])
        except KeyError as e:
            raise RuntimeError("No active conda environment detected. Please activate your base conda environment") from e

    LOGGER.debug(f"Current prefix is {current_prefix}")

    return current_prefix


def get_base_prefix() -> Path:
    try:
        conda_exe = Path(environ["CONDA_EXE"])
    except KeyError:
        try:
            conda_exe = Path(environ["_CONDA_EXE"])
        except KeyError as e:
            raise RuntimeError("No active conda environment detected. Please activate your base conda environment") from e

    LOGGER.debug(f"Base prefix is {conda_exe.parents[1]}")

    # your base environment will be the grandparent of the conda executable
    return conda_exe.parents[1]


def get_menuinst_version() -> tuple[str, str, str]:
    conda_process = run(["conda", "list", "--prefix", str(get_base_prefix()), "--json"], capture_output=True, check=True)

    try:
        conda_pkgs = loads(conda_process.stdout)
    except JSONDecodeError as decode_exception:
        raise JSONDecodeError(f"Error parsing conda output as JSON: {decode_exception}") from decode_exception

    for pkg in conda_pkgs:
        if pkg["name"] == "menuinst":
            break
    else:
        raise RuntimeError("menuinst was not found in the base conda envirionment")

    LOGGER.debug(f"menuinst=={pkg['version']} found")

    return pkg["version"].split(".")


def in_base_env() -> bool:
    return get_current_prefix().samefile(get_base_prefix())


def menuinst_gt_v2_present() -> bool:
    major, minor, patch = get_menuinst_version()

    return (int(major) >= 2) and patch.isnumeric()


def meets_prerequisites() -> bool:
    return in_base_env() and menuinst_gt_v2_present()


def stage_configs(destination_dir: Path) -> Path:
    repo_dir = Path(__file__).parent
    shortcut_json = repo_dir / "jupyterlab_shortcut.json"
    jupyterlab_config = repo_dir / "jupyter_lab_config.py"

    LOGGER.debug(f"Repository directory is {repo_dir}")
    LOGGER.debug(f"menuinst spec json file is {shortcut_json}")
    LOGGER.debug(f"JupyterLab config file is {jupyterlab_config}")
    # download an icon file referenced in shortcut spec json
    download_icon_file(destination_dir)

    if not destination_dir.samefile(repo_dir):
        LOGGER.debug(f"The config files will be staged in {destination_dir}")
        copy(jupyterlab_config, destination_dir)
        copy(shortcut_json, destination_dir)
        return destination_dir / shortcut_json.name
    else:
        LOGGER.debug(f"Repository directory {repo_dir} is already the environment Menu directory.  No need to stage config files")
        return shortcut_json


def download_icon_file(menu_dir: PathLike):
    LOGGER.debug(f"OS is {platform.system()}")
    match platform.system():
        case "Windows":
            url = "https://raw.githubusercontent.com/jupyterlab/jupyterlab-desktop/master/dist-resources/icons/icon.ico"
        case "Linux":
            url = "https://raw.githubusercontent.com/jupyterlab/jupyterlab-desktop/master/dist-resources/icons/512x512.png"
        case "Darwin":
            url = "https://raw.githubusercontent.com/jupyterlab/jupyterlab-desktop/8614277f274b0e9ee9cc550d194e4f02d0c5c3c7/dist-resources/icon.svg"
        case _:
            raise RuntimeError(f"{platform.system()} is not a supported platform")

    try:
        LOGGER.debug(f"Downloading {url} to {menu_dir} for use as shortcut icon")
        response = get(url)
    except RequestException as e:
        raise RuntimeError("Unable to download an icon to use for the JupyterLab shortcut") from e
    else:
        file_extension = Path(urlparse(url).path).suffix
        with (Path(menu_dir) / f"jupyterlab{file_extension}").open("wb") as icon_file:
            LOGGER.debug(f"Writing icon file to {icon_file.name}")
            icon_file.write(response.content)

        if platform.system() == "Darwin" and file_extension == ".svg":
            svg_to_icns(menu_dir/"jupyterlab.svg")


def svg_to_icns(svg_file: PathLike) -> None:
    if not platform.system() == "Darwin":
        raise RuntimeError("svg_to_icns is designed to run on MacOS only")

    svg_file = Path(svg_file)

    if not svg_file.exists():
        raise ValueError(f"{svg_file} does not exist")
    elif not svg_file.is_file():
        raise ValueError(f"{svg_file} exists but is not a file")
    elif not svg_file.suffix == ".svg":
        raise ValueError(f"{svg_file} doesn't seem to be an SVG file")

    target_dir = svg_file.parent

    LOGGER.debug(f"Converting {svg_file} to {svg_file.with_suffix('.icns')}")

    with TemporaryDirectory() as temp_dir:
        iconset_dir = Path(temp_dir)/"jupyterlab.iconset"
        iconset_dir.mkdir(exist_ok=True)

        for size in [2**n for n in range(4, 11)]:
            outfile = iconset_dir/f"icon_{size}x{size}.png"
            try:
                run(
                    [
                        "qlmanage",
                        "-t",
                        "-s",
                        str(size),
                        "-o",
                        str(iconset_dir),
                        str(svg_file)
                    ],
                    capture_output=True,
                    check=True
                )
            except CalledProcessError as e:
                LOGGER.critical(f"Error converting SVG icon to PNG thumbnail iconset with qlmanage")
                raise

            (iconset_dir/svg_file.with_suffix(".svg.png").name).rename(outfile)

            if size > 16:
                copy(outfile, outfile.with_stem(f"icon_{size/2}x{size/2}@2x"))

        try:
            run(
                [
                    "iconutil",
                    "-c",
                    "icns",
                    "-o",
                    str(target_dir/"jupyterlab.icns"),
                    str(iconset_dir)
                ],
                capture_output=True,
                check=True
            )
        except CalledProcessError as e:
            LOGGER.critical(f"Error calling iconutil to create MacOS .icns file from iconset in {iconset_dir}")
            raise

    svg_file.unlink()


def ensure_env(env_name: str) -> Path:
    conda_proc = run(
        [
            "conda",
            "list",
            "--json",
            "--name",
            env_name
        ],
        capture_output=True,
        check=False
    )

    try:
        env_spec = loads(conda_proc.stdout)
    except JSONDecodeError as e:
        raise RuntimeError(f"Error parsing conda output while checking the existance of '{env_name}'") from e
    else:
        env_prefix = get_base_prefix()/f"envs/{env_name}"

        if isinstance(env_spec, dict) and "error" in env_spec.keys():
            # enviornment doesn't exist.  create one with some commonly used packages
            # including ipywidgets because it will automatically install the plugin to render them in jupyterlab
            # ultimately, though, nb_conda_kernels allows the execution of notebooks in any installed conda environment
            # which has `ipykernel` installed
            LOGGER.info(f"Creating new conda enviornment '{env_name}'")
            run(
                [
                    "conda",
                    "create",
                    "--yes",
                    "--name",
                    env_name,
                    "--override-channels",
                    "--channel",
                    "conda-forge",
                    "--no-default-packages",
                    "jupyterlab",
                    "nb_conda_kernels",
                    "nbconvert",
                    "jupyterlab-nbconvert-nocode",
                    "jupyterlab-git",
                    "jupyterlab-lsp",
                    "jupyterlab_code_formatter",
                    "jupyterlab-day",
                    "jupyterlab-night",
                    "jupyterlab_pygments",
                    "black",
                    "isort",
                    "python-lsp-server",
                    "ipykernel",
                    "ipywidgets",
                    "panel",
                    "pandas",
                    "numpy",
                    "scipy",
                    "statsmodels",
                    "openpyxl",
                    "tabulate",
                    "matplotlib",
                    "toolz",
                    "more-itertools",
                    "ipyparallel",
                    "requests",
                    "tqdm",
                    "rich",
                    "rich-with-jupyter",
                    "sqlalchemy",
                ],
                capture_output=False,
                check=True
            )

            # set conda-forge as the one and only channel for this environment
            with open(env_prefix/".condarc", "w") as condarc:
                print(
                    "pip_interop_enabled: true",
                    "channels: [conda-forge]",
                    sep=linesep,
                    end=linesep,
                    file=condarc
                )

        else:
            # add minimal new jupyter packages t existing environment
            pkgs = {pkg["name"] for pkg in env_spec}

            missing_pkgs = {"jupyterlab", "nb_conda_kernels", "ipykernel"} - pkgs

            if missing_pkgs:
                LOGGER.info(f"Installing {'and '.join(missing_pkgs)} in '{env_name}")

                run(
                    [
                        "conda",
                        "install",
                        "--yes",
                        "--name",
                        env_name,
                        *sorted(missing_pkgs)
                    ],
                    capture_output=False,
                    check=True
                )

        (env_prefix/"Menu").mkdir(exist_ok=True)

        return env_prefix


def main(target_env_name: str, remove_shortcut: bool=False) -> Union[int, None]:
    if not in_base_env():
        LOGGER.warning("Not in base environment. Re-running this script from the base environment")

        # I don't know why, but Windows *really* does not want to resolve conda in PATH if you aren't in the base environment
        try:
            conda_exe = environ["CONDA_EXE"]
        except KeyError:
            try:
                conda_exe = environ["_CONDA_EXE"]
            except KeyError:
                conda_exe = "conda"

        # call conda run to re-run this in the base prefix
        rerun_proces = run(
            [conda_exe, "run", "--prefix", str(get_base_prefix()), "--no-capture-output", "python", *argv],
            capture_output=False,
            check=False
        )
        # Surface subprocess return code to parent process
        return rerun_proces.returncode
    elif not menuinst_gt_v2_present():
        if input("This script requires menuinst>=2.0.0.  Would you like to install it and try again? ").lower() in ("y", "yes"):
            run(
                ["conda", "install", "--prefix", str(get_base_prefix()), "menuinst>=2.0.0"],
                capture_output=False,
                check=True
            )

            run(["python", *argv], capture_output=False, check=True)
    elif meets_prerequisites() and remove_shortcut:
        from menuinst.api import remove

        target_prefix = get_base_prefix() / f"envs/{target_env_name}"
        menu_dir = target_prefix / "Menu"

        shortcut_json = menu_dir / "jupyterlab_shortcut.json"
        jupyterlab_config = menu_dir / "jupyter_lab_config.py"
        match platform.system():
            case "Windows":
                icon_file = menu_dir/"jupyterlab.ico"
            case "Linux":
                icon_file = menu_dir/"jupyterlab.png"
            case "Darwin":
                icon_file = menu_dir/"jupyterlab.ico"
            case _:
                raise RuntimeError(f"{platform.system()} is not a supported platform")

        if shortcut_json.is_file():
            LOGGER.debug("Removing JupyterLab shortcut")
            try:
                remove(shortcut_json, target_prefix=target_prefix)
            except:
                pass
            else:
                LOGGER.info("JupyterLab shortcut removed")
        else:
            LOGGER.error(f"Shortcut spec file '{shortcut_json}' does not exist, therefore the shotcut cannot be removed by this script. Please delete it manually")

        if menu_dir.exists() and menu_dir.is_dir():
            LOGGER.debug(f"Cleaning up {target_env_name} environment's Menu directory {menu_dir}")
            jupyterlab_config.unlink(missing_ok=True)
            icon_file.unlink(missing_ok=True)
            shortcut_json.unlink(missing_ok=True)

    elif meets_prerequisites():
        from menuinst.api import install, remove

        target_prefix = ensure_env(target_env_name)

        shortcut_json = stage_configs(target_prefix/"Menu")

        try:
            LOGGER.debug("Removing old shortcut")
            remove(shortcut_json, target_prefix=target_prefix)
        except:
            pass
        finally:
            LOGGER.debug("Creating new shortcut")
            install(shortcut_json, target_prefix=target_prefix)
            LOGGER.info("Jupyter Lab shortcut created!")


if __name__ == "__main__":
    LOGGER = logging.getLogger()

    STDOUT = logging.StreamHandler(stdout)
    STDOUT.setLevel(logging.INFO)
    STDOUT.addFilter(lambda r: r.levelno < logging.WARNING)
    STDOUT.setFormatter(logging.Formatter())

    STDERR = logging.StreamHandler(stderr)
    STDERR.setLevel(logging.WARNING)
    STDERR.setFormatter(
        logging.Formatter(
            "{levelname}: {message}",
            style="{"
        )
    )

    DEBUG_HANDLER = logging.StreamHandler(stderr)
    DEBUG_HANDLER.setLevel(logging.DEBUG)
    DEBUG_HANDLER.addFilter(lambda r: r.levelno < logging.INFO)
    DEBUG_HANDLER.setFormatter(
        logging.Formatter(
            "{levelname}: {message}",
            style="{"
        )
    )

    parser = ArgumentParser()

    parser.add_argument(
        "--debug",
        action = "store_true",
        help = "Enable debug logging to the terminal"
    )
    parser.add_argument(
        "--remove",
        action = "store_true",
        help = "Remove the shortcut created by this script and cleanup environment Menu directory to remove files created by this script"
    )
    parser.add_argument(
        "name",
        help = "Name of the target conda environment containing JupyterLab. If it does not exist, one will be created"
    )

    args = parser.parse_args()

    if args.debug:
        logging.basicConfig(
            level=logging.DEBUG,
            handlers=(STDOUT, STDERR, DEBUG_HANDLER),
        )
    else:
        logging.basicConfig(
            level=logging.INFO,
            handlers=(STDOUT, STDERR),
        )

    logging.captureWarnings(True)

    try:
        logging.info("Creating Jupyterlab shortcut.  This may take a moment...")
        exit(main(args.name, args.remove))
    except CalledProcessError as e:
        # catch any exceptions raised if calling conda returns an unsuccessful return code
        # log exception and suface conda's return code.
        logging.exception(f"'{e.cmd}' failed with exit code {e.returncode}:{linesep * 2}{e. output}")
        exit(e.returncode)
    except (OperationCancelled, KeyboardInterrupt) as e:
        logging.info("Operation cancelled by the user")
        exit(1)
    except Exception as e:
        logging.exception(str(e))
        exit(1)
    finally:
        logging.shutdown()
