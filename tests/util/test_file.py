"""Test Home Assistant file utility functions."""
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from homeassistant.util.file import WriteError, write_utf8_file


def test_write_utf8_file_private(tmpdir):
    """Test files can be written as 0o600 or 0o644."""
    test_dir = tmpdir.mkdir("files")
    test_file = Path(test_dir / "test.json")

    write_utf8_file(test_file, '{"some":"data"}', False)
    with open(test_file) as fh:
        assert fh.read() == '{"some":"data"}'
    assert os.stat(test_file).st_mode & 0o777 == 0o644

    write_utf8_file(test_file, '{"some":"data"}', True)
    with open(test_file) as fh:
        assert fh.read() == '{"some":"data"}'
    assert os.stat(test_file).st_mode & 0o777 == 0o600


def test_write_utf8_file_fails_at_creation(tmpdir):
    """Test that failed creation of the temp file does not create an empty file."""
    test_dir = tmpdir.mkdir("files")
    test_file = Path(test_dir / "test.json")

    with pytest.raises(WriteError), patch(
        "homeassistant.util.file.tempfile.NamedTemporaryFile", side_effect=OSError
    ):
        write_utf8_file(test_file, '{"some":"data"}', False)

    assert not os.path.exists(test_file)


def test_write_utf8_file_fails_at_rename(tmpdir, caplog):
    """Test that if rename fails not not remove, we do not log the failed cleanup."""
    test_dir = tmpdir.mkdir("files")
    test_file = Path(test_dir / "test.json")

    with pytest.raises(WriteError), patch(
        "homeassistant.util.file.os.replace", side_effect=OSError
    ):
        write_utf8_file(test_file, '{"some":"data"}', False)

    assert not os.path.exists(test_file)

    assert "File replacement cleanup failed" not in caplog.text


def test_write_utf8_file_fails_at_rename_and_remove(tmpdir, caplog):
    """Test that if rename and remove both fail, we log the failed cleanup."""
    test_dir = tmpdir.mkdir("files")
    test_file = Path(test_dir / "test.json")

    with pytest.raises(WriteError), patch(
        "homeassistant.util.file.os.remove", side_effect=OSError
    ), patch("homeassistant.util.file.os.replace", side_effect=OSError):
        write_utf8_file(test_file, '{"some":"data"}', False)

    assert "File replacement cleanup failed" in caplog.text
