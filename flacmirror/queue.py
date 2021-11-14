from subprocess import CalledProcessError
from typing import List, Tuple
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed, CancelledError
import traceback
import os
import shutil

from .encode import encode_flac
from .options import Options
from .files import source_is_newer, get_all_files, generate_output_path


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
    if options.copy_files:
        filename_whitelist = options.copy_files.split(",")
    else:
        filename_whitelist = None
    src_files = get_all_files(
        options.src_dir, extensions=[".flac"], allowed_names=filename_whitelist
    )

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
            suffix=".ogg",
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
    for bla in dst_files_found:
        print(bla)
    for dst_file_found in dst_files_found:
        # If the found dst_file does not exist in the output list, delete it.
        if not any(bytes(f) == bytes(dst_file_found) for f in dst_files):
            jobs_delete.append(JobDelete(dst_file_found))

    return jobs, jobs_delete


class Job:
    def run(self, options: Options):
        pass


class JobEncode(Job):
    def __init__(self, src_file: Path, dst_file: Path):
        self.src_file = src_file
        self.dst_file = dst_file

    def run(self, options: Options):
        print(f"Encoding: {str(self.src_file)}\nOutput  : {str(self.dst_file)}")
        if not options.dry_run:
            self.dst_file.parent.mkdir(parents=True, exist_ok=True)
            encode_flac(self.src_file, self.dst_file, options)


class JobCopy(Job):
    def __init__(self, src_file: Path, dst_file: Path):
        self.src_file = src_file
        self.dst_file = dst_file

    def run(self, options: Options):
        print(f"Copying {str(self.src_file)}\n    to {str(self.dst_file)}")
        if not options.dry_run:
            self.dst_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(str(self.src_file), str(self.dst_file))


class JobDelete(Job):
    def __init__(self, file: Path):
        self.file = file

    def run(self, options: Options):
        assert options.dst_dir.absolute() in self.file.absolute().parents
        print(f"Deleting from dst:{self.file}")
        if not options.dry_run:
            self.file.unlink()


class JobQueue:
    def __init__(self, options: Options):
        self.options = options
        self.jobs, self.jobs_delete = generate_jobs(options)
        self.futures = []

    def run_singlethreaded(self):
        for job in self.jobs:
            job.run(self.options)

    def run(self):
        if self.jobs_delete:
            for job in self.jobs_delete:
                print(f"Marked for deletion: {job.file}")
            while True:
                inp = input(
                    "Warning! The files listed above will be deleted. "
                    "Do you want to proceed? (y/[n]):"
                )
                if inp == "y":
                    break
                elif inp == "n" or inp == "":
                    return
            for job in self.jobs_delete:
                job.run(self.options)

        if self.options.num_threads is not None:
            num_threads = self.options.num_threads
        else:
            num_threads = os.cpu_count()

        with ThreadPoolExecutor(max_workers=num_threads) as e:
            self.futures = [e.submit(job.run, self.options) for job in self.jobs]
            for future in as_completed(self.futures):
                try:
                    future.result()
                except CancelledError:
                    pass
                except CalledProcessError as e:
                    print(f"\nError when calling: {e.cmd}")
                    print(f"Process returned code: {e.returncode}")
                    # print(f"stdout:\n{e.stdout}")
                    print(f"stderr:\n{e.stderr.decode()}")
                    self.cancel()
                    # do not check all the other futures and print their errors
                    break
                except Exception as e:  # pylint: disable=broad-except
                    print("Error:")
                    print(traceback.format_exc())
                    self.cancel()
                    # do not check all the other futures and print their errors
                    break

    def cancel(self):
        print("Stopping pending jobs and finishing running jobs...")
        for future in self.futures:
            # Cancel still pending Futures if we stop early
            future.cancel()
