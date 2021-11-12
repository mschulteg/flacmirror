from argparse import ArgumentParser
from pathlib import Path
from .queue import JobQueue
from .options import Options


def main():
    argparser = ArgumentParser()
    argparser.add_argument("src_dir")
    argparser.add_argument("dst_dir")
    argparser.add_argument("--codec", type=str, choices=["ogg", "vorbis"])
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
    job_queue = JobQueue(options)
    job_queue.run()
