import logging
import platform

from io import StringIO
from itertools import product
from os import environ, pathsep
from pathlib import Path
from re import search
from subprocess import CalledProcessError, run

logging.getLogger(__name__).propagate=True

def find_flatpak_browser():
    if platform.system() != "Linux":
        return

    for path_element in map(Path, environ["PATH"].split(":")):
        if (path_element/"flatpak").is_file():
            flatpak_bin = path_element/"flatpak"
            break
    else:
        # flatpak is not installed
        return

    flatpak_apps = ("com.google.Chrome", "com.microsoft.Edge", "com.brave.Browser", "org.chromium.Chromium")

    try:
        flatpak_process = run(
            [
                str(flatpak_bin),
                "list",
                "--app",
                "--columns=application"
            ],
            capture_output=True,
            check=True
        )
    except CalledProcessError as e:
        pass
    else:
        with StringIO(flatpak_process.stdout.decode()) as flatpak_output:
            installed_flatpaks = flatpak_output.readlines()[1:]

        for flatpak_app in flatpak_apps:
            if flatpak_app in [_.strip() for _ in installed_flatpaks]:
                return f"flatpak run --filesystem={Path.home()/'.local/share/jupyter/runtime'} {flatpak_app} --start-maximized --profile-directory=Default --app=%s"


def find_browser():
    # find a chromium-based browser on the system to use.
    if platform.system() == "Windows":
        from winreg import HKEY_CLASSES_ROOT, OpenKey, QueryValue

        cmds = (
            "Google/Chrome/Application/chrome.exe",
            "BraveSoftware/Brave-Browser/Application/brave.exe",
            "Microsoft/Edge/Application/msedge.exe",
        )
        path_elements = map(Path, (environ["ProgramFiles"], environ["ProgramFiles(x86)"]))

        # do a lookup of default browser command in windows registry
        try:
            with OpenKey(HKEY_CLASSES_ROOT, r"http\shell\open") as k:
                default_browser_cmd = QueryValue(k, "command").replace('"%1"', "").replace('"', "").strip()
        except FileNotFoundError:
            pass
        else:
            # if the command looks like one of the known chromium browsers or even vaguely resembles one, return immediately with a browser command
            if any(default_browser_cmd.endswith(cmd.replace("/", pathsep)) for cmd in cmds) or search(r"\\Application\\\w+\.exe$", default_browser_cmd):
                return f'"{default_browser_cmd}" --start-maximized --profile-directory=Default --app=%s'

    elif platform.system() == "Linux":
        # prefers Google Chrome on Linux due to popularity of the browser
        cmds = ("google-chrome", "microsoft-edge", "brave", "chromium")
        path_elements = map(Path, environ["PATH"].split(":"))

    elif platform.system() == "Darwin":
        # also prefers Google Chrome on MacOS due to popularity of the browser
        cmds = (
            "Contents/MacOS/Google Chrome",
            "Contents/MacOS/Microsoft Edge",
            "Contents/MacOS/Brave Browser",
            "Contents/MacOS/Chromium",
        )
        path_elements = [Path(f"/Applications/{Path(cmd).name}.app") for cmd in cmds]

    # use the first chromium-based browser found as the browser to run Jupyter in app mode
    for cmd, path_element in product(cmds, path_elements):
        browser = path_element / cmd
        if browser.exists():
             return f'"{browser}" --start-maximized --profile-directory=Default --app=%s'


# generated if you run `jupyter lab --generate-config`, used for additional configuration
DEFAULT_CONFIG_FILE = Path.home() / ".jupyter/jupyter_lab_config.py"

# user's home will be the root path of jupyter's file explorer
c.ServerApp.root_dir = str(Path.home())

browser_cmd = find_flatpak_browser() or find_browser()

if browser_cmd:
    c.ServerApp.browser = browser_cmd
else:
    logging.getLogger(__name__).warning(
        "No Chromium-based browser was found on this system, therefore Jupyter will run "
        + "in a new tab of the system-default browser"
    )

# read and exec default config file for additional config/overrides
if DEFAULT_CONFIG_FILE.exists():
    with open(DEFAULT_CONFIG_FILE, "r") as config_file:
        exec(config_file.read())
