import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from mak.core.album import Album

TEST_ALBUM_1 = "TestAlbum1"
TEST_TRACK_1 = "01 Station To Station.m4a"
TEST_TRACK_2 = "02 Golden Years.m4a"
TEST_TRACK_3 = "03 - The Good Life.mp3"
TEST_TRACK_4 = "04 - Word from Bird.mp3"
TEST_TRACK_5 = "05 Healing The Feeling.mp3"
TEST_TRACK_6 = "06 Singing In The Shower.mp3"

def test_album_init(tmp_path):
    """Test initializing an Album from a directory."""
    # Create a test directory with sample audio files
    album_dir = tmp_path / "test_album"
    album_dir.mkdir()
    
    # Create empty files with audio extensions
    for i, ext in enumerate(['.mp3', '.m4a', '.flac']):
        dummy_file = album_dir / f"track_{i}{ext}"
        dummy_file.write_bytes(b'dummy content')
    
    # Create a non-audio file
    text_file = album_dir / "notes.txt"
    text_file.write_text("album notes")
    
    # This will fail because our dummy files aren't real audio files
    with pytest.raises(ValueError):
        album = Album(album_dir)

def test_album_init_with_real_files(data_dir):
    """Test initializing an Album with real audio files."""
    album_dir = data_dir / TEST_ALBUM_1
    # Skip if data_dir doesn't have enough audio files
    audio_files = list(data_dir.glob("*.mp3")) + list(data_dir.glob("*.m4a")) + list(data_dir.glob("*.flac"))
    if len(audio_files) < 2:
        pytest.skip("Not enough audio files in data_dir for testing")
    
    album = Album(data_dir)
    
    # Check if tracks were loaded
    assert album.get_track_count() > 0
    assert len(album.get_track_names()) == album.get_track_count()
    
    # Try getting a track
    track_name = album.get_track_names()[0]
    track = album.get_track(track_name)
    assert track is not None

def test_album_health(data_dir):
    """Test album health checks."""
    album_dir = data_dir / TEST_ALBUM_1
    
    # Skip if test album directory doesn't exist
    if not album_dir.exists():
        pytest.skip("TestAlbum directory not found in data_dir")
    
    album = Album(album_dir)
    
    # Test album-wide health
    album_health = album.get_album_health()
    assert 'overall' in album_health
    assert album_health['overall'] in ['red', 'amber', 'green']
    assert 'consistency' in album_health
    assert 'album' in album_health['consistency']
    
    # Test track-specific health
    track_health = album.get_track_health()
    assert len(track_health) == album.get_track_count()
    
    # Test a specific track's health
    track_name = album.get_track_names()[0]
    single_track_health = album.get_track_health(track_name)
    assert 'status' in single_track_health
    assert 'issues' in single_track_health

def test_export_selection():
    """Test adding and removing tracks from export selection."""
    # Skip the initialization entirely by creating a minimal Album object
    album = Album.__new__(Album)
    album.tracks = {
        'track1.mp3': MagicMock(),
        'track2.mp3': MagicMock(),
        'track3.mp3': MagicMock()
    }
    album.export_selection = []
    album.get_track_names = lambda: list(album.tracks.keys())
    
    # Test initial state
    assert album.get_export_selection() == []
    
    # Test adding tracks
    pos1 = album.add_to_export('track1.mp3')
    assert pos1 == 0
    assert album.get_export_selection() == ['track1.mp3']
    
    # Test adding at specific position
    pos2 = album.add_to_export('track2.mp3', 0)  # Insert at beginning
    assert pos2 == 0
    assert album.get_export_selection() == ['track2.mp3', 'track1.mp3']
    
    # Test adding track that's already in selection (should move it)
    pos1_new = album.add_to_export('track1.mp3')
    assert pos1_new == 1
    assert album.get_export_selection() == ['track2.mp3', 'track1.mp3']
    
    # Test adding at position beyond end
    pos3 = album.add_to_export('track3.mp3', 10)  # Position too large
    assert pos3 == 2
    assert album.get_export_selection() == ['track2.mp3', 'track1.mp3', 'track3.mp3']
    
    # Test removing track
    result = album.remove_from_export('track1.mp3')
    assert result is True
    assert album.get_export_selection() == ['track2.mp3', 'track3.mp3']
    
    # Test removing track not in selection
    result = album.remove_from_export('track1.mp3')
    assert result is False
    assert album.get_export_selection() == ['track2.mp3', 'track3.mp3']
    
    # Test clear selection
    album.clear_export_selection()
    assert album.get_export_selection() == []
    
    # Test select all
    album.select_all_for_export()
    # The order depends on what get_track_names returns
    assert sorted(album.get_export_selection()) == sorted(['track1.mp3', 'track2.mp3', 'track3.mp3'])
    
    # Test invalid track
    with pytest.raises(KeyError):
        album.add_to_export('nonexistent.mp3')

