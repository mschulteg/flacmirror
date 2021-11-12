import subprocess
from pathlib import Path
from typing import Optional, Sequence
import shutil


class Process:
    def __init__(self, executable: str):
        self.executable = executable

    def check_executable(self):
        return shutil.which(self.executable) is not None


class FFMPEG(Process):
    def __init__(self):
        super().__init__("ffmpeg")

    def extract_picture(self, file: Path) -> bytes:
        # exctract coverart as jpeg and read it in
        results = subprocess.run(
            [
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
            ],
            capture_output=True,
            check=True,
        )
        return results.stdout


class Metaflac(Process):
    def __init__(self):
        super().__init__("metaflac")

    def extract_picture(self, file: Path) -> bytes:
        # exctract coverart as jpeg and read it in
        results = subprocess.run(
            [
                self.executable,
                str(file),
                "--export-picture-to",
                "-",
            ],
            capture_output=True,
            check=True,
        )
        return results.stdout


class ImageMagick(Process):
    def __init__(self):
        super().__init__("convert")

    def optimize_picture(self, data: bytes) -> bytes:
        results = subprocess.run(
            [
                self.executable,
                "convert",
                "-",
                "-strip",
                "-interlace",
                "Plane",
                "-sampling-factor",
                "4:2:0",
                "-colorspace",
                "RGB",
                "-quality",
                "85%",
                "jpeg:-",
            ],
            capture_output=True,
            check=True,
            input=data,
        )
        return results.stdout

    def optimize_and_resize_picture(self, data: bytes, max_width: int) -> bytes:
        results = subprocess.run(
            [
                self.executable,
                "-",
                "-strip",
                "-resize",
                f"{max_width}>",
                "-interlace",
                "Plane",
                "-sampling-factor",
                "4:2:0",
                "-colorspace",
                "RGB",
                "-quality",
                "85%",
                "jpeg:-",
            ],
            capture_output=True,
            check=True,
            input=data,
        )
        return results.stdout


class Opusenc(Process):
    def __init__(self):
        super().__init__("opusenc")

    def encode(
        self,
        input_f: Path,
        output_f: Path,
        discard_pictures: bool = False,
        picture_paths: Optional[Sequence[Path]] = None,
    ):
        args = [
            "opusenc",
            str(input_f),
            str(output_f),
        ]
        if discard_pictures:
            args.extend(["--discard-pictures"])
        if picture_paths is not None:
            for picture in picture_paths:
                args.extend(["--picture", f"||||{str(picture)}"])
        subprocess.run(args, capture_output=True, check=True)
