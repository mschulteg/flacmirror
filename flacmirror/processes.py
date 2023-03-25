import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from flacmirror.options import Options


def check_requirements(options: Options) -> bool:
    print("Checking program requirements:")
    # TODO: this is a dumb way to check requirements - improve
    requirements: List[Process] = []
    if options.albumart in ["resize", "optimize"]:
        requirements.append(ImageMagick(False))
    if options.codec == "vorbis":
        requirements.append(Oggenc(None, False))
        if options.albumart != "discard":
            requirements.append(VorbisComment(False))
    elif options.codec == "opus":
        requirements.append(Opusenc(None, False))
    elif options.codec == "aac":
        requirements.append(FFMPEG(False))
        requirements.append(Fdkaac(1, None, False))
        requirements.append(AtomicParsley(False))
    elif options.codec == "mp3":
        requirements.append(FFMPEG(False))
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
    # TODO: Setting encoding options (see other Process classes) in the constructor
    # is not really optimal; change.
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
        self.loglevel = "info" if debug else "warning"

    def executable_info(self):
        return 'Can be found on most distros as a package "ffmpeg" '

    def extract_picture(self, file: Path) -> Optional[bytes]:
        """exctract coverart into memory (this will keep PNGs as PNGs)"""
        args = [
            self.executable,
            "-loglevel",
            self.loglevel,
            "-nostdin",
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
        try:
            results = subprocess.run(
                args,
                capture_output=True,
                check=True,
                start_new_session=True,
            )
        except subprocess.CalledProcessError as e:
            if (
                b"Output file" in e.stderr
                and b"does not contain any stream" in e.stderr
            ):
                return None
            else:
                raise e from None
        return results.stdout

    def encode_caf(self, file: Path) -> bytes:
        args = [
            self.executable,
            "-loglevel",
            self.loglevel,
            "-nostdin",
            "-i",
            str(file),
            "-f",
            "caf",
            "-",
        ]
        self.print_debug_info(args)
        results = subprocess.run(
            args,
            capture_output=True,
            check=True,
            start_new_session=True,
        )
        return results.stdout

    def resample_caf(
        self,
        input: bytes,
        fs: int,
    ) -> bytes:
        args = [
            self.executable,
            "-loglevel",
            self.loglevel,
            "-nostdin",
            "-fflags",
            "+discardcorrupt",
            "-i",
            "pipe:",
            "-af",
            "aresample=resampler=soxr",
            "-ar",
            str(int(fs)),
            "-f",
            "caf",
            "-",
        ]
        self.print_debug_info(args)
        results = subprocess.run(
            args,
            input=input,
            capture_output=True,
            check=True,
            start_new_session=True,
        )
        return results.stdout

    def encode_lame(
        self,
        input_f: Path,
        output_f: Path,
        image: Optional[bytes],
        discard: bool,
        mode: Optional[str],
        quality: Optional[int],
    ) -> bytes:
        if mode is not None and quality is None:
            raise ValueError("If mode is specified, quality must also be specified.")
        args = [
            self.executable,
            "-y",
            "-loglevel",
            self.loglevel,
            "-nostdin",
            "-i",
            str(input_f),
        ]
        args_keep = ["-map", "0", "-c:v", "copy"]
        args_image = [
            "-i",
            "pipe:",
            "-map",
            "0:a",
            "-map",
            "1:v",
            "-c:v",
            "copy",
            "-metadata:s:v",
            "comment=Cover (front)",
        ]
        args_discard = ["-map", "0:a"]
        args_lame = ["-map_metadata", "0", "-id3v2_version", "3"]
        args_quality = []
        if mode == "cbr" or mode == "abr":
            if mode == "abr":
                args_quality.append("-abr")
                args_quality.append("1")
            # cbr goes from 8 to 320?
            args_quality.append("-b:a")
            args_quality.append(f"{quality}k")
        elif mode == "vbr":
            # vbr goes from 0 to 9
            args_quality.append("-q:a")
            args_quality.append(f"{quality}")

        if image is not None:
            args.extend(args_image)
        elif discard:
            args.extend(args_discard)
        else:
            args.extend(args_keep)
        args.extend(args_lame)
        args.extend(args_quality)
        args.append(str(output_f))

        self.print_debug_info(args)
        results = subprocess.run(
            args,
            input=image,
            capture_output=True,
            check=True,
            start_new_session=True,
        )
        return results.stdout


class Metaflac(Process):
    def __init__(self, debug: bool):
        super().__init__("metaflac", debug)

    def executable_info(self):
        return 'Part of the package "flac" on most distros'

    def extract_picture(self, file: Path) -> Optional[bytes]:
        # extract coverart as jpeg and read it in
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
                start_new_session=True,
            )
        except subprocess.CalledProcessError as e:
            if b"FLAC file has no PICTURE block" in e.stderr:
                return None
            else:
                raise e from None
        return results.stdout

    def extract_tags(self, file: Path) -> Dict[str, str]:
        # extract tags and return them in a dict
        args = [
            self.executable,
            str(file),
            "--export-tags-to",
            "-",
        ]

        self.print_debug_info(args)
        results = subprocess.run(
            args,
            capture_output=True,
            check=True,
            start_new_session=True,
        )
        tags_raw = results.stdout.decode()
        # Workaround since metaflac does not handle multi-line tags well
        # Newlines in multi-line tags are not escaped so we need to guess if we
        # actually have the next key pair value or just the next line of the tag.
        tags: List[Tuple[str, str]] = []
        line_iter = iter(tags_raw.splitlines(keepends=True))
        while True:
            try:
                line = next(line_iter)
            except StopIteration:
                break
            pair = line.split("=", 1)
            try:
                tags.append((pair[0], pair[1]))
            except IndexError:
                # Workaround 2
                # No equal sign, maybe this is the next line of a multi-line tag
                prev_key, prev_value = tags[-1]
                # Append this line to the value of the previous line
                tags[-1] = (prev_key, prev_value + line)
                continue

            # Workaround 1 - if we are lucky, the multiline tag uses Windows newlines
            # which means we can distinguish those \r\n from the unix Newlines \n that
            # come out of Metaflac.
            while line.endswith("\r\n"):
                # This seems to be a multiline comment - consume next line too.
                try:
                    line = next(line_iter)
                except StopIteration:
                    break
                tags[-1] = (pair[0], pair[1] + line)

        # cleanup newlines and convert to dict
        tags_dict = {key: value.strip() for key, value in tags}

        return tags_dict


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
            start_new_session=True,
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
            start_new_session=True,
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
            args,
            capture_output=True,
            check=True,
            start_new_session=True,
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
            args,
            capture_output=True,
            check=True,
            start_new_session=True,
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
            start_new_session=True,
        )


