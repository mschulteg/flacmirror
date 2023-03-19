from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass
class Options:
    src_dir: Path
    dst_dir: Path
    codec: str
    albumart: str
    albumart_max_width: int
    overwrite: str
    delete: bool
    yes: bool
    copy_file: Optional[List[str]]
    copy_ext: Optional[List[str]]
    num_threads: Optional[int]
    opus_quality: Optional[float]
    vorbis_quality: Optional[int]
    aac_quality: Optional[int]
    aac_mode: Optional[int]
    mp3_quality: Optional[int]
    mp3_mode: Optional[str]
    dry_run: bool
    debug: bool
