import os
import tempfile
import aiofiles


def create_file(filesystem, ext="txt", is_file=True):
    source = os.path.join(filesystem.name, "mnt")
    ext = ext.lower().removeprefix(".")
    ext = "." + ext
    if is_file:
        f = tempfile.NamedTemporaryFile(mode="w+b", suffix=ext, dir=source)
        f.flush()
    else:
        f = tempfile.TemporaryDirectory(dir=source)

    return f


def contains(folder, file):
    return os.path.basename(file) in os.listdir(folder)
