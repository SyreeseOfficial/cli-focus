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
import traceback
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn, SpinnerColumn
from rich.panel import Panel
from rich import box
from rich.layout import Layout
from rich.align import Align
from rich.text import Text
from audio_manager import AudioManager

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

    def reset_stats(self):
        self.stats = {
            "total_seconds": 0.0,
            "last_session_date": None,
            "current_streak": 0
        }
        self.save_stats()

class SettingsManager:
    def __init__(self, filename="settings.json"):
        self.filename = filename
        self.settings = self.load_settings()

    def load_settings(self):
        default = {
            "volume": 100,
            "timer_duration": 25,
            "show_timer": True,
            "play_gong": True,
            "dynamic_weather": True,
            "theme_color": "cyan",
            "volume_step": 5,
            "auto_start": False,
            "weather_freq": "medium",
            "fade_duration": 2.0,
            "confirm_exit": False
        }
        if not os.path.exists(self.filename):
            return default
        try:
            with open(self.filename, 'r') as f:
                data = json.load(f)
                return {**default, **data}
        except:
            return default

    def save_settings(self):
        with open(self.filename, 'w') as f:
            json.dump(self.settings, f, indent=2)

    def get(self, key, default=None):
        return self.settings.get(key, default)

    def set(self, key, value):
        self.settings[key] = value
        self.save_settings()

