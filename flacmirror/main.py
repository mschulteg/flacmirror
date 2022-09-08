import argparse
import signal
from pathlib import Path

from flacmirror.processes import check_requirements

from . import __version__
from .options import Options
from .queue import JobQueue


def main():
    codecs = ["vorbis", "opus"]
    argparser = argparse.ArgumentParser(
        prog="flacmirror",
        description=(
            "Program to recursively synchronize a directory containing flac files to"
            " another directory while encoding the flac files instead of copying them."
        ),
        formatter_class=lambda prog: argparse.HelpFormatter(
            prog, max_help_position=48, width=120
        ),
    )
    argparser.add_argument(
        "src_dir",
        help=(
            "The source directory. This directory will be recursively scanned for flac"
            " files to be encoded."
        ),
    )
    argparser.add_argument(
        "dst_dir",
        help=(
            "The destination directory. Encoded files will be saved here using the same"
            " directory structure as in src_dir."
        ),
    )
    argparser.add_argument(
        "--codec",
        type=str,
        choices=codecs,
        help="Specify which target codec to use.",
    )
    argparser.add_argument(
        "--opus-quality",
        type=float,
        default=None,
        help=(
            "If opus encoding was selected, the bitrate in kbit/s can be specified as a"
            " float. The value is direclty passed to the --bitrate argument of opusenc."
        ),
    )
    argparser.add_argument(
        "--vorbis-quality",
        type=int,
        default=None,
        help=(
            "If vorbis encoding was selected, the quality can be specified as an"
            " integer between -1 and 10. The value is directly passed to the --quality"
            " argument of oggenc."
        ),
    )
    argparser.add_argument(
        "--albumart",
        type=str,
        default="optimize",
        choices=["optimize", "resize", "keep", "discard"],
        help=(
            "Specify what to do with album covers. Defaults to 'optimize'. 'optimize'"
            " will try to optimize the picture for better size, while 'resize' will"
            " additionally downsample pictures with a pixel width greater than"
            " --albumart-max-width (default 750) while scaling the height"
            " proportionally. 'keep' will just copy the album art over to the new file,"
            " while 'discard' will not add the album art to the encoded file."
        ),
    )
    argparser.add_argument(
        "--albumart-max-width",
        type=int,
        default=750,
        help=(
            "Specify the width in pixels to which album art is downscaled to (if"
            " greater). Defaults to 750. Only used when --albumart is set to resize."
        ),
    )
    argparser.add_argument(
        "--overwrite",
        type=str,
        default="old",
        choices=["all", "none", "old"],
        help=(
            "Specify if or when existing files should be overwritten. 'all' means that"
            " files are always overwritten, 'none' means that files are never"
            " overwritten and 'old' means that files are only overwritten if the source"
            " file has changed since (the source file's modification date is newer)."
        ),
    )
    argparser.add_argument(
        "--delete",
        action="store_true",
        help="Delete files that exist at the destination but not the source.",
    )
    argparser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Skip any prompts that require you to press [y] (--delete)",
    )
    argparser.add_argument(
        "--copy-file",
        type=str,
        action="append",
        help=(
            "Copy additional files with filename COPY_FILE that are not being encoded."
            " This option can be used multiple times. For example --copy-file cover.jpg"
            " --copy-file album.jpg"
        ),
    )
    argparser.add_argument(
        "--copy-ext",
        type=str,
        action="append",
        help=(
            "Copy additional files with the extension COPY_EXT that are not being encoded."
            " This option can be used multiple times. For example --copy-ext m3u"
            " --copy-ext log --copy-ext jpg. This will not copy flac files."
        ),
    )
    argparser.add_argument(
        "--num-threads",
        type=int,
        default=None,
        help=(
            "Number of threads to use. Defaults to the number of threads in the system."
        ),
    )
    argparser.add_argument(
        "--dry-run",
        action="store_true",
        help="Do a dry run (do no copy, encode, delete any file)",
    )
    argparser.add_argument(
        "--debug",
        action="store_true",
        help="Give more output about how subcommands are called",
    )
    argparser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    arg_results = argparser.parse_args()
    options = Options(
        src_dir=Path(arg_results.src_dir),
        dst_dir=Path(arg_results.dst_dir),
        codec=arg_results.codec,
        albumart=arg_results.albumart,
        albumart_max_width=arg_results.albumart_max_width,
        overwrite=arg_results.overwrite,
        delete=arg_results.delete,
        yes=arg_results.yes,
        copy_file=arg_results.copy_file,
        copy_ext=arg_results.copy_ext,
        num_threads=arg_results.num_threads,
        opus_quality=arg_results.opus_quality,
        vorbis_quality=arg_results.vorbis_quality,
        dry_run=arg_results.dry_run,
        debug=arg_results.debug,
    )

    if options.codec not in codecs:
        print("Please specify a codec")
        print(f"Available codecs are: {codecs}")
        return

    # make sure we have all the programs installed
    if not check_requirements(options):
        print(
            "Not all requirements are met, make sure that tools marked "
            "as unavailable are installed correctly"
        )
        return

    job_queue = JobQueue(options)

    def sig_handler(_signum, _frame):
        print("\nReceived SIGINT")
        job_queue.cancel()

    signal.signal(signal.SIGINT, sig_handler)
    job_queue.run()
