from __future__ import annotations

import functools
import inspect
import logging
import os
import re
import shlex
import shutil
import subprocess
from contextlib import contextmanager
from functools import wraps
from pathlib import Path
from tkinter import Tk, filedialog
from typing import Callable, Sequence, TypeVar, Union
from urllib.parse import urlsplit

import panel as pn
import param

from ecodata.app.assets import get_link_list_html, list_links_html, menu_fast_html
from ecodata.app.config import extension, format_tempalte, DEFAULT_TEMPLATE

Servable = Union[Callable, pn.viewable.Viewable]

IS_WINDOWS = os.name == "nt"
PathLike = TypeVar("PathLike", str, os.PathLike)

links = []

logger = logging.getLogger(__file__)


# all registered apps need to be imported to ecodata.app.apps. this is because
# when the apps dict is imported, then it imports each app,
# which registers them
applications = {}


def param_widget(panel_widget):
    """
    Wrapper utility to create a param.ClassSelector from a panel widget

    Parameters
    ----------
    panel_widget : pn.widgets.Widget
        panel widget

    Returns
    -------
    param.ClassSelector
        param.ClassSelector of the panel widget
    """
    return param.ClassSelector(class_=pn.widgets.Widget, default=panel_widget)


def rename_param_widgets(cls_instance, widgets: list[str]):
    for widget_str in widgets:
        getattr(cls_instance, widget_str).name = getattr(cls_instance.__class__, widget_str).name


def select_file():
    """
    Get filepath from native os GUI file selector, using Tkinter

    Returns
    -------
    str
        filepath selected from the file dialog
    """
    root = Tk()
    root.attributes("-topmost", True)
    root.withdraw()
    f = filedialog.askopenfilename(multiple=False)

    if f:
        return f


def select_output(initial_dir=None, initial_file=None, extension=None):
    """
    Get filepath for output file from native os GUI file selector, using Tkinter

    Parameters
    ----------
    initial_dir : str, optional
        Initial directory opened in the GUI, by default None
    initial_file : str, optional
        Initial filename for the output file, by default None
    extension : str, optional
        Initial extension for the output file, by default None

    Returns
    -------
    str
        filepath for the output file
    """
    root = Tk()
    root.attributes("-topmost", True)
    root.withdraw()
    f = filedialog.asksaveasfilename(initialdir=initial_dir, initialfile=initial_file, defaultextension=extension)
    if f:
        return f