# We need this tool for decoding flac, could also use ffmpeg
class Flac(Process):
    def __init__(self, debug: bool):
        super().__init__("flac", debug)

    def executable_info(self):
        return 'Available as "flac" on most distros'

    def decode_to_memory(self, input_f: Path) -> bytes:
        args = [
            self.executable,
            "-dc",
            str(input_f),
        ]
        self.print_debug_info(args)
        results = subprocess.run(
            args,
            capture_output=True,
            check=True,
            start_new_session=True,
        )
        return results.stdout


class FdkaacUnsupportedSamplerateError(Exception):
    pass


class Fdkaac(Process):
    def __init__(
        self, bitrate_mode: Optional[int], bitrate: Optional[int], debug: bool
    ):
        super().__init__("fdkaac", debug)
        self.additional_args: List[str] = []
        if bitrate_mode is not None:
            if bitrate_mode not in range(6):
                raise ValueError("Invalid bitrate_mode")
            self.additional_args.extend(["--bitrate-mode", f"{bitrate_mode}"])
        else:
            bitrate_mode = 0  # default is 0
        if bitrate is not None:
            if bitrate_mode in range(1, 6):  # if vbr
                raise ValueError("Cannot set bitrate for VBR")
            self.additional_args.extend(["--bitrate", f"{bitrate}"])
        else:  # bitrate not set
            if bitrate_mode == 0:  # if cbr
                raise ValueError("Must set bitrate for CBR")

    def executable_info(self):
        return 'Available as "fdkaac" on most distros'

    def encode_from_mem(self, input: bytes, output_f: Path, tags_file: Optional[Path]):
        args = [
            self.executable,
            *self.additional_args,
            "-",
            "-o",
            str(output_f),
        ]
        if tags_file is not None:
            args.append("--tag-from-json")
            args.append(str(tags_file))
        self.print_debug_info(args)
        try:
            subprocess.run(
                args,
                input=input,
                capture_output=True,
                check=True,
                start_new_session=True,
            )
        except subprocess.CalledProcessError as e:
            if b"unsupported sample rate" in e.stderr:
                raise FdkaacUnsupportedSamplerateError from None
            else:
                raise e from None


class AtomicParsley(Process):
    def __init__(self, debug: bool):
        super().__init__("atomicparsley", debug)
        if not self.available():
            self.executable = "AtomicParsley"

    def executable_info(self):
        return 'Available as "atomicparsley" on most distros'

    def add_artwork(self, file: Path, artwork: Path):
        args = [
            self.executable,
            str(file),
            "--artwork",
            str(artwork),
            "--overWrite",
        ]
        self.print_debug_info(args)
        subprocess.run(
            args,
            capture_output=True,
            check=True,
            start_new_session=True,
        )
