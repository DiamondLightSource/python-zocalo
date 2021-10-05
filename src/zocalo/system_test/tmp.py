import datetime
import errno
import os
import stat


def _create_tmp_folder(tmp_folder):
    try:
        os.makedirs(tmp_folder)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise
    try:
        os.chmod(
            tmp_folder,
            stat.S_IRUSR
            | stat.S_IWUSR
            | stat.S_IXUSR
            | stat.S_IRGRP
            | stat.S_IWGRP
            | stat.S_IXGRP
            | stat.S_IROTH
            | stat.S_IWOTH
            | stat.S_IXOTH,
        )
    except OSError as exception:
        if exception.errno != errno.EPERM:
            raise


def tmp_folder(path):
    _create_tmp_folder(path)
    return path


def tmp_folder_date(path):
    _tmp_folder = os.path.join(
        tmp_folder(path), datetime.date.today().strftime("%Y-%m-%d")
    )
    _create_tmp_folder(path)
    return _tmp_folder
