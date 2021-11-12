from argparse import ArgumentParser
from pathlib import Path
import signal

from flacmirror.processes import check_requirements
from .queue import JobQueue
from .options import Options


def main():
    codecs = ["vorbis", "opus"]
    argparser = ArgumentParser()
    argparser.add_argument("src_dir")
    argparser.add_argument("dst_dir")
    argparser.add_argument("--codec", type=str, choices=codecs)
    argparser.add_argument(
        "--albumart", type=str, choices=["optimize", "resize", "keep", "discard"]
    )
    argparser.add_argument("--albumart-max-width", type=int, default=750)
    argparser.add_argument("--overwrite", type=str, choices=["all", "none", "old"])
    argparser.add_argument("--delete", action="store_true")
    argparser.add_argument("--copy-files", type=str, default="")
    argparser.add_argument("--num-threads", type=int, default=None)
    argparser.add_argument("--opus-quality", type=float, default=None)
    argparser.add_argument("--vorbis-quality", type=int, default=None)
    arg_results = argparser.parse_args()
    options = Options(
        src_dir=Path(arg_results.src_dir),
        dst_dir=Path(arg_results.dst_dir),
        codec=arg_results.codec,
        albumart=arg_results.albumart,
        albumart_max_width=arg_results.albumart_max_width,
        overwrite=arg_results.overwrite,
        delete=arg_results.delete,
        copy_files=arg_results.copy_files,
        num_threads=arg_results.num_threads,
        opus_quality=arg_results.opus_quality,
        vorbis_quality=arg_results.vorbis_quality,
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
    # job_queue.run_singlethreaded()

    def sig_handler(_signum, _frame):
        job_queue.cancel()

    signal.signal(signal.SIGINT, sig_handler)
    job_queue.run()
