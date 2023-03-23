import datetime
import os
import shutil
import traceback
from concurrent.futures import CancelledError, ThreadPoolExecutor, as_completed
from pathlib import Path
from subprocess import CalledProcessError
from typing import TYPE_CHECKING, List, Tuple

from flacmirror.misc import format_date

from .encode import encode_flac
from .files import generate_output_path, get_all_files, source_is_newer
from .options import Options

if TYPE_CHECKING:
    from concurrent.futures import Future


def job_required(src_file: Path, dst_file: Path, options: Options) -> bool:
    if not dst_file.exists():
        return True
    else:
        if options.overwrite == "all":
            return True
        elif options.overwrite == "old":
            if source_is_newer(src_file, dst_file):
                return True
    return False


def generate_jobs(options: Options) -> Tuple[List["Job"], List["JobDelete"]]:
    extensions = ["flac"]
    if options.copy_ext is not None:
        for ext in options.copy_ext:
            if ext.startswith("."):
                ext = ext[1:]
            extensions.append(ext)
    src_files = get_all_files(
        options.src_dir, extensions=extensions, allowed_names=options.copy_file
    )
    # Select output extension depending on which codec is used
    # .ogg also works for opus but some players don't like that so we just use opus
    if options.codec == "opus":
        out_suffix = ".opus"
    elif options.codec == "vorbis":
        out_suffix = ".ogg"
    elif options.codec == "aac":
        out_suffix = ".m4a"
    else:  # if options.codec == "mp3"
        out_suffix = ".mp3"

    # Keep list of valid dst files even if there is no encode or copy job for them.
    # This list is used to check which files need to be deleted.
    dst_files: List[Path] = []
    # We want copy jobs to be interleaved with encode jobs.
    # Deletion jobs should get their own joblist.
    jobs: List["Job"] = []
    for src_file in src_files:
        src_file_relative = src_file.relative_to(options.src_dir.absolute())
        dst_file = generate_output_path(
            base=options.dst_dir.absolute(),
            input_suffix=".flac",
            suffix=out_suffix,
            file=src_file_relative,
        )
        dst_files.append(dst_file)
        if job_required(src_file, dst_file, options):
            # copy or encode?
            if src_file.suffix == ".flac":
                jobs.append(JobEncode(src_file, dst_file))
            else:
                jobs.append(JobCopy(src_file, dst_file))

    if not options.delete:
        return jobs, []

    jobs_delete = []
    # Get a dst_files list that we can match against src_files
    dst_files_found = get_all_files(options.dst_dir, extensions=None)
    dst_files_set = set(bytes(dst_file) for dst_file in dst_files)
    for dst_file_found in dst_files_found:
        # If the found dst_file does not exist in the output list, delete it.
        if bytes(dst_file_found) not in dst_files_set:
            jobs_delete.append(JobDelete(dst_file_found))

    return jobs, jobs_delete


class Job:
    def run(self, options: Options):
        pass

    def job_info(self) -> str:
        """Info that identifies the job in case of error"""
        return ""


class JobEncode(Job):
    def __init__(self, src_file: Path, dst_file: Path):
        self.src_file = src_file
        self.dst_file = dst_file

    def run(self, options: Options):
        print(f"Encoding: {str(self.src_file)}\nOutput  : {str(self.dst_file)}")
        if not options.dry_run:
            self.dst_file.parent.mkdir(parents=True, exist_ok=True)
            encode_flac(self.src_file, self.dst_file, options)

    def job_info(self) -> str:
        """Info that identifies the job in case of error"""
        return str(self.src_file)


class JobCopy(Job):
    def __init__(self, src_file: Path, dst_file: Path):
        self.src_file = src_file
        self.dst_file = dst_file

    def run(self, options: Options):
        print(f"Copying {str(self.src_file)}\n    to {str(self.dst_file)}")
        if not options.dry_run:
            self.dst_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(str(self.src_file), str(self.dst_file))

    def job_info(self) -> str:
        """Info that identifies the job in case of error"""
        return str(self.src_file)


class JobDelete(Job):
    def __init__(self, file: Path):
        self.file = file

    def run(self, options: Options):
        assert options.dst_dir.absolute() in self.file.absolute().parents
        print(f"Deleting from dst:{self.file}")
        if not options.dry_run:
            self.file.unlink()

    def job_info(self) -> str:
        """Info that identifies the job in case of error"""
        return str(self.file)


class JobQueue:
    def __init__(self, options: Options):
        self.options = options
        print("Scanning files and calculating jobs...")
        self.jobs, self.jobs_delete = generate_jobs(options)
        self.futures: List["Future[None]"] = []

    def run_singlethreaded(self):
        for job in self.jobs:
            job.run(self.options)

    def run(self):
        start_time = datetime.datetime.now()
        if self.jobs_delete:
            for job in self.jobs_delete:
                print(f"Marked for deletion: {job.file}")
            if not self.options.yes:
                # prompt to ask for permission to delete
                while True:
                    inp = input(
                        "Warning! The files listed above will be deleted. "
                        "Do you want to proceed? (y/[n]):"
                    )
                    if inp == "y":
                        break
                    elif inp == "n" or inp == "":
                        return
            print("Deleting...")
            for job in self.jobs_delete:
                job.run(self.options)

        if self.options.num_threads is not None:
            num_threads = self.options.num_threads
        else:
            num_threads = os.cpu_count()

        print("Running copy/encode jobs...")
        with ThreadPoolExecutor(max_workers=num_threads) as ex:
            self.futures = [ex.submit(job.run, self.options) for job in self.jobs]
            for future in as_completed(self.futures):
                try:
                    future.result()
                except CancelledError:
                    pass
                except CalledProcessError as err:
                    print(f"\nError when calling: {err.cmd}")
                    print(f"Process returned code: {err.returncode}")
                    # print(f"stdout:\n{e.stdout}")
                    print(f"stderr:\n{err.stderr.decode()}")
                    self.cancel()
                    # do not check all the other futures and print their errors
                    break
                except Exception:
                    job = self.jobs[self.futures.index(future)]  # lookup job
                    print(f"\nError processing file {job.job_info()}:")
                    print(traceback.format_exc())
                    self.cancel()
                    # do not check all the other futures and print their errors
                    break
        stop_time = datetime.datetime.now()
        print(f"All jobs done. Took {format_date(stop_time - start_time)}.")

    def cancel(self):
        print("Stopping pending jobs and finishing running jobs...")
        for future in self.futures:
            # Cancel still pending Futures if we stop early
            future.cancel()
