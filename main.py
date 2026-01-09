import os
import time
import json
import datetime
import sys
import termios
import tty
import select
# Suppress pygame welcome message
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
import pygame
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn
from rich.panel import Panel
from rich import box
from rich.layout import Layout
from rich.align import Align
from rich.text import Text

class StatsManager:
    def __init__(self, filename="stats.json"):
        self.filename = filename
        self.stats = self.load_stats()

    def load_stats(self):
        default = {
            "total_seconds": 0.0,
            "last_session_date": None,
            "current_streak": 0
        }
        if not os.path.exists(self.filename):
            return default
        
        try:
            with open(self.filename, 'r') as f:
                data = json.load(f)
                return {**default, **data} # Merge with default to ensure keys exist
        except:
            return default

    def save_stats(self):
        with open(self.filename, 'w') as f:
            json.dump(self.stats, f, indent=2)

    def update_time(self, seconds):
        if seconds <= 0:
            return
            
        today = str(datetime.date.today())
        last_date = self.stats["last_session_date"]
        
        # Streak Logic
        if last_date != today:
            if last_date:
                # Check if consecutive day
                last_dt = datetime.datetime.strptime(last_date, "%Y-%m-%d").date()
                curr_dt = datetime.date.today()
                delta = (curr_dt - last_dt).days
                
                if delta == 1:
                    self.stats["current_streak"] += 1
                elif delta > 1:
                    self.stats["current_streak"] = 1
                # If delta < 1 (same day), do nothing
            else:
                self.stats["current_streak"] = 1
                
            self.stats["last_session_date"] = today
        
        self.stats["total_seconds"] += seconds
        self.save_stats()

    def get_display_stats(self):
        total_sec = int(self.stats["total_seconds"])
        hours = total_sec // 3600
        mins = (total_sec % 3600) // 60
        time_str = f"{hours}h {mins}m"
        
        streak = self.stats["current_streak"]
        streak_str = f"{streak} Day{'s' if streak != 1 else ''}"
        
        return time_str, streak_str

class AudioManager:
    def __init__(self, assets_dir="assets"):
        pygame.mixer.init()
        self.assets_dir = assets_dir
        self.sfx_dir = os.path.join(assets_dir, "sfx")
        self.sounds = {} # filename -> mixer.Sound
        self.sfx = {} # filename -> mixer.Sound
        self.channels = {} # filename -> mixer.Channel
        self.playing = [] # List of filenames currently playing
        self.master_volume = 1.0
        self.emojis = {
            'rain': '🌧️',
            'fire': '🔥',
            'cafe': '☕',
            'coffee': '☕',
            'brown': '🤎',
            'city': '🏙️',
            'water': '💧',
            'sea': '🌊',
            'lofi': '🎧',
            'omm': '🧘'
        }
        self.scan_assets()
        self.scan_sfx()

    def scan_assets(self):
        if not os.path.exists(self.assets_dir):
            return
        
        valid_extensions = (".wav", ".mp3", ".ogg")
        for f in os.listdir(self.assets_dir):
            if f.lower().endswith(valid_extensions):
                path = os.path.join(self.assets_dir, f)
                try:
                    self.sounds[f] = pygame.mixer.Sound(path)
                except Exception as e:
                    print(f"Error loading {f}: {e}")

    def scan_sfx(self):
        if not os.path.exists(self.sfx_dir):
            return

        valid_extensions = (".wav", ".mp3", ".ogg")
        for f in os.listdir(self.sfx_dir):
            if f.lower().endswith(valid_extensions):
                path = os.path.join(self.sfx_dir, f)
                try:
                    self.sfx[f] = pygame.mixer.Sound(path)
                except Exception as e:
                    print(f"Error loading SFX {f}: {e}")

    def play_gong(self):
        # Specific helper for the gong
        gong_file = "gong.mp3"
        if gong_file in self.sfx:
            self.sfx[gong_file].set_volume(self.master_volume)
            self.sfx[gong_file].play()

    def get_emoji(self, filename):
        # ID generic names from filename
        lower_name = filename.lower()
        for key, emoji in self.emojis.items():
            if key in lower_name:
                return emoji
        return '🎵'

    def play_sound(self, filename, fade_ms=2000):
        if filename in self.sounds:
            # Play in loop
            channel = self.sounds[filename].play(loops=-1, fade_ms=fade_ms)
            channel.set_volume(self.master_volume)
            self.channels[filename] = channel
            self.playing.append(filename)

    def set_volume(self, filename, level):
        # level 0.0 to 1.0
        if filename in self.sounds:
            self.sounds[filename].set_volume(level)

    def set_master_volume(self, level):
        self.master_volume = max(0.0, min(1.0, level))
        for filename, channel in self.channels.items():
            if channel.get_busy():
                channel.set_volume(self.master_volume)

    def stop_all(self, fade_ms=2000):
        for filename in self.playing:
            self.sounds[filename].fadeout(fade_ms)
        self.playing.clear()
        self.channels.clear()

