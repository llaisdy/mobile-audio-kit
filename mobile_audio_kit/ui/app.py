from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Input, DataTable, Static
from textual.containers import Container, Vertical, Horizontal
from textual.binding import Binding
from pathlib import Path
from mobile_audio_kit.core.album import Album

class MakApp(App):
    """The main MAK application for audio file management."""

    # Add keyboard bindings
    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit"),
        Binding("ctrl+h", "help", "Help")
    ]
    
    CSS = """
    #album-info {
        height: auto;
        margin: 1 0;
        padding: 1;
        border: solid green;
    }
    
    #tracks-table {
        height: 1fr;
        min-height: 10;
    }
    
    #status-bar {
        height: auto;
        padding: 1;
        background: $primary-background-lighten-2;
    }
    
    #command-input {
        margin: 1 0;
    }
    
    .health-red {
        background: red;
        color: red;
    }

    .health-amber {
        background: yellow;
        color: yellow;
    }

    .health-green {
        background: #050;
        color: green;
    }
    """
    
    def __init__(self, directory: str = "."):
        """Initialize the app with a directory to work with."""
        super().__init__()
        self.directory = Path(directory)
        self.album = None
        self.current_screen = "main"  # main, track, config
        self.current_track = None
    
    def compose(self) -> ComposeResult:
        """Create the UI layout."""
        yield Header(show_clock=True)
        
        # Main content area
        with Container(id="main-content"):
            # Album info section
            yield Static("", id="album-info")
            
            # Tracks table
            yield DataTable(id="tracks-table")
            
            # Status bar
            yield Static("Ready", id="status-bar")
            
            # Command input
            yield Input(placeholder="> ", id="command-input")
        
        yield Footer()
    
    def on_mount(self) -> None:
        """Initialize the application after mounting."""
        try:
            self.album = Album(self.directory)
            self.load_album_view()
            # Focus the input field
            self.query_one("#command-input").focus()
        except Exception as e:
            self.query_one("#status-bar").update(f"Error: {e}")
    
    def load_album_view(self) -> None:
        """Load the album information into the UI."""
        if not self.album:
            return

        # Update album info
        album_health = self.album.get_album_health()
        health_class = f"health-{album_health['overall']}"
        album_info = self.query_one("#album-info")
        album_info.update(f"[{health_class}]Album: {self.directory.name}[/]")

        # Setup tracks table
        table = self.query_one("#tracks-table")
        table.clear(columns=True)

        # Add columns to the table
        table.add_columns("#", "Type", "Name", "Artist", "Album", "Encoding", "Image", "Health")

        # Get track names and sort them alphabetically
        track_names = sorted(self.album.get_track_names())
        export_selection = self.album.get_export_selection()
        
        # Add rows for each track
        track_health = self.album.get_track_health()
        for i, track_name in enumerate(track_names, 1):
            track = self.album.get_track(track_name)
            metadata = track.get_metadata()

            health = track_health[track_name]
            if health['status'] == 'amber':
                health_colour = 'yellow'
            else:
                health_colour = health['status']
            health_class = f"bold {health_colour}"
            health_message = "OK" if not health['issues'] else ", ".join(health['issues'])
            health_cell = f"[{health_class}]{health_message}[/]"

            # Check if track is in export selection
            if track_name in export_selection:
                # Track is selected - highlight it
                type_cell = "[bold cyan]Track ✓[/]"
                name_cell = f"[cyan]{track_name}[/]"
            else:
                type_cell = "Track"
                name_cell = track_name
            
            table.add_row(
                str(i),
                type_cell,
                name_cell,
                metadata['artist'] or "",
                metadata['album'] or "",
                metadata['encoding'],
                "✓" if metadata['has_image'] else "✗",
                health_cell
            )

        # Find and add playlists
        playlists = self.album.get_playlist_names()
        for j, playlist_name in enumerate(playlists, i + 1):
            # Check if playlist is in export selection
            if playlist_name in export_selection:
                # Playlist is selected - highlight it
                type_cell = "[bold purple]Playlist ✓[/]"
                name_cell = f"[purple]{playlist_name}[/]"
            else:
                type_cell = "[purple]Playlist[/]"
                name_cell = playlist_name

            table.add_row(
                str(j),
                type_cell,
                name_cell,
                "", "", "", "", ""
            )

        # Update command input
        cmd_input = self.query_one("#command-input")
        cmd_input.placeholder = "> "
        cmd_input.focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle command input."""
        command = event.value.strip()

        # Debug output to status bar
        status_bar = self.query_one("#status-bar")
        status_bar.update(f"Processing command: {command}")
        
        if not command:
            return
        
        # Clear the input
        input_widget = self.query_one("#command-input")
        input_widget.value = ""
        
        # Handle command based on current screen
        if self.current_screen == "main":
            self.handle_main_command(command)
        elif self.current_screen == "track":
            self.handle_track_command(command)
        elif self.current_screen == "config":
            self.handle_config_command(command)
        elif self.current_screen == "selection":
            self.handle_selection_command(command)
            
        # Re-focus the input field
        input_widget.focus()

    def refresh_album_data(self):
        """Refresh album data to reflect any changes in the directory."""
        try:
            # Create a new Album object to re-scan the directory
            self.album = Album(self.directory)

            # Reload the view based on current screen
            if self.current_screen == "main":
                self.load_album_view()
            elif self.current_screen == "track" and self.current_track:
                # Check if current track still exists
                if self.current_track in self.album.get_track_names():
                    self.load_track_view()
                else:
                    # If track no longer exists, go back to main view
                    self.current_screen = "main"
                    self.load_album_view()
            elif self.current_screen == "config":
                self.load_config_view()
        except Exception as e:
            self.query_one("#status-bar").update(f"Error refreshing album data: {e}")
        
    def handle_main_command(self, command: str) -> None:
        """Handle commands in the main screen."""
        parts = command.split(maxsplit=1)
        verb = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        # Check if the command is a track number
        try:
            track_num = int(verb)
            if 1 <= track_num <= len(self.album.get_track_names()):
                track_names = sorted(self.album.get_track_names())
                self.current_track = track_names[track_num - 1]
                self.current_screen = "track"
                self.load_track_view()
                return
        except ValueError:
            pass

        # Handle other commands
        status_bar = self.query_one("#status-bar")

        if verb == "q" or verb == "quit":
            self.exit()
        elif verb == "enc":
            self.handle_encoding_command(args)
        elif verb == "sel" or verb == "select":
            self.handle_select_command(args)
        elif verb == "unsel" or verb == "unselect":
            self.handle_unselect_command(args)
        elif verb == "selall":
            self.album.select_all_for_export()
            # TODO reload album view for table update
            status_bar.update(f"Selected all {len(self.album.get_track_names())} tracks for export")
        elif verb == "selclear":
            self.album.clear_export_selection()
            # TODO reload album view for table update
            status_bar.update("Cleared export selection")
        elif verb == "sellist":
            self.show_selection()
        elif verb == "selview":
            self.current_screen = "selection"
            self.load_selection_view()
        elif verb == "art":
            self.handle_artist_command(args)
        elif verb == "alb":
            self.handle_album_command(args)
        elif verb == "img":
            self.handle_image_command(args)
        elif verb == "pll":
            self.handle_playlist_command(args)
        elif verb == "zip":
            self.handle_zip_command()
        elif verb == "cfg":
            status_bar.update("Opening config screen...")
            self.current_screen = "config"
            self.load_config_view()
        elif verb == "help" or verb == "?":
            self.show_help()
        else:
            status_bar.update(f"Unknown command: {verb}")

    def handle_select_command(self, args):
        """Handle selecting tracks or playlists for export."""
        status_bar = self.query_one("#status-bar")

        if not args:
            status_bar.update("Usage: sel <number(s)> - e.g., sel 1 2 3")
            return

        # Get all selectable items in order
        track_names = sorted(self.album.get_track_names())
        playlist_names = self.album.get_playlist_names()
        all_items = track_names + playlist_names
        track_nums = args.split()
        selected = []

        try:
            for num_str in track_nums:
                num = int(num_str)
                if 1 <= num <= len(all_items):
                    item = all_items[num - 1]
                    self.album.add_to_export(item)
                    selected.append(item)
                else:
                    status_bar.update(f"Invalid track number: {num}")
                    return

            if len(selected) == 1:
                status_bar.update(f"Selected {selected[0]} for export")
            else:
                status_bar.update(f"Selected {len(selected)} items for export")
            self.load_album_view()
        except ValueError:
            status_bar.update("Invalid number format")

    def handle_unselect_command(self, args):
        """Handle unselecting tracks for export."""
        status_bar = self.query_one("#status-bar")

        if not args:
            status_bar.update("Usage: unsel <track_number(s)> - e.g., unsel 1 2 3")
            return

        track_names = sorted(self.album.get_track_names())
        playlist_names = self.album.get_playlist_names()
        all_items = track_names + playlist_names
        track_nums = args.split()
        unselected = []

        try:
            for num_str in track_nums:
                num = int(num_str)
                if 1 <= num <= len(all_items):
                    item = all_items[num - 1]
                    if self.album.remove_from_export(item):
                        unselected.append(item)
                else:
                    status_bar.update(f"Invalid number: {num}")
                    return

            if len(unselected) == 1:
                status_bar.update(f"Removed item {unselected[0]} from export selection")
            else:
                status_bar.update(f"Removed {len(unselected)} items from export selection")
            self.load_album_view()
        except ValueError:
            status_bar.update("Invalid number format")

    def show_selection(self):
        """Show currently selected tracks for export."""
        status_bar = self.query_one("#status-bar")
        selection = self.album.get_export_selection()

        if not selection:
            status_bar.update("No tracks selected for export")
            return

        # Use the album info area to show selection
        album_info = self.query_one("#album-info")
        selection_text = f"Export selection ({len(selection)} tracks): " + ", ".join(selection)
        album_info.update(selection_text)

        status_bar.update(f"{len(selection)} tracks selected for export")
            
    def handle_track_command(self, command: str) -> None:
        """Handle commands in the track detail screen."""
        parts = command.split(maxsplit=1)
        verb = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        status_bar = self.query_one("#status-bar")

        if verb == ".." or verb == "<":
            self.current_screen = "main"
            self.load_album_view()
        elif verb == "art":
            # Handle setting artist for this track only
            self.handle_artist_command(args, track_name=self.current_track)
        elif verb == "alb":
            # Handle setting album for this track only
            self.handle_album_command(args, track_name=self.current_track)
        elif verb == "enc":
            # Handle encoding for this track only
            self.handle_encoding_command(args, track_name=self.current_track)
        elif verb == "img":
            # Handle image for this track only
            self.handle_image_command(args, track_name=self.current_track)
        else:
            status_bar.update(f"Unknown command: {verb}")

    def handle_encoding_command(self, args, track_name=None):
        """Handle encoding conversion command."""
        status_bar = self.query_one("#status-bar")

        if not args:
            status_bar.update("Usage: enc <format> - Valid formats: mp3, flac, aac")
            return

        target_format = args.strip().lower()
        valid_formats = ["mp3", "flac", "aac", "m4a"]

        if target_format not in valid_formats:
            status_bar.update(f"Invalid format: {target_format}. Valid formats: mp3, flac, aac")
            return

        try:
            if track_name:
                # Convert single track
                track = self.album.get_track(track_name)
                status_bar.update(f"Converting {track_name} to {target_format}...")
                # This would be async in a real app
                new_track = track.convert_to_format(target_format)
                status_bar.update(f"Converted {track_name} to {target_format}")
                # Refresh view
                if self.current_screen == "track":
                    self.load_track_view()
                else:
                    self.load_album_view()
            else:
                # Convert all tracks
                status_bar.update(f"Converting all tracks to {target_format}...")
                # This would be handled by a background worker in a real app
                for name in self.album.get_track_names():
                    track = self.album.get_track(name)
                    track.convert_to_format(target_format)
                status_bar.update(f"Converted all tracks to {target_format}")
                self.load_album_view()
            self.refresh_album_data()
        except Exception as e:
            status_bar.update(f"Error converting: {e}")

    def handle_artist_command(self, args, track_name=None):
        """Handle setting artist metadata."""
        status_bar = self.query_one("#status-bar")

        if not args:
            status_bar.update("Usage: art <artist name>")
            return

        try:
            if track_name:
                # Set artist for a single track
                track = self.album.get_track(track_name)
                track.set_artist(args).save()
                status_bar.update(f"Set artist to '{args}' for {track_name}")
                # Refresh view
                if self.current_screen == "track":
                    self.load_track_view()
                else:
                    self.load_album_view()
            else:
                # Set artist for all tracks
                for name in self.album.get_track_names():
                    track = self.album.get_track(name)
                    track.set_artist(args).save()
                status_bar.update(f"Set artist to '{args}' for all tracks")
                self.load_album_view()
            self.refresh_album_data()
        except Exception as e:
            status_bar.update(f"Error setting artist: {e}")

    def handle_album_command(self, args, track_name=None):
        """Handle setting album metadata."""
        status_bar = self.query_one("#status-bar")

        if not args:
            status_bar.update("Usage: alb <album name>")
            return

        try:
            if track_name:
                # Set album for a single track
                track = self.album.get_track(track_name)
                track.set_album(args).save()
                status_bar.update(f"Set album to '{args}' for {track_name}")
                # Refresh view
                if self.current_screen == "track":
                    self.load_track_view()
                else:
                    self.load_album_view()
            else:
                # Set album for all tracks
                for name in self.album.get_track_names():
                    track = self.album.get_track(name)
                    track.set_album(args).save()
                status_bar.update(f"Set album to '{args}' for all tracks")
                self.load_album_view()
            self.refresh_album_data()
        except Exception as e:
            status_bar.update(f"Error setting album: {e}")

    def handle_image_command(self, args, track_name=None):
        """Handle image commands."""
        status_bar = self.query_one("#status-bar")
        parts = args.split(maxsplit=1)

        if not args:
            status_bar.update("Usage: img <image_path> or img <track_number> from <other_track_number>")
            return

        try:
            # Check if it's a "from" command
            if len(parts) > 1 and parts[0].lower() == "from":
                # Extract source track
                try:
                    source_num = int(parts[1])
                    track_names = sorted(self.album.get_track_names())
                    if 1 <= source_num <= len(track_names):
                        source_track_name = track_names[source_num - 1]

                        # Extract image from source track
                        source_track = self.album.get_track(source_track_name)
                        if not source_track.get_metadata()['has_image']:
                            status_bar.update(f"Source track {source_track_name} has no image")
                            return

                        # Extract to a temporary file
                        import tempfile
                        temp_image = tempfile.mktemp(suffix=".jpg")
                        source_track.extract_image(temp_image)

                        # Apply to target track(s)
                        if track_name:
                            target_track = self.album.get_track(track_name)
                            target_track.set_image(temp_image).save()
                            status_bar.update(f"Copied image from {source_track_name} to {track_name}")
                        else:
                            status_bar.update(f"Usage: img <track_number> from <source_track_number>")

                        # Clean up temp file
                        import os
                        os.remove(temp_image)

                        self.refresh_album_data()
                    else:
                        status_bar.update(f"Invalid track number: {source_num}")
                except ValueError:
                    status_bar.update(f"Invalid track number format")
            else:
                # Assume it's a file path
                image_path = args

                if track_name:
                    # Set image for a single track
                    track = self.album.get_track(track_name)
                    track.set_image(image_path).save()
                    status_bar.update(f"Set image from {image_path} for {track_name}")
                else:
                    # Set image for all tracks
                    for name in self.album.get_track_names():
                        track = self.album.get_track(name)
                        track.set_image(image_path).save()
                    status_bar.update(f"Set image from {image_path} for all tracks")
                self.refresh_album_data()
        except Exception as e:
            status_bar.update(f"Error setting image: {e}")

    def handle_playlist_command(self, args):
        """Handle playlist creation command."""
        status_bar = self.query_one("#status-bar")

        parts = args.strip().split()
        if len(parts) < 2:
            status_bar.update("Usage: pll <track_nums> <playlist_name>")
            return

        # Last part is the playlist name
        playlist_name = parts[-1]
        track_nums = parts[:-1]

        try:
            # Convert track numbers to track names
            track_names = sorted(self.album.get_track_names())
            selected_tracks = []

            for num_str in track_nums:
                try:
                    num = int(num_str)
                    if 1 <= num <= len(track_names):
                        selected_tracks.append(track_names[num - 1])
                    else:
                        status_bar.update(f"Invalid track number: {num}")
                        return
                except ValueError:
                    status_bar.update(f"Invalid track number: {num_str}")
                    return

            # Create the playlist
            playlist_path = self.album.directory / f"{playlist_name}.m3u"

            with open(playlist_path, "w") as f:
                f.write("#EXTM3U\n")
                for track in selected_tracks:
                    f.write(f"{track}\n")

            status_bar.update(f"Created playlist {playlist_name}.m3u with {len(selected_tracks)} tracks")
            self.refresh_album_data()
        except Exception as e:
            status_bar.update(f"Error creating playlist: {e}")

    def handle_zip_command(self):
        """Handle zip export command."""
        status_bar = self.query_one("#status-bar")

        try:
            # Check if there's an existing selection
            selection = self.album.get_export_selection()
            if not selection:
                # If no tracks are explicitly selected, select all
                self.album.select_all_for_export()
                selection = self.album.get_export_selection()
                status_bar.update(f"No tracks were selected, using all {len(selection)} tracks for export")

            # Create the zip file in the album directory
            zip_path = self.album.create_export_zip()

            status_bar.update(f"Created export zip with {len(selection)} tracks: {zip_path}")
            self.refresh_album_data()
        except Exception as e:
            status_bar.update(f"Error creating zip: {e}")

    def load_track_view(self) -> None:
        """Load the track detail view."""
        if not self.current_track or not self.album:
            return

        # Get track and metadata
        track = self.album.get_track(self.current_track)
        metadata = track.get_metadata()
        track_health = self.album.get_track_health(self.current_track)
        health_class = f"health-{track_health['status']}"

        # Clear the tracks table and repurpose for track details
        table = self.query_one("#tracks-table")
        table.clear(columns=True)

        # Set up columns for key-value pairs
        table.add_columns("Property", "Value")

        # Add track details
        table.add_row("Filename", self.current_track)
        table.add_row("Artist", metadata['artist'] or "")
        table.add_row("Album", metadata['album'] or "")
        table.add_row("Encoding", metadata['encoding'])
        table.add_row("Has Image", "Yes" if metadata['has_image'] else "No")

        if metadata['has_image'] and metadata['image_info']:
            table.add_row("Image Format", metadata['image_info'].get('format', ''))
            table.add_row("Image Size", f"{metadata['image_info'].get('size', 0)} bytes")

        # Add health issues
        issues_text = ", ".join(track_health['issues']) if track_health['issues'] else "No issues"
        table.add_row("Health", f"[{health_class}]{issues_text}[/]")

        # Update album info section to show we're in track view
        album_info = self.query_one("#album-info")
        album_info.update(f"Track Detail: {self.current_track} (type '..' to return)")

        # Update status bar
        status = self.query_one("#status-bar")
        status.update("Track detail view. Available commands: art, alb, enc, img, ..")

        # Update command input placeholder
        cmd_input = self.query_one("#command-input")
        cmd_input.placeholder = f"{self.current_track}> "
        cmd_input.focus()
    
    def handle_track_command(self, command: str) -> None:
        """Handle commands in the track detail screen."""
        # TODO: Implement track commands
        if command in ("q", "quit"):
            self.exit()
        elif command in ("..", "<"):
            self.current_screen = "main"
            self.load_album_view()
    
    def load_config_view(self) -> None:
        """Load the config view."""
        # Update album info section to show we're in config view
        album_info = self.query_one("#album-info")
        album_info.update("Configuration (type '..' to return)")

        # Clear the tracks table and repurpose for settings
        table = self.query_one("#tracks-table")
        table.clear(columns=True)

        # Set up columns for settings
        table.add_columns("Setting", "Value")

        # Add configuration options (placeholder)
        table.add_row("Backup files before editing", "Yes")
        table.add_row("Default export format", "ZIP")
        table.add_row("Default playlist format", "M3U")

        # Update status bar
        status = self.query_one("#status-bar")
        status.update("Config view. Type '..' to return to main view.")

        # Update command input placeholder
        cmd_input = self.query_one("#command-input")
        cmd_input.placeholder = "config> "
        cmd_input.focus()

    def handle_config_command(self, command: str) -> None:
        """Handle commands in the config screen."""
        status_bar = self.query_one("#status-bar")

        if command == ".." or command == "<":
            self.current_screen = "main"
            self.load_album_view()
        else:
            # Placeholder for actual config commands
            status_bar.update(f"Config command not implemented: {command}")

    def load_selection_view(self):
        """Load a view showing the export selection in order."""
        selection = self.album.get_export_selection()

        if not selection:
            self.query_one("#status-bar").update("No tracks selected for export")
            self.current_screen = "main"
            self.load_album_view()
            return

        # Update album info
        album_info = self.query_one("#album-info")
        album_info.update(f"Export Selection ({len(selection)} tracks)")

        # Setup tracks table
        table = self.query_one("#tracks-table")
        table.clear(columns=True)

        # Add columns to the table
        table.add_columns("Order", "Original #", "Name", "Artist", "Album", "Encoding", "Image", "Health")

        # Get track health
        track_health = self.album.get_track_health()

        # Get all tracks for reference
        track_names = sorted(self.album.get_track_names())
        playlist_names = self.album.get_playlist_names()
        all_items = track_names + playlist_names
        
        # Add rows for each track in selection order
        for sel_idx, item_name in enumerate(selection, 1):
            # Find the original position
            orig_idx = all_items.index(item_name) + 1

            # Check if it's a track or playlist
            if item_name in track_names:
                # It's a track
                track = self.album.get_track(item_name)
                metadata = track.get_metadata()

                # Format health info
                health = track_health[item_name]
                if health['status'] == 'amber':
                    health_colour = 'yellow'
                else:
                    health_colour = health['status']
                health_message = "OK" if not health['issues'] else ", ".join(health['issues'])
                health_cell = f"[bold {health_colour}]{health_message}[/]"

                table.add_row(
                    f"[bold cyan]{sel_idx}[/]",          # Selection order
                    str(orig_idx),                        # Original position
                    item_name,
                    metadata['artist'] or "",
                    metadata['album'] or "",
                    metadata['encoding'],
                    "✓" if metadata['has_image'] else "✗",
                    health_cell
                )
            else:
                # It's a playlist
                table.add_row(
                    f"[bold cyan]{sel_idx}[/]",          # Selection order
                    str(orig_idx),                        # Original position
                    f"[purple]{item_name}[/]",
                    "[purple]Playlist[/]",
                    "", "", "", ""
                )
            
        # Update status bar with available commands
        status_bar = self.query_one("#status-bar")
        status_bar.update("Selection view: 'back' to return to album view, 'move <from> <to>' to reorder")

        # Update command input
        cmd_input = self.query_one("#command-input")
        cmd_input.placeholder = "selection> "
        cmd_input.focus()

    def handle_selection_command(self, command):
        """Handle commands in the selection view."""
        parts = command.lower().split()
        verb = parts[0] if parts else ""

        status_bar = self.query_one("#status-bar")

        if verb in ('back', 'return', '..'):
            # Return to main view
            self.current_screen = "main"
            self.load_album_view()
        elif verb == 'move' and len(parts) == 3:
            try:
                # Parse positions
                from_pos = int(parts[1])
                to_pos = int(parts[2])

                # Get current selection
                selection = self.album.get_export_selection()

                # Validate positions
                if 1 <= from_pos <= len(selection) and 1 <= to_pos <= len(selection):
                    # Get the track to move
                    track_to_move = selection[from_pos - 1]

                    # Remove from current position
                    self.album.remove_from_export(track_to_move)

                    # Add at new position
                    adjusted_position = to_pos - 1  # Convert to 0-based index
                    self.album.add_to_export(track_to_move, adjusted_position)

                    status_bar.update(f"Moved track from position {from_pos} to {to_pos}")
                    self.load_selection_view()
                else:
                    status_bar.update(f"Invalid position: must be between 1 and {len(selection)}")
            except ValueError:
                status_bar.update("Invalid position format")
        else:
            status_bar.update("Unknown command. Type 'back' to return to album view")

            
    def show_help(self) -> None:
        """Show help information."""
        help_text = """
        Available commands:
        <number> - View track details
        enc <format> - Set encoding for all tracks
        art <artist> - Set artist for all tracks
        alb <album> - Set album for all tracks
        img <file> - Set image for all tracks
        img <track> from <track> - Copy image between tracks
        pll <tracks> <name> - Create playlist

        sel <track_numbers> - Select tracks for export
        unsel <track_numbers> - Unselect tracks from export
        selall - Select all tracks for export
        selclear - Clear the export selection
        sellist - Show currently selected tracks
        selview - Show and manage selection order
        zip - Create zip export of selected tracks

        cfg - Open config screen
        help or ? - Show this help
        q or quit - Exit the application
        """
        self.query_one("#status-bar").update(help_text)

    # Add action handlers for bindings
    def action_quit(self) -> None:
        """Quit the application."""
        self.exit()
    
    def action_help(self) -> None:
        """Show help information."""
        self.show_help()
        

# Command-line entry point
def run():
    import sys
    directory = sys.argv[1] if len(sys.argv) > 1 else "."
    app = MakApp(directory)
    app.run()


if __name__ == "__main__":
    run()