def try_catch(msg="Error... Check options and try again"):
    def inner(func):
        @functools.wraps(func)
        def tru_dec(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except Exception:
                logging.exception(msg)
                self.status_text = msg

        return tru_dec

    return inner


def split_shell_command(cmd: str):
    """
    split shell command for passing to python subproccess.
    This should correctly split commands like "echo 'Hello, World!'"
    to ['echo', 'Hello, World!'] (2 items) and not ['echo', "'Hello,", "World!'"] (3 items)
    It also works for posix and windows systems appropriately
    """
    return shlex.split(cmd, posix=not IS_WINDOWS)


def sanitize_filepath(filepath: str):
    """
    Sanitize filepath string using pathlib.
    Makes sure spaces, special characters, etc are escaped

    Parameters
    ----------
    filepath : str
        File path to sanitize

    Returns
    -------
    str
        Sanitized filepath
    """

    return str(Path(filepath).absolute().resolve())


def make_mp4_from_frames(frames_dir, output_file, frame_rate, start_frame=None, end_frame=None):
    """
    Create an MP4 file from a sequence of frames stored in a directory using ffmpeg.

    This function generates a video file in MP4 format by combining image frames
    following a the naming pattern 'Frame<number>.png' (e.g., Frame1.png, Frame2.png, ...).
    It allows for specifying a range of frames to include through start_frame and end_frame.
    The output video's frame rate can also be defined.

    Parameters
    ----------
    frames_dir : str or Path
        The directory containing the frame images.
    output_file : str or Path
        The path (including filename) for the generated MP4 file. If a relative path is given,
        it is considered relative to `frames_dir`.
    frame_rate : int
        The frame rate (frames per second) of the output video.
    start_frame : int, optional
        The first frame number to include in the video. If None (default), the video will start
        from the first frame found in `frames_dir`.
    end_frame : int, optional
        The last frame number to include in the video. If None (default), the video will include
        all frames up to the last one found in `frames_dir`.

    Returns
    -------
    output_file : Path
        The path to the created MP4 file.

    Raises
    ------
    ValueError
        If no frames matching the file pattern are found in `frames_dir`.

    Notes
    -----
    This function requires ffmpeg to be installed and accessible in the system's PATH.
    The frame images must be named with the pattern 'Frame<number>.png', where <number>
    is a zero-padded integer (e.g., Frame001.png, Frame002.png, ...).

    Examples
    --------
    Create an MP4 video from all frames in the directory './frames' at 24 frames per second:

    >>> make_mp4_from_frames('./frames', 'output_video.mp4', 24)

    Create an MP4 video using frames from 10 to 50 in the directory './frames' at 30 fps:

    >>> make_mp4_from_frames('./frames', 'output_video.mp4', 30, start_frame=10, end_frame=50)
    """

    frames_pattern = "Frame%d.png"
    temp_output_file = "output.mp4"

    frames_dir_sanitized = Path(frames_dir).absolute().resolve()

    frames = list(sorted(frames_dir_sanitized.glob("Frame*.png")))
    print(f"Found {len(frames)} frames in {frames_dir_sanitized}")
    if not frames:
        raise ValueError(f"No frames with file pattern {frames_pattern} found in {frames_dir_sanitized}")

    if start_frame is None:
        start_frame = int(re.search(r"Frame(\d+)", str(frames[0].stem)).group(1))
    if end_frame is None:
        n_frames = len(frames)
    else:
        n_frames = end_frame - start_frame + 1

    if Path(output_file).root == "":
        output_file = frames_dir_sanitized / output_file
    else:
        output_file = Path(sanitize_filepath(output_file))

    with cd_and_cd_back():
        print("Moving to frames directory...")
        os.chdir(frames_dir_sanitized)
        print(f"In directory: {os.getcwd()}")
        cmd = f"""ffmpeg -start_number {start_frame} -framerate {frame_rate} -i {frames_pattern} -frames:v {n_frames}
        -vf pad='width=ceil(iw/2)*2:height=ceil(ih/2)*2' -c:v libx265 -pix_fmt yuv420p -tag:v hvc1
        -y {temp_output_file}"""

        subprocess.run(split_shell_command(cmd))
        print("ffmpeg done!")
        print(f"Target output file: {output_file}")

        shutil.move(temp_output_file, output_file)

    return output_file


def register_view(url=None, name=None, ext_kw=None, ext_args=(), **template_format_kw):
    ext_kw = {} if ext_kw is None else ext_kw
    # grab url of as filename of calling file if not supplied
    url = url or Path(inspect.stack()[1].filename).stem  # file name of calling file
    # grab name for app from url
    name = name or (
        urlsplit(url)
        .path.strip(  # extract path from url (the part after .com, .org, etc
            "/"
        )  # depending on url structure can come with leading / so we remove
        .split("/")[0]  # if path is multipart, we split and only take first (if not this does no change)
        .replace("-", " ")
        .replace("_", " ")  # replace - and _ with space
        .title()
    )

    # create and append links at definition/compile time so all apps have the same links
    link = get_link_list_html({"url": url, "name": name})
    links.append(link)

    def inner(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            # create app and template at run time so that each is a fresh app
            # to prevent bleed over effects where to stack on top of each other
            pn.extension(*ext_args, **ext_kw)
            template = view(*args, **kwargs)
            format_tempalte(template, name=name, **template_format_kw)

            return template.servable()

        applications[url] = wrapper
        return wrapper

    return inner


@contextmanager
def cd_and_cd_back(path: PathLike = None):
    """Context manager that will return to the starting directory
    when the context manager exits, regardless of what directory
    changes happen between start and end.
    Parameters
    ==========
    path
        If supplied, will change directory to this path at the start of the
        context manager (it will "cd" to this path before "cd" back to the
        original directory)
    Examples
    ========
    >>> starting_dir = os.getcwd()
    ... with cd_and_cd_back():
    ...     # with do some things that change the directory
    ...     os.chdir("..")
    ... # When we exit the context manager (dedent) we go back to the starting directory
    ... ending_dir = os.getcwd()
    ... assert starting_dir == ending_dir
    >>> starting_dir = os.getcwd()
    ... path_to_change_to = ".."
    ... with cd_and_cd_back(path=path_to_change_to):
    ...     # with do some things inside the context manager
    ...     ...
    ... # When we exit the context manager (dedent) we go back to the starting directory
    ... ending_dir = os.getcwd()
    ... assert starting_dir == ending_dir
    """
    cwd = os.getcwd()
    try:
        if path:
            os.chdir(path)
        yield
    finally:
        os.chdir(cwd)
