import os
import pytest
import shutil
import tempfile

from pathlib import Path

@pytest.fixture
def data_dir():
    """Return the path to the sample files directory."""
    return Path(__file__).parent / "sample_data"

@pytest.fixture
def temp_dir():
    """Create a temporary directory for file operations."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)
