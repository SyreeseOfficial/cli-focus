import os
import pygame
import shutil
import random
import time

# Texture mapping as requested
TEXTURE_MAP = {
    "Brown Noise": ["keyboard.mp3", "page-turn.mp3", "vinyl-crackle.mp3"],
    "City": ["distant-ambulance-siren.mp3", "distant-train.mp3", "bike-bell.mp3", "door-open-close-with-bell.mp3"],
    "Coffee Shop": ["espresso-steam.mp3", "pouring-coffee.mp3", "spoon-and-cup.mp3", "cup-and-saucer.mp3", "cash-register.mp3"],
    "Fire": ["page-turn.mp3", "vinyl-crackle.mp3", "crickets.mp3", "owl.mp3", "winter-wind.mp3"],
    "Flowing Water": ["frog.mp3", "wind-chimes.mp3", "distant-thunder.mp3"],
    "Gentle Rain": ["distant-thunder.mp3", "winter-wind.mp3", "wind-chimes.mp3"],
    "Lofi": ["vinyl-crackle.mp3", "keyboard.mp3", "page-turn.mp3", "big-bell.mp3"],
    "Omm": ["big-bell.mp3", "wind-chimes.mp3"],
    "Rain Sounds": ["distant-thunder.mp3", "winter-wind.mp3"],
    "Sea Wave": ["seagull.mp3", "distant-foghorn.mp3", "winter-wind.mp3"]
}

class AudioManager:
    def __init__(self, assets_dir="assets"):
        pygame.mixer.init()
        self.assets_dir = assets_dir
        self.sfx_dir = os.path.join(assets_dir, "sfx")
        self.textures_dir = os.path.join(assets_dir, "textures")
        
        # 1. Automatic File Setup
        self.organize_textures()
        
        self.sounds = {} # filename -> mixer.Sound
        self.sfx = {} # filename -> mixer.Sound
        self.textures = {} # filename -> mixer.Sound
        self.channels = {} # filename -> mixer.Channel
        self.playing = [] # List of filenames currently playing (loops)
        self.master_volume = 1.0
        
        # Dynamic Weather State
        self.last_texture_time = time.time()
        self.weather_freq_range = (30, 90) # Default Medium
        self.next_texture_interval = random.uniform(*self.weather_freq_range)
        
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
        self.scan_textures()

    def organize_textures(self):
        """Checks for 'noises' folder and moves files to 'assets/textures'."""
        noises_path = "noises"
        if os.path.exists(noises_path):
            if not os.path.exists(self.textures_dir):
                os.makedirs(self.textures_dir)
            
            print(f"Moving files from {noises_path} to {self.textures_dir}...")
            count = 0
            for f in os.listdir(noises_path):
                src = os.path.join(noises_path, f)
                dst = os.path.join(self.textures_dir, f)
                if os.path.isfile(src):
                    shutil.move(src, dst)
                    count += 1
            
            try:
                os.rmdir(noises_path)
            except OSError:
                print("Could not remove 'noises' directory (might not be empty).")
                
            print(f"Moved {count} texture files.")

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

    def scan_textures(self):
        if not os.path.exists(self.textures_dir):
            return

        valid_extensions = (".wav", ".mp3", ".ogg")
        for f in os.listdir(self.textures_dir):
            if f.lower().endswith(valid_extensions):
                path = os.path.join(self.textures_dir, f)
                try:
                    self.textures[f] = pygame.mixer.Sound(path)
                except Exception as e:
                    print(f"Error loading Texture {f}: {e}")

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

    def update_textures(self):
        """Called periodically to play random texture sounds."""
        now = time.time()
        
        if now - self.last_texture_time > self.next_texture_interval:
            self.play_random_texture()
            self.last_texture_time = now
            # Set next interval based on current range
            self.next_texture_interval = random.uniform(*self.weather_freq_range)

    def set_weather_frequency(self, level):
        ranges = {
            "low": (60, 120),
            "medium": (30, 90),
            "high": (15, 45)
        }
        self.weather_freq_range = ranges.get(level.lower(), (30, 90))

    def play_random_texture(self):
        if not self.playing:
            return

        # 1. Identify valid textures based on playing loops
        valid_textures = []
        
        for loop_file in self.playing:
            # Map filename to key in TEXTURE_MAP
            # We need to match loose names.
            # e.g. "rain.wav" should match "Rain Sounds" or "Gentle Rain" if possible, 
            # but the user provided specific keys. Let's try to match keys to filenames best effort.
            
            # Simple fuzzy match: check if map key is part of filename or vice versa
            loop_name_clean = os.path.splitext(loop_file)[0].replace("_", " ").replace("-", " ").lower()
            
            for key, textures in TEXTURE_MAP.items():
                if key.lower() in loop_name_clean or loop_name_clean in key.lower():
                    valid_textures.extend(textures)
        
        # If no strict match found, maybe just pick from all if we want chaos? 
        # But user asked to "link loops to new textures". 
        # If valid_textures is empty, we do nothing.
        
        if not valid_textures:
            return

        # 2. Pick one
        texture_file = random.choice(valid_textures)
        
        # 3. Play it
        if texture_file in self.textures:
            # Volume: subtle, 30-60% of master volume
            vol = self.master_volume * random.uniform(0.3, 0.6)
            self.textures[texture_file].set_volume(vol)
            self.textures[texture_file].play()
            # We don't track texture channels strictly unless we need to stop them instantly.
            # They are one-shots usually.
