# tests/test_track.py
import pytest
from pathlib import Path
from mak.core.track import AudioTrack

TEST_MP3_1 = "05 - Compute.mp3" # has artwork
TEST_M4A_ALAC_1 = "05 Stay.m4a" # no artwork


def test_set_image(data_dir, tmp_path):
    """Test setting album artwork on an audio file."""
    # Copy a test file to temp directory
    import shutil
    src_file = data_dir / TEST_M4A_ALAC_1
    file_ext = src_file.suffix
    test_file = tmp_path / f"set_image_test{file_ext}"
    shutil.copy(src_file, test_file)
    
    # Create or locate a test image
    test_image = data_dir / "test_image.jpg"
    if not test_image.exists():
        # If no test image exists, create a simple one
        from PIL import Image
        img = Image.new('RGB', (100, 100), color='red')
        img.save(test_file.with_stem("test_image").with_suffix(".jpg"))
        test_image = test_file.with_stem("test_image").with_suffix(".jpg")
    
    # Check initial state
    track = AudioTrack(test_file)
    metadata = track.get_metadata()
    initial_has_image = metadata['has_image']
    
    # Set the image
    track.set_image(test_image).save()
    
    # Check that the image was set
    new_track = AudioTrack(test_file)
    new_metadata = new_track.get_metadata()
    assert new_metadata['has_image'] == True
    
    # If we had a way to extract the image, we could verify it matches
    if hasattr(track, 'extract_image'):
        # Extract the image and compare with original
        extracted_path = tmp_path / "extracted_after_set.jpg"
        track.extract_image(extracted_path)
        
        with open(test_image, 'rb') as f1, open(extracted_path, 'rb') as f2:
            assert f1.read() == f2.read()

                                                       
def test_extract_image(data_dir, tmp_path):
    """Test extracting album artwork from an audio file."""
    # Ensure test file has artwork
    audio_file = data_dir / TEST_MP3_1
    
    # Copy the file to the temporary directory first
    import shutil
    temp_audio = tmp_path / audio_file.name
    shutil.copy(audio_file, temp_audio)
    
    track = AudioTrack(temp_audio)
    metadata = track.get_metadata()
    
    if not metadata['has_image']:
        pytest.skip("Test file doesn't have artwork")
    
    # Extract the image with auto-generated filename
    # This will save in the temp directory since that's where our file is
    saved_path = track.extract_image()
    
    # Verify file was created with appropriate extension
    assert saved_path.exists()
    assert saved_path.suffix in ('.jpg', '.jpeg', '.png')
    assert saved_path.stat().st_size > 0

def test_convert_encoding(data_dir, tmp_path):
    """Test converting audio to a different encoding."""
    import shutil
    src_file = data_dir / TEST_M4A_ALAC_1
    test_file = tmp_path / "encoding_test.m4a"
    shutil.copy(src_file, test_file)
    
    # Get original metadata
    track = AudioTrack(test_file)
    metadata = track.get_metadata()
    assert metadata["encoding"] == "alac"
    
    # Convert to FLAC and save
    output_file = tmp_path / "converted.flac"  # Note the new extension
    track.convert_to_format("flac", output_file_path=output_file)
    
    # Check that the conversion created a new file with the right encoding
    converted_track = AudioTrack(output_file)
    new_metadata = converted_track.get_metadata()
    assert new_metadata["encoding"] == "flac"
    assert new_metadata["file_type"] == "flac"
    
    # Optional: verify the original metadata was preserved
    assert new_metadata["artist"] == metadata["artist"]
    assert new_metadata["album"] == metadata["album"]

def test_set_artist(data_dir, tmp_path):
    """Test setting artist metadata."""
    # Copy test file to temp dir to avoid modifying original
    import shutil
    src_file = data_dir / TEST_MP3_1
    test_file = tmp_path / "artist_test.mp3"
    shutil.copy(src_file, test_file)
    
    # Modify and save
    track = AudioTrack(test_file)
    track.set_artist("New Artist").save()
    
    # Check that the change was saved
    new_track = AudioTrack(test_file)
    metadata = new_track.get_metadata()
    assert metadata["artist"] == "New Artist"

def test_audio_track_metadata(data_dir):
    """Test extracting metadata from an MP3 file."""
    mp3_file = data_dir / TEST_MP3_1
    
    track = AudioTrack(mp3_file)
    metadata = track.get_metadata()
    
    # Check that all expected keys are present
    assert "artist" in metadata
    assert "album" in metadata
    assert "encoding" in metadata
    assert "has_image" in metadata
    
    # Check for expected values
    assert metadata["artist"] == "Pat Metheny/Ornette Coleman"
    assert metadata["album"] == "Song X"
    assert metadata["encoding"] == "mp3"
    assert metadata["file_type"] == "mp3"
    assert metadata["has_image"] is True  # assuming the test file has artwork

def test_get_metadata_nonexistent_file():
    """Test handling of nonexistent files."""
    with pytest.raises(FileNotFoundError):
        AudioTrack("nonexistent_file.mp3")

def test_get_metadata_invalid_file(data_dir):
    """Test handling of invalid audio files."""
    # Create a text file that's not a valid audio file
    invalid_file = data_dir / "invalid.txt"
    invalid_file.write_text("This is not an audio file")
    
    with pytest.raises(ValueError):
        AudioTrack(invalid_file)

def test_get_metadata_image_info(data_dir):
    """Test extracting image metadata from an audio file with artwork."""
    mp3_file = data_dir / TEST_MP3_1
    
    track = AudioTrack(mp3_file)
    metadata = track.get_metadata()
    
    assert metadata["has_image"] is True
    assert metadata["image_info"] is not None
    assert "format" in metadata["image_info"]
    assert "size" in metadata["image_info"]
    
    # For MP3, these should also be present
    if metadata["file_type"] == "mp3":
        assert "type" in metadata["image_info"]
        assert "desc" in metadata["image_info"]
    
    # Check the format is as expected (typically image/jpeg)
    assert metadata["image_info"]["format"] in ["image/jpeg", "image/png"]