class FocusApp:
    def __init__(self):
        self.console = Console()
        self.audio = AudioManager()
        self.stats = StatsManager()
        self.settings = SettingsManager()
        
    @property
    def theme_color(self):
        return self.settings.get("theme_color", "cyan")

    def show_menu(self):
        self.console.clear()
        tc = self.theme_color
        self.console.print(f"[bold {tc}]Focus Noise Player[/bold {tc}] 🎧", justify="center")
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
        self.console.print(Panel("[bold yellow]S[/bold yellow] - Settings", box=box.SIMPLE), justify="center")
        self.console.print()

    def settings_menu(self):
        vol_steps = [1, 5, 10]
        weather_freqs = ["low", "medium", "high"]
        fade_durations = [1.0, 2.0, 3.0, 5.0]
        theme_colors = ["cyan", "green", "magenta", "blue", "yellow", "red"]

        while True:
            self.console.clear()
            tc = self.theme_color
            self.console.print(f"[bold {tc}]Settings[/bold {tc}] ⚙️", justify="center")
            self.console.print()
            
            table = Table(box=box.ROUNDED, show_header=True, header_style=f"bold {tc}")
            table.add_column("Option", style="yellow")
            table.add_column("Value", style="green")
            table.add_column("Description", style="dim italic")
            
            # Helper to format boolean
            def fmt_bool(val): return "ON" if val else "OFF"
            
            table.add_row("1. Default Volume", f"{self.settings.get('volume')}%", "Startup volume level")
            table.add_row("2. Default Duration", f"{self.settings.get('timer_duration')} min", "Startup session length")
            table.add_row("3. Show Timer", fmt_bool(self.settings.get('show_timer')), "Toggle countdown visibility")
            table.add_row("4. Play Gong", fmt_bool(self.settings.get('play_gong')), "Sound at session end")
            table.add_row("5. Dynamic Weather", fmt_bool(self.settings.get('dynamic_weather')), "Random background SFX")
            table.add_row("6. Theme Color", f"[{self.settings.get('theme_color')}]{self.settings.get('theme_color').title()}[/]", "UI accent color")
            table.add_row("7. Volume Step", f"{self.settings.get('volume_step')}%", "Adjustment increment")
            table.add_row("8. Auto-Start", fmt_bool(self.settings.get('auto_start')), "Skip setup if sounds selected")
            table.add_row("9. Weather Freq", f"{self.settings.get('weather_freq').title()}", "How often textures play")
            table.add_row("10. Fade Duration", f"{self.settings.get('fade_duration')}s", "Stop fade-out time")
            table.add_row("11. Confirm Exit", fmt_bool(self.settings.get('confirm_exit')), "Prompt before quitting")
            table.add_row("12. Reset Stats", "[red]Action[/red]", "Clear all progress data")
            
            self.console.print(table, justify="center")
            self.console.print()
            self.console.print("[dim]Enter number to change, or 'b' to back[/dim]", justify="center")
            
            choice = input("\nSelect: ").strip().lower()
            
            if choice == 'b':
                break
            elif choice == '1':
                try:
                    val = int(input("Enter default volume (0-100): "))
                    if 0 <= val <= 100:
                        self.settings.set('volume', val)
                except ValueError:
                    pass
            elif choice == '2':
                try:
                    val = int(input("Enter default duration (min): "))
                    if val > 0:
                        self.settings.set('timer_duration', val)
                except ValueError:
                    pass
            elif choice == '3':
                self.settings.set('show_timer', not self.settings.get('show_timer'))
            elif choice == '4':
                self.settings.set('play_gong', not self.settings.get('play_gong'))
            elif choice == '5':
                self.settings.set('dynamic_weather', not self.settings.get('dynamic_weather'))
            elif choice == '6':
                current = self.settings.get('theme_color')
                try:
                    idx = theme_colors.index(current)
                    next_idx = (idx + 1) % len(theme_colors)
                except ValueError:
                    next_idx = 0
                self.settings.set('theme_color', theme_colors[next_idx])
            elif choice == '7':
                current = self.settings.get('volume_step')
                try:
                    idx = vol_steps.index(current)
                    next_idx = (idx + 1) % len(vol_steps)
                except ValueError:
                    next_idx = 1 # Default to 5
                self.settings.set('volume_step', vol_steps[next_idx])
            elif choice == '8':
                self.settings.set('auto_start', not self.settings.get('auto_start'))
            elif choice == '9':
                current = self.settings.get('weather_freq', 'medium')
                try:
                    idx = weather_freqs.index(current)
                    next_idx = (idx + 1) % len(weather_freqs)
                except ValueError:
                    next_idx = 1
                self.settings.set('weather_freq', weather_freqs[next_idx])
            elif choice == '10':
                current = self.settings.get('fade_duration', 2.0)
                try:
                    idx = fade_durations.index(current)
                    next_idx = (idx + 1) % len(fade_durations)
                except ValueError:
                    next_idx = 1
                self.settings.set('fade_duration', fade_durations[next_idx])
            elif choice == '11':
                self.settings.set('confirm_exit', not self.settings.get('confirm_exit'))
            elif choice == '12':
                confirm = input("Are you sure you want to reset all stats? (y/n): ").lower()
                if confirm == 'y':
                    self.stats.reset_stats()
                    self.console.print("[green]Stats reset![/green]")
                    time.sleep(1)

    def phase_one_selection(self):
        while True:
            self.show_menu()
            
            # Selection
            self.console.print("[bold yellow]Select Sound IDs (comma separated) or 'S' for Settings:[/bold yellow] ", end="")
            selection_str = input().strip()
            
            if selection_str.lower() == 's':
                self.settings_menu()
                continue
            
            # Parse selection
            selected_ids = [s.strip() for s in selection_str.split(",")]
            selected_files = []
            valid_selection = False
            
            for sid in selected_ids:
                if sid in self.sound_map:
                    selected_files.append(self.sound_map[sid])
                    valid_selection = True
            
            if not valid_selection:
                if not selection_str: # Allow simple enter to refresh or nothing
                     self.console.print("[red]No valid sounds selected.[/red]")
                     time.sleep(1)
                     continue
                
                self.console.print("[red]No valid sounds selected. Exiting.[/red]")
                return None, None, []
                
            break
        
        # Duration
        default_duration = self.settings.get("timer_duration")
        
        # Auto-Start Logic: If auto_start is ON, use defaults immediately
        if self.settings.get("auto_start"):
            self.console.print(f"\n[italic {self.theme_color}]Auto-starting with default duration ({default_duration}m) and volume ({self.settings.get('volume')}%)[/italic {self.theme_color}]")
            time.sleep(1)
            seconds = int(default_duration * 60)
            vol_percent = float(self.settings.get("volume"))
            self.audio.set_master_volume(vol_percent / 100.0)
            return selected_files, seconds, [] # Auto-start skips task entry for speed

        self.console.print(f"[bold yellow]Session Duration (minutes) [{default_duration}]:[/bold yellow] ", end="")
        try:
            dur_input = input().strip()
            if not dur_input:
                minutes = float(default_duration)
            else:
                minutes = float(dur_input)
            seconds = int(minutes * 60)
        except ValueError:
            self.console.print(f"[red]Invalid duration. Defaulting to {default_duration} minutes.[/red]")
            seconds = int(default_duration * 60)
            
        # Initial Volume
        default_vol = self.settings.get("volume")
        self.console.print(f"[bold yellow]Initial Volume (0-100%) [{default_vol}]:[/bold yellow] ", end="")
        try:
            vol_input = input().strip()
            if not vol_input:
                vol_percent = float(default_vol)
            else:
                vol_percent = float(vol_input)
            self.audio.set_master_volume(vol_percent / 100.0)
        except ValueError:
            self.console.print(f"[red]Invalid volume. Using default {default_vol}%.[/red]")
            self.audio.set_master_volume(default_vol / 100.0)

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
        fade_ms = int(self.settings.get("fade_duration", 2.0) * 1000)
        for f in files:
            self.audio.play_sound(f, fade_ms=fade_ms)
        
        # Apply Weather Frequency
        self.audio.set_weather_frequency(self.settings.get("weather_freq", "medium"))

        self.console.clear()
        self.console.print("[dim]controls: +/- to adjust volume, ctrl+c to quit[/dim]")
        
        # Prepare valid emojis for footer
        playing_emojis = []
        for f in files:
            base = os.path.splitext(f)[0]
            name = base.replace("_", " ").replace("-", " ").title()
            emoji = self.audio.get_emoji(f)
            playing_emojis.append(f"{emoji} {name}")
        
        base_footer = "Playing: " + " + ".join(playing_emojis)
        def get_footer():
            return f"{base_footer} | Volume: {int(self.audio.master_volume * 100)}%"


        # Progress bar configuration
        # Check settings for timer visibility
        show_timer = self.settings.get("show_timer")
        
        columns = [
            SpinnerColumn(style="bold yellow"),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(bar_width=None, complete_style="bold magenta", finished_style="bold green"),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        ]
        
        if show_timer:
            columns.append(TimeRemainingColumn())
            
        progress = Progress(*columns, expand=True)
        
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
                    
                    # Periodic Dynamic Weather Update
                    if self.settings.get("dynamic_weather", True):
                        self.audio.update_textures()
                    
                    # Input Handling
                    key = self.check_input()
                    if key:
                        step = self.settings.get("volume_step", 5) / 100.0
                        if key in ('+', 'w', '='): # = is unshifted +
                            self.audio.set_master_volume(self.audio.master_volume + step)
                        elif key in ('-', 's'):
                            self.audio.set_master_volume(self.audio.master_volume - step)

                    # Update Progress
                    progress.update(task_id, completed=elapsed)
                    
                    # Update Layout details
                    # Update Layout details
                    layout["upper"].update(Align.center(Text("Focus Noise Player", style=f"bold {self.theme_color}")))
                    
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
            fade_ms = int(self.settings.get("fade_duration", 2.0) * 1000)
            self.audio.stop_all(fade_ms=fade_ms)
            time.sleep(self.settings.get("fade_duration", 2.0))
            
            # Play Gong
            if self.settings.get("play_gong", True):
                self.audio.play_gong()
                time.sleep(4.0) # Wait for gong to ring out
            
            self.console.print("[bold green]Session Complete![/bold green] 🎉")
            self.console.print(f"[dim]Stats Saved: +{int(elapsed_total/60)}m focus time[/dim]")
            
        except Exception:
            # Capture any rendering or logic errors in the live loop
            self.console.print("\n[bold red]Dashboard Error:[/bold red]")
            self.console.print(traceback.format_exc())
            self.audio.stop_all(fade_ms=1000)
        except KeyboardInterrupt:
            # Confirm Exit Check
            if self.settings.get("confirm_exit", False):
                self.console.print("\n[bold red]Exit requested. Confirm? (y/n): [/bold red]", end="")
                try:
                    confirm = input().strip().lower()
                    if confirm != 'y':
                        self.console.print("[dim]Resuming not supported yet. Exiting...[/dim]")
                except:
                    pass

            # Save stats on interrupt too
            try:
                elapsed_total = time.time() - start_time
                self.stats.update_time(elapsed_total)
            except NameError:
                pass
            
            self.console.print("\n[dim]Fading out...[/dim]")
            fade_ms = int(self.settings.get("fade_duration", 2.0) * 1000)
            self.audio.stop_all(fade_ms=fade_ms)
            time.sleep(self.settings.get("fade_duration", 2.0))
            self.console.print("\n[bold red]Session Stopped.[/bold red] 👋")
            try:
                self.console.print(f"[dim]Stats Saved: +{int(elapsed_total/60)}m focus time[/dim]")
            except NameError:
                pass
        finally:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)

if __name__ == "__main__":
    try:
        app = FocusApp()
        app.run()
    except KeyboardInterrupt:
        print("\n\nGoodbye! 👋")
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)
