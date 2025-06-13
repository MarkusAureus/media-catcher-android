# -----------------------------------------------------------------------------
# -- MEDIA CATCHER - A KIVY-BASED YT-DLP FRONTEND                            --
# -- Author: Markus Aureus                                                   --
# -- Date: [Date of Last Edit]                                               --
# -- Description: A cross-platform GUI application for downloading audio     --
# --              and video from various websites using yt-dlp as the        --
# --              backend.                                                   --
# -----------------------------------------------------------------------------

# --- Standard Library Imports ---
import os
import re
import threading
import subprocess

# --- Kivy Framework Imports ---
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.uix.progressbar import ProgressBar
from kivy.uix.checkbox import CheckBox
from kivy.uix.popup import Popup
from kivy.uix.filechooser import FileChooserListView
from kivy.clock import Clock
from kivy.utils import platform
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle

# Set a fixed window size for desktop platforms for a consistent mobile-like experience.
if platform not in ['android', 'ios']:
    Window.size = (400, 700)

class MediaCatcherApp(App):
    """
    The main application class. It orchestrates the UI, event handling,
    and the backend download process.
    """
    def build(self):
        """
        Initializes the application and builds the user interface layout.
        This method sets up all the widgets and their initial states.
        """
        self.title = 'Media Catcher'
        self.icon = 'media-catcher.png'

        # --- Main Layout & Background ---
        # The root widget for the application.
        self.main_layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        # Bind the background update function to the layout's size changes.
        self.main_layout.bind(size=self._update_background)

        # Set up a colored rectangle as the dynamic background.
        with self.main_layout.canvas.before:
            Color(0.1, 0.1, 0.2, 1)  # Dark blue background color
            self.rect = Rectangle(size=self.main_layout.size, pos=self.main_layout.pos)

        # --- UI Widgets ---
        # Application Title Label
        title = Label(
            text='Media Catcher', size_hint=(1, 0.1),
            font_size='24sp', bold=True
        )
        self.main_layout.add_widget(title)

        # URL Input Field
        self.url_input = TextInput(
            hint_text='Enter URL(s) here...', multiline=True,
            size_hint=(1, 0.2), background_color=(0.2, 0.2, 0.3, 1),
            foreground_color=(1, 1, 1, 1)
        )
        self.main_layout.add_widget(self.url_input)

        # Download Mode Selector (Audio/Video)
        mode_layout = BoxLayout(size_hint=(1, 0.08), spacing=10)
        mode_label = Label(text='Mode:', size_hint=(0.3, 1))
        self.mode_spinner = Spinner(
            text='Audio', values=('Audio', 'Video'),
            size_hint=(0.7, 1), background_color=(0.3, 0.3, 0.4, 1)
        )
        self.mode_spinner.bind(text=self.on_mode_change)
        mode_layout.add_widget(mode_label)
        mode_layout.add_widget(self.mode_spinner)
        self.main_layout.add_widget(mode_layout)

        # Playlist Download Option
        playlist_layout = BoxLayout(size_hint=(1, 0.08))
        self.playlist_check = CheckBox(size_hint=(0.1, 1))
        playlist_label = Label(text='Download entire playlist', size_hint=(0.9, 1))
        playlist_layout.add_widget(self.playlist_check)
        playlist_layout.add_widget(playlist_label)
        self.main_layout.add_widget(playlist_layout)

        # --- Dynamic Options Layouts ---
        # These layouts will be shown/hidden based on the selected mode.
        self._create_audio_options()
        self._create_video_options()

        # Add audio options by default.
        self.main_layout.add_widget(self.audio_options)

        # Output Folder Selection Button
        self.output_dir = self.get_default_download_dir()
        self.folder_button = Button(
            text=f'Output: {os.path.basename(self.output_dir)}', size_hint=(1, 0.08),
            background_color=(0.3, 0.3, 0.4, 1)
        )
        self.folder_button.bind(on_press=self.choose_folder)
        self.main_layout.add_widget(self.folder_button)

        # Action Buttons (Download, Stop, Clear)
        buttons_layout = BoxLayout(size_hint=(1, 0.08), spacing=10)
        self.download_button = Button(text='Download', background_color=(0.2, 0.6, 0.2, 1))
        self.download_button.bind(on_press=self.start_download)
        self.stop_button = Button(text='Stop', background_color=(0.6, 0.2, 0.2, 1), disabled=True)
        self.stop_button.bind(on_press=self.stop_download)
        self.clear_button = Button(text='Clear', background_color=(0.4, 0.4, 0.4, 1))
        self.clear_button.bind(on_press=self.clear_fields)
        buttons_layout.add_widget(self.download_button)
        buttons_layout.add_widget(self.stop_button)
        buttons_layout.add_widget(self.clear_button)
        self.main_layout.add_widget(buttons_layout)

        # Progress Bar and Status Label
        self.progress_bar = ProgressBar(max=100, size_hint=(1, 0.05))
        self.main_layout.add_widget(self.progress_bar)
        self.status_label = Label(text='Ready', size_hint=(1, 0.08))
        self.main_layout.add_widget(self.status_label)

        # --- Initial State Variables ---
        self.current_process = None
        self.is_downloading = False

        return self.main_layout

    def _create_audio_options(self):
        """Helper method to create the audio options layout."""
        self.audio_options = BoxLayout(orientation='vertical', size_hint=(1, 0.16), spacing=5)
        # Audio format
        audio_format_layout = BoxLayout(size_hint=(1, 0.5))
        audio_format_label = Label(text='Format:', size_hint=(0.3, 1))
        self.audio_format_spinner = Spinner(
            text='mp3', values=('mp3', 'wav', 'aac', 'm4a', 'opus'),
            size_hint=(0.7, 1), background_color=(0.3, 0.3, 0.4, 1)
        )
        audio_format_layout.add_widget(audio_format_label)
        audio_format_layout.add_widget(self.audio_format_spinner)
        self.audio_options.add_widget(audio_format_layout)
        # Audio quality
        audio_quality_layout = BoxLayout(size_hint=(1, 0.5))
        audio_quality_label = Label(text='Quality:', size_hint=(0.3, 1))
        self.audio_quality_spinner = Spinner(
            text='192K', values=('Best (0)', '192K (5)', '128K (7)', 'Worst (9)'),
            size_hint=(0.7, 1), background_color=(0.3, 0.3, 0.4, 1)
        )
        audio_quality_layout.add_widget(audio_quality_label)
        audio_quality_layout.add_widget(self.audio_quality_spinner)
        self.audio_options.add_widget(audio_quality_layout)

    def _create_video_options(self):
        """Helper method to create the video options layout."""
        self.video_options = BoxLayout(orientation='vertical', size_hint=(1, 0.24), spacing=5)
        # Video quality
        video_quality_layout = BoxLayout(size_hint=(1, 0.33))
        video_quality_label = Label(text='Quality:', size_hint=(0.3, 1))
        self.video_quality_spinner = Spinner(
            text='720p', values=('Best', '1080p', '720p', '480p', '360p'),
            size_hint=(0.7, 1), background_color=(0.3, 0.3, 0.4, 1)
        )
        video_quality_layout.add_widget(video_quality_label)
        video_quality_layout.add_widget(self.video_quality_spinner)
        self.video_options.add_widget(video_quality_layout)
        # Subtitles checkbox
        subtitles_layout = BoxLayout(size_hint=(1, 0.33))
        self.subtitles_check = CheckBox(size_hint=(0.1, 1))
        subtitles_label = Label(text='Download subtitles', size_hint=(0.9, 1))
        subtitles_layout.add_widget(self.subtitles_check)
        subtitles_layout.add_widget(subtitles_label)
        self.video_options.add_widget(subtitles_layout)
        # Subtitle language
        sub_lang_layout = BoxLayout(size_hint=(1, 0.33))
        sub_lang_label = Label(text='Language:', size_hint=(0.3, 1))
        self.sub_lang_spinner = Spinner(
            text='en', values=('en', 'sk', 'cs', 'de', 'fr', 'es'),
            size_hint=(0.7, 1), background_color=(0.3, 0.3, 0.4, 1)
        )
        sub_lang_layout.add_widget(sub_lang_label)
        sub_lang_layout.add_widget(self.sub_lang_spinner)
        self.video_options.add_widget(sub_lang_layout)

    def _update_background(self, instance, value):
        """Updates the background rectangle's size to match the window."""
        self.rect.pos = instance.pos
        self.rect.size = instance.size

    def get_default_download_dir(self):
        """Determines the default download directory based on the OS."""
        if platform == 'android':
            from android.storage import primary_external_storage_path
            return os.path.join(primary_external_storage_path(), 'Download')
        else: # For Windows, macOS, Linux
            return os.path.expanduser('~/Downloads')

    def on_mode_change(self, spinner, text):
        """Swaps the audio and video option widgets when the mode changes."""
        # Determine the correct index to insert the new options widget.
        # It should be placed right before the folder selection button.
        index = self.main_layout.children.index(self.folder_button) + 1

        if text == 'Audio':
            # If video options are visible, remove them.
            if self.video_options.parent:
                self.main_layout.remove_widget(self.video_options)
            # If audio options are not visible, add them.
            if not self.audio_options.parent:
                self.main_layout.add_widget(self.audio_options, index)
        else: # text == 'Video'
            # If audio options are visible, remove them.
            if self.audio_options.parent:
                self.main_layout.remove_widget(self.audio_options)
            # If video options are not visible, add them.
            if not self.video_options.parent:
                self.main_layout.add_widget(self.video_options, index)

    def choose_folder(self, instance):
        """Opens a popup with a file chooser to select the output directory."""
        content = BoxLayout(orientation='vertical')
        filechooser = FileChooserListView(path=self.output_dir, dirselect=True, size_hint=(1, 0.9))
        content.add_widget(filechooser)

        buttons = BoxLayout(size_hint=(1, 0.1), spacing=5)
        select_btn = Button(text='Select')
        cancel_btn = Button(text='Cancel')
        buttons.add_widget(select_btn)
        buttons.add_widget(cancel_btn)
        content.add_widget(buttons)

        popup = Popup(title='Choose Output Folder', content=content, size_hint=(0.9, 0.9))

        def on_select(instance):
            if filechooser.selection:
                self.output_dir = filechooser.selection[0]
                self.folder_button.text = f'Output: {os.path.basename(self.output_dir)}'
            popup.dismiss()

        select_btn.bind(on_press=on_select)
        cancel_btn.bind(on_press=popup.dismiss)
        popup.open()

    def clear_fields(self, instance):
        """Resets the input and status fields to their initial state."""
        self.url_input.text = ''
        self.progress_bar.value = 0
        self.status_label.text = 'Ready'

    def start_download(self, instance):
        """Validates input and starts the download process in a new thread."""
        urls = self.url_input.text.strip()
        if not urls:
            self.show_error('Please enter at least one URL.')
            return

        # Update UI to downloading state
        self.is_downloading = True
        self.download_button.disabled = True
        self.stop_button.disabled = False
        self.status_label.text = 'Starting download...'
        self.progress_bar.value = 0

        # Run download in a separate thread to prevent GUI from freezing.
        thread = threading.Thread(target=self.download_thread, args=(urls,))
        thread.daemon = True
        thread.start()

    def stop_download(self, instance):
        """Stops the current download process by terminating the subprocess."""
        if self.current_process:
            self.current_process.terminate()
            # The finally block in download_thread will handle the cleanup.
        self.is_downloading = False # Ensure the loop in download_thread exits
        self.status_label.text = 'Download stopped by user.'

    def download_thread(self, urls):
        """
        The core download logic. Constructs and runs a yt-dlp command
        in a subprocess for each URL.
        """
        try:
            url_list = [url.strip() for url in urls.split('\n') if url.strip()]

            for i, url in enumerate(url_list):
                if not self.is_downloading:
                    break

                Clock.schedule_once(lambda dt: setattr(self.status_label, 'text', f'Preparing download ({i+1}/{len(url_list)})...'))

                # --- Construct the yt-dlp command ---
                cmd = ['yt-dlp', url, '--newline', '--progress']

                # Output path and filename template
                output_template = os.path.join(self.output_dir, '%(title)s.%(ext)s')
                cmd.extend(['-o', output_template])

                # --- Mode-specific options ---
                if self.mode_spinner.text == 'Audio':
                    audio_format = self.audio_format_spinner.text
                    quality_str = self.audio_quality_spinner.text
                    quality_val = re.search(r'\((\d+)\)', quality_str).group(1)

                    cmd.extend(['-x', '--audio-format', audio_format, '--audio-quality', quality_val])
                else: # Video Mode
                    quality = self.video_quality_spinner.text
                    format_str = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
                    if quality != 'Best':
                        format_str = f'bestvideo[height<={quality[:-1]}][ext=mp4]+bestaudio[ext=m4a]/{format_str}'
                    cmd.extend(['-f', format_str, '--merge-output-format', 'mp4'])

                    if self.subtitles_check.active:
                        sub_lang = self.sub_lang_spinner.text
                        cmd.extend(['--write-subs', '--sub-lang', sub_lang, '--convert-subs', 'srt'])

                # Playlist handling
                if not self.playlist_check.active:
                    cmd.append('--no-playlist')
                
                cmd.append('--ignore-errors')

                # --- Execute the command ---
                self.current_process = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    text=True, encoding='utf-8', errors='replace', bufsize=1
                )

                # --- Parse stdout in real-time for progress updates ---
                for line in iter(self.current_process.stdout.readline, ''):
                    if not self.is_downloading: break # Check for user stop request

                    # Regex to find the progress percentage
                    match = re.search(r'\[download\]\s+([0-9.]+)%', line)
                    if match:
                        progress = float(match.group(1))
                        status_text = f'Downloading ({i+1}/{len(url_list)})... {progress:.1f}%'
                        # Schedule UI updates on the main thread
                        Clock.schedule_once(lambda dt, p=progress: setattr(self.progress_bar, 'value', p))
                        Clock.schedule_once(lambda dt, t=status_text: setattr(self.status_label, 'text', t))

                self.current_process.wait() # Wait for the subprocess to finish

                if self.current_process.returncode != 0 and self.is_downloading:
                    # Read stderr if an error occurred
                    error_output = self.current_process.stderr.read()
                    self.show_error(f"Error on item {i+1}: {error_output[:200]}")


            if self.is_downloading:
                Clock.schedule_once(lambda dt: setattr(self.status_label, 'text', 'All downloads finished!'))

        except FileNotFoundError:
            self.show_error('yt-dlp command not found. Please ensure it is installed and in your system\'s PATH.')
        except Exception as e:
            self.show_error(f"An unexpected error occurred: {str(e)}")
        finally:
            # This block runs whether the download succeeds, fails, or is stopped.
            self.current_process = None
            Clock.schedule_once(self.download_finished)

    def download_finished(self, *args):
        """Resets the UI to the 'ready' state after a download task completes."""
        self.is_downloading = False
        self.download_button.disabled = False
        self.stop_button.disabled = True
        self.progress_bar.value = 0 # Reset progress bar

    def show_error(self, message):
        """Displays an error message in a popup window."""
        # Ensure this is run on the main thread
        def do_popup(dt):
            popup = Popup(
                title='Error', content=Label(text=message, halign='center'),
                size_hint=(0.8, 0.4)
            )
            popup.open()
        Clock.schedule_once(do_popup)

    # --- Kivy App Lifecycle Methods ---
    def on_pause(self):
        return True # Allow the app to be paused on mobile

    def on_resume(self):
        pass # Called when the app is resumed from a paused state


# --- Application Entry Point ---
if __name__ == '__main__':
    MediaCatcherApp().run()

# -----------------------------------------------------------------------------
# Media Catcher
# Copyright (C) 2024 Markus Aureus
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
# -----------------------------------------------------------------------------
