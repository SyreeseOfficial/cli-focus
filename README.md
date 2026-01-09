# FocusNoiseCLI

FocusNoiseCLI is a terminal-based focus tool that plays ambient noises (brown noise, rain, cafe interaction) to help you get into the flow state. It features a rich TUI (Text User Interface) with progress tracking, gamification (ranks, streaks), and dynamic weather soundscapes.

## Features

- **Ambient Audio**: Choose from Brown Noise, Rain, Cafe, and more.
- **Dynamic Weather**: Audio textures change over time for an organic feel.
- **Gamification**: Earn ranks like "Terminal Tourist" to "Time Lord" based on focus hours.
- **Focus Timer**: Customizable Pomodoro-style timer with optional visual countdown.
- **System Logs**: "Hacker-style" system messages and occasional "Ghost" easter eggs.
- **Task Intent**: Optional task entry to keep your session purpose clear.
- **Receipts**: Get a generated "receipt" summary at the end of every session.

## Installation

1.  Clone the repository:
    ```bash
    git clone https://github.com/SyreeseOfficial/FocusNoiseCLI.git
    cd FocusNoiseCLI
    ```

2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

    *Note: Requires `pygame` and `rich`.*

3.  (Optional) Setup Assets:
    If you don't have custom assets, generate placeholders:
    ```bash
    python setup_assets.py
    ```

## Usage

Run the application:

```bash
python main.py
```

### Controls

- **Sound Selection**: Enter the ID(s) of the sounds you want to layer (e.g., `1,3`).
- **Settings**: Enter `s` in the main menu to configure volume, timer, colors, and more.
- **Volume**: Use `+` / `-` keys during the session.
- **Quit**: Press `Ctrl+C` to exit.

## Configuration

Settings and stats are saved automatically to your user configuration directory (e.g., `~/.config/focus-cli` on Linux).

## License

MIT
