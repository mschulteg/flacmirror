from pathlib import Path
from typing import List, Optional


def get_files(directory: Path) -> List[Path]:
    files = directory.rglob("*.flac")
    files_filtered = [file for file in files if file.is_file()]
    return list(files_filtered)


def get_all_files(
    directory: Path,
    extensions: Optional[List[str]],
    allowed_names: Optional[List[str]] = None,
) -> List[Path]:
    # return one list with files to be converted and files to be copied interleaved
    matches = directory.rglob("*")
    # is_file() is what makes this slow since it needs to check symlinks too
    files = [match for match in matches if match.is_file()]
    files_filtered: List[Path] = []
    for file in files:
        if extensions is None:
            files_filtered.append(file)
        elif file.suffix and file.suffix[1:] in extensions:
            files_filtered.append(file)
        elif allowed_names is not None and file.name in allowed_names:
            files_filtered.append(file)
    files_absolute = [file.absolute() for file in files_filtered]

    return list(files_absolute)


def generate_output_path(base: Path, input_suffix: str, suffix: str, file: Path):
    if not suffix.startswith("."):
        raise ValueError("Suffix must start with .")
    if file.suffix == input_suffix:
        return base / file.parent / (file.stem + suffix)
    else:
        return base / file.parent / (file.name)


def source_is_newer(src_file: Path, dst_file: Path) -> bool:
    return src_file.lstat().st_mtime >= dst_file.lstat().st_mtime
