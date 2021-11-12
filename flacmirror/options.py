from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class Options:
    src_dir: Path
    dst_dir: Path
    codec: str
    albumart: str
    albumart_max_width: int
    overwrite: str
    delete: bool
    copy_files: str
    num_threads: Optional[int]
    opus_quality: Optional[float]
    vorbis_quality: Optional[int]
