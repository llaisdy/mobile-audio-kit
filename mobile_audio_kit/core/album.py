from pathlib import Path
import mutagen
from .track import AudioTrack

class Album:
    """
    Represents a collection of audio tracks in a directory, functioning as a workspace.
    """
    # Audio file extensions to look for
    AUDIO_EXTENSIONS = ['.mp3', '.m4a', '.flac', '.wav', '.ogg']
    
    def __init__(self, directory):
        """
        Initialize an Album from a directory of audio files.
        
        Args:
            directory: Path to the directory containing audio files
        
        Raises:
            FileNotFoundError: If the directory doesn't exist
            ValueError: If no audio files are found in the directory
        """
        self.directory = Path(directory)
        if not self.directory.exists() or not self.directory.is_dir():
            raise FileNotFoundError(f"Directory not found: {directory}")
        
        # Store all files in the directory
        self.all_files = list(self.directory.iterdir())
        
        # Categorize files
        self.audio_files = []
        self.tracks = {}  # Map of filename -> AudioTrack
        self.export_selection = []  # Ordered list of track names to export
        
        # Load audio tracks
        self._load_tracks()

        self.playlists = []
        self._load_playlists()
        
        if not self.tracks:
            raise ValueError(f"No audio files found in {directory}")
    
    def _load_tracks(self):
        """Load all audio tracks in the directory."""
        for file in self.all_files:
            if file.is_file() and file.suffix.lower() in self.AUDIO_EXTENSIONS:
                self.audio_files.append(file)
                try:
                    track = AudioTrack(file)
                    self.tracks[file.name] = track
                except (ValueError, mutagen.MutagenError) as e:
                    # Log error but continue with other files
                    print(f"Error loading {file}: {e}")

    def _load_playlists(self):
        """Load playlists from the directory."""
        self.playlists = []

        # Find playlist files
        playlist_files = list(self.directory.glob("*.m3u")) + list(self.directory.glob("*.m3u8"))

        for playlist_file in sorted(playlist_files):
            self.playlists.append(playlist_file.name)

    def get_playlist_names(self):
        """Return a list of playlist filenames."""
        return self.playlists.copy()
                    
    def get_track_count(self):
        """Return the number of valid audio tracks."""
        return len(self.tracks)
    
    def get_track_names(self):
        """Return a list of track filenames."""
        return list(self.tracks.keys())
    
    def get_track(self, filename):
        """Get an AudioTrack by filename."""
        if filename not in self.tracks:
            raise KeyError(f"Track not found: {filename}")
        return self.tracks[filename]

    def get_album_health(self):
        """
        Analyze the album's health and consistency.

        Returns:
            dict: Health status information with:
                - overall: Overall album health ('red', 'amber', 'green')
                - issues: List of album-wide issues
                - consistency: Dict of metadata consistency checks
        """
        health = {
            'overall': 'green',
            'issues': [],
            'consistency': {
                'album': self._check_consistency('album'),
                'artist': self._check_consistency('artist'),
                'encoding': self._check_consistency('encoding'),
                'has_image': self._check_consistency('has_image')
            }
        }

        # Determine overall health based on consistency
        for field, status in health['consistency'].items():
            if status['status'] == 'red':
                health['overall'] = 'red'
                health['issues'].append(f"Inconsistent {field} values")
            elif status['status'] == 'amber' and health['overall'] != 'red':
                health['overall'] = 'amber'
                health['issues'].append(f"Inconsistent {field} values")

        return health

    def get_track_health(self, track_name=None):
        """
        Get health status for a specific track or all tracks.

        Args:
            track_name: Name of the track to check (optional)
                       If None, returns health for all tracks

        Returns:
            dict: Health status for tracks
        """
        result = {}

        tracks_to_check = [track_name] if track_name else self.get_track_names()

        for name in tracks_to_check:
            track = self.tracks[name]
            metadata = track.get_metadata()

            health = {
                'status': 'green',
                'issues': []
            }

            # Check for critical issues (red)
            if metadata['encoding'] == 'alac':
                health['status'] = 'red'
                health['issues'].append('ALAC encoding needs conversion')

            # Check for important issues (amber)
            if not metadata['has_image']:
                if health['status'] != 'red':
                    health['status'] = 'amber'
                    health['issues'].append('Missing album artwork')

            if not metadata['artist']:
                if health['status'] != 'red':
                    health['status'] = 'amber'
                    health['issues'].append('Missing artist')

            if not metadata['album']:
                if health['status'] != 'red':
                    health['status'] = 'amber'
                    health['issues'].append('Missing album name')

            result[name] = health

        return result if track_name is None else result[track_name]

    def _check_consistency(self, field):
        """
        Check if all tracks have the same value for a field.

        Args:
            field: Metadata field to check

        Returns:
            dict: Consistency status information
        """
        values = set()

        for track in self.tracks.values():
            metadata = track.get_metadata()
            # Handle special case for boolean values
            if field == 'has_image':
                values.add(metadata[field])
            else:
                if metadata[field] is not None:
                    values.add(metadata[field])

        result = {
            'values': list(values),
            'consistent': len(values) <= 1
        }

        # Determine status based on field and consistency
        if not result['consistent']:
            if field in ['album', 'has_image']:
                result['status'] = 'red'  # These should always be consistent
            elif field == 'artist':
                result['status'] = 'amber'  # Artist might vary (compilations)
            elif field == 'encoding':
                result['status'] = 'amber'  # Mixed encodings might be intentional
            else:
                result['status'] = 'amber'
        else:
            result['status'] = 'green'

        return result

    def add_to_export(self, filename, position=None):
        """
        Add a track or playlist  to the export selection at the specified position.
        
        Args:
            filename: Name of the file to add
            position: Position to insert (default: end of list)
        
        Returns:
            int: New position in the export list
        
        Raises:
            KeyError: If filename doesn't exist in the album
        """
        # Check if it's a track
        if filename in self.tracks:
            pass  # Track exists
        # Check if it's a playlist
        elif filename in self.playlists:
            pass  # Playlist exists
        else:
            raise KeyError(f"File not found: {filename}")        
        
        # Remove if already in the list to avoid duplicates
        if filename in self.export_selection:
            self.export_selection.remove(filename)
        
        # Add at the specified position or at the end
        if position is None or position >= len(self.export_selection):
            self.export_selection.append(filename)
            return len(self.export_selection) - 1
        else:
            self.export_selection.insert(position, filename)
            return position
    
    def remove_from_export(self, track_name):
        """
        Remove a track from the export selection.
        
        Args:
            track_name: Name of the track to remove
        
        Returns:
            bool: True if the track was in the selection and removed
        """
        if track_name in self.export_selection:
            self.export_selection.remove(track_name)
            return True
        return False
    
    def clear_export_selection(self):
        """Clear the export selection."""
        self.export_selection = []
    
    def get_export_selection(self):
        """
        Get the current export selection.
        
        Returns:
            list: Ordered list of track names to export
        """
        return self.export_selection.copy()
    
    def select_all_for_export(self):
        """Select all tracks for export in their natural order."""
        self.export_selection = self.get_track_names()

    def create_export_zip(self, output_path=None, parent_dir=None):
        """
        Create a zip file containing the selected tracks and playlists.

        Args:
            output_path: Path for the zip file (optional)
                If not provided, creates a zip in parent_dir
                with the album directory name and timestamp
            parent_dir: Directory to place the zip if output_path not provided
                Defaults to the parent directory of the album

        Returns:
            Path: Path to the created zip file

        Raises:
            ValueError: If no tracks are selected for export
        """
        import zipfile
        from datetime import datetime

        if not self.export_selection:
            raise ValueError("No tracks selected for export")

        # Use provided parent_dir or default to album directory's parent
        parent_dir = parent_dir or self.directory.parent

        # Generate default output path if not provided
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = parent_dir / f"{self.directory.name}_{timestamp}.zip"
        else:
            output_path = Path(output_path)

        # Create zip file
        with zipfile.ZipFile(output_path, 'w') as zipf:
            for filename in self.export_selection:
                file_path = self.directory / filename
                zipf.write(file_path, arcname=filename)

        return output_path
