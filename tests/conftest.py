# Must run BEFORE config.settings is imported: point everything at a throwaway SQLite setup.
import os
import tempfile

_tmp = tempfile.mkdtemp(prefix="dfd_test_")
os.environ.update({
    "DB_BACKEND": "sqlite",
    "SQLITE_DIR": f"{_tmp}/sqlite",
    "LAKE_PATH": f"{_tmp}/lake",
})