class FocusApp:
    def __init__(self):
        self.console = Console()
        self.audio = AudioManager()
        self.stats = StatsManager()
        
    def show_menu(self):
        self.console.clear()
        self.console.print("[bold cyan]Focus Noise Player[/bold cyan] 🎧", justify="center")
        self.console.print()
        
        # Stats Panel
        time_str, streak_str = self.stats.get_display_stats()
        stats_text = f"[bold green]Total Focus:[/bold green] {time_str}  |  [bold yellow]Current Streak:[/bold yellow] {streak_str} 🔥"
        self.console.print(Panel(Align.center(stats_text), box=box.ROUNDED, style="blue"), justify="center")
        self.console.print()

        table = Table(title="Available Sounds", show_header=True, header_style="bold magenta", box=box.ROUNDED, padding=(0, 2))
        table.add_column("ID", style="dim", width=4, justify="center")
        table.add_column("Name", style="green")

        # Sort sounds for consistent ID
        sound_files = sorted(list(self.audio.sounds.keys()))
        self.sound_map = {str(i+1): f for i, f in enumerate(sound_files)}

        for i, f in enumerate(sound_files):
            idx = str(i+1)
            # Generic clean name: remove extension, replace separators
            base = os.path.splitext(f)[0]
            headers = base.replace("_", " ").replace("-", " ").title()
            table.add_row(idx, headers)

        self.console.print(table, justify="center")
        self.console.print()

    def phase_one_selection(self):
        self.show_menu()
        
        # Selection
        self.console.print("[bold yellow]Select Sound IDs (comma separated):[/bold yellow] ", end="")
        selection_str = input()
        
        # Parse selection
        selected_ids = [s.strip() for s in selection_str.split(",")]
        selected_files = []
        for sid in selected_ids:
            if sid in self.sound_map:
                selected_files.append(self.sound_map[sid])
        
        if not selected_files:
            self.console.print("[red]No valid sounds selected. Exiting.[/red]")
            return None, None, []

        # Duration
        self.console.print("[bold yellow]Session Duration (minutes):[/bold yellow] ", end="")
        try:
            minutes = float(input())
            seconds = int(minutes * 60)
        except ValueError:
            self.console.print("[red]Invalid duration. Defaulting to 25 minutes.[/red]")
            seconds = 25 * 60
            
        # Initial Volume
        self.console.print("[bold yellow]Initial Volume (0-100%):[/bold yellow] ", end="")
        try:
            vol_input = input()
            if vol_input.strip():
                vol_percent = float(vol_input)
                self.audio.set_master_volume(vol_percent / 100.0)
        except ValueError:
            self.console.print("[red]Invalid volume. Defaulting to 100%.[/red]")

        # Task Intents
        tasks = []
        self.console.print()
        self.console.print("[bold magenta]Optional: Enter up to 3 tasks for this session (press Enter to skip)[/bold magenta]")
        for i in range(3):
            self.console.print(f"[bold yellow]Task #{i+1}:[/bold yellow] ", end="")
            t = input().strip()
            if not t:
                break
            tasks.append(t)
            
        return selected_files, seconds, tasks

    def check_input(self):
        if select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], []):
            return sys.stdin.read(1)
        return None

    def run(self):
        files, duration, tasks = self.phase_one_selection()
        if not files:
            return


        # Start Audio
        for f in files:
            self.audio.play_sound(f, fade_ms=2000)

        self.console.clear()
        self.console.print("[dim]controls: +/- to adjust volume, ctrl+c to quit[/dim]")
        
        # Prepare valid emojis for footer
        playing_emojis = []
        for f in files:
            base = os.path.splitext(f)[0]
            name = base.replace("_", " ").replace("-", " ").title()
            emoji = self.audio.get_emoji(f)
            playing_emojis.append(f"{emoji} {name}")
        
            playing_emojis.append(f"{emoji} {name}")
        
        base_footer = "Playing: " + " + ".join(playing_emojis)
        def get_footer():
            return f"{base_footer} | Volume: {int(self.audio.master_volume * 100)}%"

        # Progress bar configuration
        progress = Progress(
            TextColumn("[bold blue]{task.description}"),
            BarColumn(bar_width=None),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeRemainingColumn(),
            expand=True
        )
        
        task_id = progress.add_task("Focus Session", total=duration)
        
        # Layout
        layout = Layout()
        layout.split_column(
            Layout(name="upper", size=3),
            Layout(name="center"),
            Layout(name="lower", size=3)
        )
        
        # Configure center layout based on tasks
        if tasks:
            layout["center"].split_column(
                Layout(name="timer"),
                Layout(name="tasks", size=len(tasks) + 4)
            )
            timer_layout = layout["center"]["timer"]
            tasks_layout = layout["center"]["tasks"]
        else:
            timer_layout = layout["center"]
        
        # Initial View
        old_settings = termios.tcgetattr(sys.stdin)
        try:
            tty.setcbreak(sys.stdin.fileno())
            with Live(layout, refresh_per_second=4, screen=True) as live:
                start_time = time.time()
                while True:
                    elapsed = time.time() - start_time
                    remaining = duration - elapsed
                    
                    if remaining <= 0:
                        break
                    
                    # Input Handling
                    key = self.check_input()
                    if key:
                        if key in ('+', 'w', '='): # = is unshifted +
                            self.audio.set_master_volume(self.audio.master_volume + 0.05)
                        elif key in ('-', 's'):
                            self.audio.set_master_volume(self.audio.master_volume - 0.05)

                    # Update Progress
                    progress.update(task_id, completed=elapsed)
                    
                    # Update Layout details
                    layout["upper"].update(Align.center(Text("Focus Noise Player", style="bold cyan")))
                    
                    # We render progress into a panel for the center
                    timer_layout.update(
                        Panel(progress, title="Time Remaining", border_style="green")
                    )
                    
                    if tasks:
                        task_table = Table.grid(padding=(0, 1))
                        task_table.add_column(style="bold yellow", justify="right")
                        task_table.add_column(style="white")
                        for i, t in enumerate(tasks):
                            task_table.add_row(f"{i+1}.", t)
                        
                        tasks_layout.update(
                            Panel(Align.center(task_table), title="Current Tasks", border_style="magenta")
                        )
                    
                    layout["lower"].update(
                        Panel(Align.center(Text(get_footer(), style="dim")))
                    )
                    
                    time.sleep(0.1) # Faster poll for input responsiveness
            
            # Save stats
            elapsed_total = time.time() - start_time
            self.stats.update_time(elapsed_total)
            
            self.console.print("[dim]Fading out...[/dim]")
            self.audio.stop_all(fade_ms=2000)
            time.sleep(2.0)
            
            # Play Gong
            self.audio.play_gong()
            time.sleep(4.0) # Wait for gong to ring out
            
            self.console.print("[bold green]Session Complete![/bold green] 🎉")
            self.console.print(f"[dim]Stats Saved: +{int(elapsed_total/60)}m focus time[/dim]")
            
        except KeyboardInterrupt:
            # Save stats on interrupt too
            elapsed_total = time.time() - start_time
            self.stats.update_time(elapsed_total)
            
            self.console.print("\n[dim]Fading out...[/dim]")
            self.audio.stop_all(fade_ms=2000)
            time.sleep(2.0)
            self.console.print("\n[bold red]Session Stopped.[/bold red] 👋")
            self.console.print(f"[dim]Stats Saved: +{int(elapsed_total/60)}m focus time[/dim]")
        finally:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)

if __name__ == "__main__":
    app = FocusApp()
    app.run()
