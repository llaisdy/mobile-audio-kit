from pathlib import Path
import mutagen
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4
from mutagen.flac import FLAC
from .handlers import AudioFormatHandler, MP3Handler, MP4Handler, FLACHandler

class AudioTrack:
    def __init__(self, filename):
        """
        Initialize an AudioTrack object.
        
        Args:
            filename: Path to the audio file
        
        Raises:
            FileNotFoundError: If the file doesn't exist
            ValueError: If the file isn't a valid audio file
        """
        self.filepath = Path(filename)
        if not self.filepath.exists():
            raise FileNotFoundError(f"File not found: {filename}")
        
        self.audio = mutagen.File(self.filepath)
        if self.audio is None:
            raise ValueError(f"Could not read audio file: {filename}")
        
        # Store file type
        self.file_type = self.filepath.suffix.lower().lstrip('.')
        
        # Select appropriate handler
        if isinstance(self.audio, MP3):
            self.handler = MP3Handler()
        elif isinstance(self.audio, MP4):
            self.handler = MP4Handler()
        elif isinstance(self.audio, FLAC):
            self.handler = FLACHandler()
        else:
            self.handler = AudioFormatHandler()
    
    def get_metadata(self):
        """
        Extract metadata from the audio file.
        
        Returns:
            dict: Dictionary containing metadata
        """
        metadata = {
            'file_type': self.file_type,
            'encoding': self.handler.get_encoding(self.audio),
            'artist': self.handler.get_artist(self.audio),
            'album': self.handler.get_album(self.audio),
            'has_image': self.handler.has_image(self.audio),
            'image_info': self.handler.get_image_info(self.audio)
        }
        return metadata
    
    def set_artist(self, value):
        """Set artist metadata for the track."""
        self.handler.set_artist(self.audio, value)
        return self
    
    def set_album(self, value):
        """Set album metadata for the track."""
        self.handler.set_album(self.audio, value)
        return self

    def extract_image(self, output_path=None):
        """
        Extract album artwork from the audio file and save it to disk.
        
        Args:
            output_path: Path to save the image (optional)
                If not provided, will generate a path based on audio filename
        
        Returns:
            Path: Path to the saved image file, or None if no image was found
        
        Raises:
            ValueError: If the track doesn't contain artwork
        """
        # Check if image exists
        metadata = self.get_metadata()
        if not metadata['has_image']:
            raise ValueError(f"No image found in {self.filepath}")
    
        # Get image data and format from the handler
        image_data, mime_type = self.handler.extract_image(self.audio)
    
        # Determine file extension from mime type
        if mime_type == 'image/jpeg':
            ext = '.jpg'
        elif mime_type == 'image/png':
            ext = '.png'
        else:
            # Default to jpg for unknown types
            ext = '.jpg'
        
        # Generate output path if not provided
        if output_path is None:
            output_path = self.filepath.with_stem(f"{self.filepath.stem}-image").with_suffix(ext)
        else:
            output_path = Path(output_path)
        
        # Save the image
        with open(output_path, 'wb') as f:
            f.write(image_data)
        
        return output_path
    
    def set_image(self, image_path, mime_type=None):
        """Set album artwork from an image file."""
        image_path = Path(image_path)
        if not image_path.exists():
            raise FileNotFoundError(f"Image file not found: {image_path}")
        
        # Read image data
        with open(image_path, 'rb') as f:
            image_data = f.read()
        
        # Determine MIME type if not provided
        if mime_type is None:
            ext = image_path.suffix.lower()
            if ext in ['.jpg', '.jpeg']:
                mime_type = 'image/jpeg'
            elif ext == '.png':
                mime_type = 'image/png'
            else:
                raise ValueError(f"Unsupported image format: {ext}")
        
        # Set the image
        self.handler.set_image(self.audio, image_data, mime_type)
        return self
    
    def save(self):
        """Save changes to the file."""
        self.audio.save()
        return self

    def convert_to_format(self, format, output_file_path=None):
        """
        Convert the audio file to a different format.
        
        Args:
            format: Target format (e.g., 'mp3', 'flac', 'aac')
            output_file_path: Path to save the converted file (optional)
             If not provided, will generate a path with appropriate extension
    
        Returns:
            AudioTrack: A new AudioTrack instance for the converted file
        """
        import subprocess
    
        # Generate output path if not provided
        if output_file_path is None:
            output_file_path = self.filepath.with_suffix(f'.{format}')
        else:
            output_file_path = Path(output_file_path)
        
        # Prepare ffmpeg command
        cmd = [
            'ffmpeg',
            '-i', str(self.filepath),
            '-c:a'
        ]
        
        # Set encoder based on target format
        if format == 'mp3':
            cmd.extend(['libmp3lame', '-q:a', '2'])
        elif format == 'flac':
            cmd.extend(['flac'])
        elif format == 'aac' or format == 'm4a':
            cmd.extend(['aac', '-b:a', '256k'])
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        # Add output file path
        cmd.append(str(output_file_path))
        
        # Execute conversion
        subprocess.run(cmd, check=True, capture_output=True)
        
        # Get metadata from original file to preserve
        orig_metadata = self.get_metadata()
        
        # Create new AudioTrack for the converted file
        new_track = AudioTrack(output_file_path)
        
        # Copy over metadata from original file
        if orig_metadata['artist']:
            new_track.set_artist(orig_metadata['artist'])
        if orig_metadata['album']:
            new_track.set_album(orig_metadata['album'])
            
        # Note: We deliberately don't copy artwork
        # The UI will show has_image as False for this track
        
        # Save the metadata
        new_track.save()
        
        return new_track
