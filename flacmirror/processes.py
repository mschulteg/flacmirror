import os
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional, Sequence

from flacmirror.options import Options


# We need this so that the child processes do not catch the signals ...
def preexec_function():
    os.setpgrp()


def check_requirements(options: Options) -> bool:
    print("Checking program requirements:")
    requirements: List[Process] = []
    if options.albumart in ["resize", "optimize"]:
        requirements.append(ImageMagick(False))
    if options.codec == "vorbis":
        requirements.append(Oggenc(None, False))
        if options.albumart != "discard":
            requirements.append(VorbisComment(False))
    elif options.codec == "opus":
        requirements.append(Opusenc(None, False))
    if options.codec != "discard" or (
        options.codec == "vorbis" and options.albumart == "keep"
    ):
        requirements.append(Metaflac(False))

    fulfilled = True
    for req in requirements:
        print(f"    {req.executable_status()}")
        if not req.available():
            fulfilled = False
            print(f"        {req.executable_info()}")
    return fulfilled


class Process:
    def __init__(self, executable: str, debug: bool = False):
        self.executable = executable
        self.debug = debug

    def available(self):
        return shutil.which(self.executable) is not None

    def executable_status(self) -> str:
        available = "\033[92m" + "availble" + "\033[0m"
        unavailable = "\033[91m" + "unavailble" + "\033[0m"
        status = available if self.available() else unavailable
        message = f"{self.executable} ({shutil.which(self.executable)}) [{status}]"
        return message

    def executable_info(self) -> str:
        return ""

    def print_debug_info(self, args: List[str]):
        if self.debug:
            print(f"Calling process: {args}")


class FFMPEG(Process):
    def __init__(self, debug: bool):
        super().__init__("ffmpeg", debug)

    def executable_info(self):
        return 'Can be found on most distros as a package "ffmpeg" '

    def extract_picture(self, file: Path) -> bytes:
        # exctract coverart as jpeg and read it in
        args = [
            self.executable,
            "loglevel",
            "panic",
            "-i",
            str(file),
            "-an",
            "-c:v",
            "copy",
            "-f",
            "mjpeg",
            "-",
        ]
        self.print_debug_info(args)
        results = subprocess.run(
            args,
            capture_output=True,
            check=True,
            preexec_fn=preexec_function,
        )
        return results.stdout


class Metaflac(Process):
    def __init__(self, debug: bool):
        super().__init__("metaflac", debug)

    def executable_info(self):
        return 'Part of the package "flac" on most distros'

    def extract_picture(self, file: Path) -> Optional[bytes]:
        # exctract coverart as jpeg and read it in
        args = [
            self.executable,
            str(file),
            "--export-picture-to",
            "-",
        ]

        self.print_debug_info(args)
        try:
            results = subprocess.run(
                args,
                capture_output=True,
                check=True,
                preexec_fn=preexec_function,
            )
        except subprocess.CalledProcessError as e:
            if b"FLAC file has no PICTURE block" in e.stderr:
                return None
            else:
                raise e from None
        return results.stdout


class ImageMagick(Process):
    def __init__(self, debug: bool):
        super().__init__("convert", debug)

    def executable_info(self):
        return 'Part of the package "imagemagick" on most distros'

    def optimize_picture(self, data: bytes) -> bytes:
        args = [
            self.executable,
            "-",
            "-strip",
            "-interlace",
            "Plane",
            "-sampling-factor",
            "4:2:0",
            "-colorspace",
            "sRGB",
            "-quality",
            "85%",
            "jpeg:-",
        ]
        self.print_debug_info(args)
        results = subprocess.run(
            args,
            capture_output=True,
            check=True,
            input=data,
            preexec_fn=preexec_function,
        )
        return results.stdout

    def optimize_and_resize_picture(self, data: bytes, max_width: int) -> bytes:
        args = [
            self.executable,
            "-",
            "-strip",
            "-interlace",
            "Plane",
            "-sampling-factor",
            "4:2:0",
            "-colorspace",
            "sRGB",
            "-resize",
            f"{max_width}>",
            "-quality",
            "85%",
            "jpeg:-",
        ]
        self.print_debug_info(args)
        results = subprocess.run(
            args,
            capture_output=True,
            check=True,
            input=data,
            preexec_fn=preexec_function,
        )
        return results.stdout


class Opusenc(Process):
    def __init__(self, quality: Optional[float], debug: bool):
        super().__init__("opusenc", debug)
        self.additional_args: List[str] = []
        if quality is not None:
            self.additional_args.extend(["--bitrate", f"{quality}"])

    def executable_info(self):
        return 'Part of the package "opus-tools" on most distros'

    def encode(
        self,
        input_f: Path,
        output_f: Path,
        discard_pictures: bool = False,
        picture_paths: Optional[Sequence[Path]] = None,
    ):
        args = [
            self.executable,
            *self.additional_args,
            str(input_f),
            str(output_f),
        ]
        if discard_pictures:
            args.extend(["--discard-pictures"])
        if picture_paths is not None:
            for picture in picture_paths:
                args.extend(["--picture", f"||||{str(picture)}"])
        self.print_debug_info(args)
        subprocess.run(
            args, capture_output=True, check=True, preexec_fn=preexec_function
        )


class Oggenc(Process):
    def __init__(self, quality: Optional[int], debug: bool):
        super().__init__("oggenc", debug)
        self.additional_args: List[str] = []
        if quality is not None:
            self.additional_args.extend(["--quality", f"{quality}"])

    def executable_info(self):
        return 'Part of the package "vorbis-tools" on most distros'

    def encode(
        self,
        input_f: Path,
        output_f: Path,
    ):
        args = [
            self.executable,
            *self.additional_args,
            str(input_f),
            "-o",
            str(output_f),
        ]
        self.print_debug_info(args)
        subprocess.run(
            args, capture_output=True, check=True, preexec_fn=preexec_function
        )


class VorbisComment(Process):
    def __init__(self, debug: bool):
        super().__init__("vorbiscomment", debug)

    def executable_info(self):
        return 'Part of the package "vorbis-tools" on most distros'

    def add_comment(self, file: Path, key: str, value: str):
        args = [self.executable, str(file), "-R", "-a"]
        self.print_debug_info(args)
        subprocess.run(
            args,
            capture_output=True,
            check=True,
            input=f"{key}={value}".encode(),
            preexec_fn=preexec_function,
        )