def test_export_selection_with_real_files(data_dir):
    """Test export selection using real audio files."""
    album_dir = data_dir / TEST_ALBUM_1
    
    # Skip if test album directory doesn't exist
    if not album_dir.exists():
        pytest.skip(f"Test album directory {TEST_ALBUM_1} not found in data_dir")
    
    # Create album from test directory
    album = Album(album_dir)
    
    # Verify tracks are loaded
    track_names = album.get_track_names()
    assert len(track_names) >= 2, "Need at least 2 tracks for this test"
    
    # Test adding tracks to export
    album.add_to_export(TEST_TRACK_1)
    album.add_to_export(TEST_TRACK_3)
    
    selection = album.get_export_selection()
    assert len(selection) == 2
    assert TEST_TRACK_1 in selection
    assert TEST_TRACK_3 in selection
    
    # Test inserting a track at position 0
    album.add_to_export(TEST_TRACK_2, 0)
    selection = album.get_export_selection()
    assert selection[0] == TEST_TRACK_2
    assert len(selection) == 3
    
    # Test removing a track
    album.remove_from_export(TEST_TRACK_3)
    selection = album.get_export_selection()
    assert TEST_TRACK_3 not in selection
    assert len(selection) == 2
    
    # Test clearing selection
    album.clear_export_selection()
    assert len(album.get_export_selection()) == 0
    
    # Test select all
    album.select_all_for_export()
    assert len(album.get_export_selection()) == len(track_names)
    
    # Verify all the track names are in the selection
    for name in track_names:
        assert name in album.get_export_selection()

def test_create_export_zip(data_dir, tmp_path):
    """Test creating a zip file with selected tracks."""
    album_dir = data_dir / TEST_ALBUM_1
    
    # Skip if test album directory doesn't exist
    if not album_dir.exists():
        pytest.skip(f"Test album directory {TEST_ALBUM_1} not found in data_dir")
    
    # Create album from test directory
    album = Album(album_dir)
    
    # Select a couple of tracks for export
    album.add_to_export(TEST_TRACK_1)
    album.add_to_export(TEST_TRACK_3)
    
    # Create a zip file in the temporary directory
    zip_path = tmp_path / "test_export.zip"
    result_path = album.create_export_zip(zip_path)
    
    # Verify the zip file was created
    assert result_path.exists()
    assert result_path == zip_path
    
    # Verify the zip file contains the selected tracks
    import zipfile
    with zipfile.ZipFile(zip_path, 'r') as zipf:
        zip_contents = zipf.namelist()
        assert TEST_TRACK_1 in zip_contents
        assert TEST_TRACK_3 in zip_contents
        assert len(zip_contents) == 2  # Only the selected tracks
    
    # Test with no tracks selected
    album.clear_export_selection()
    with pytest.raises(ValueError):
        album.create_export_zip(tmp_path / "empty_export.zip")
    
    # Test with default output path but using tmp_path as parent
    album.add_to_export(TEST_TRACK_2)
    default_path = album.create_export_zip(parent_dir=tmp_path)
    
    assert default_path.exists()
    assert default_path.name.startswith(TEST_ALBUM_1)
    assert default_path.suffix == ".zip"
    
    # Verify the default zip contains the right track
    with zipfile.ZipFile(default_path, 'r') as zipf:
        assert TEST_TRACK_2 in zipf.namelist()
