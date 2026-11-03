# Must run BEFORE config.settings is imported: point source files at a throwaway test location.
import os
import tempfile

_tmp = tempfile.mkdtemp(prefix="dfd_test_")
os.environ.update({
    "LAKE_PATH": f"{_tmp}/lake",
})
