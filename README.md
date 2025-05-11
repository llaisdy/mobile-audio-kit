# MAK - Mobile Audio Kit

A terminal-based utility for managing audio file metadata, album artwork, and creating playlists.

## Features

- View and edit audio metadata (artist, album, etc.)
- Extract and embed album artwork
- Convert between audio formats
- Create playlists
- Export tracks and playlists to zip files
- Color-coded health checks for metadata completeness

## Installation

```bash
pip install mobile-audio-kit
```

## Usage
Start `mak` by pointing it to a directory containing audio files:

```bash
mak path/to/your/music/folder
```

## Commands

- `<number>` - View track details
- `enc <format>` - Set encoding for all tracks
- `art <artist>` - Set artist for all tracks
- `alb <album>` - Set album for all tracks
- `img <file>` - Set image for all tracks
- `img <track> from <track>` - Copy image between tracks
- `pll <tracks> <name>` - Create playlist
- `sel <track_numbers>` - Select tracks for export
- `selview` - Show and manage selection order
- `zip` - Create zip export of selected tracks
- `help` or `?` - Show help information
- `q` or `quit` - Exit the application

## Requirements

- Python 3.8 or higher
- ffmpeg (for audio conversion)

## License

MIT License - see LICENSE file for details.
