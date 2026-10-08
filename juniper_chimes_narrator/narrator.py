#!/usr/bin/env python3
"""
juniper_chimes_narrator.narrator
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Band Director Narrator Library for Microtonal (N-EDO) Chimes.

Features:
- Band Director voice caller for minute chord changes (polychords)
  and 7-minute key transitions (previous key completed vs. new key beginning).
- Microtonal phonetic translator handling 12, 24, 31, and N-EDO note names,
  accidental symbols (𝄳, 𝄲, ♭, #), and pitch offsets (+1, -1).
- Synchronized speech delivery tuned to 120 BPM quarter notes / 8th note cadence.
- WAV generation with silence padding and caching.
"""

import os
import re
import time
import wave
import json
import asyncio
import threading
import websockets
import numpy as np
import pyttsx3
from scipy.io import wavfile

CACHE_DIR = os.path.join(os.path.dirname(__file__), "narration_cache")
os.makedirs(CACHE_DIR, exist_ok=True)

CHORD_INTERVAL_SEC = 60       # 1 minute per chord shift
KEY_INTERVAL_SEC = 420        # 7 minutes per key (7 chords per mode)


# ==============================================================================
# MUSICAL NOTATION PHONETIC TRANSLATOR (N-EDO COMPATIBLE)
# ==============================================================================
#class MicrotonalPhoneticTranslator:
#    """Translates chord quality codes, key names, and N-EDO microtonal accidentals
#
#    into spoken English text for PyTTSx3.
#    """
#
#    @staticmethod
#    def clean_scale_name(text: str) -> str:
#        if not text:
#            return ""
#        # Remove "Mode X: " prefixes
#        cleaned = re.sub(r'Mode\s+\d+:\s*', '', str(text))
#        # Remove octave suffixes like "_4" in N-EDO pitch names
#        cleaned = re.sub(r'_\d+', '', cleaned)
#        return cleaned.strip()
#
#    @classmethod
#    def phoneticize(cls, text: str) -> str:
#        if not text:
#            return ""
#
#        s = cls.clean_scale_name(text)
#
#        # Microtonal 24-EDO Unicode accidental translation
#        s = s.replace('𝄳', ' quarter sharp ')
#        s = s.replace('𝄲', ' quarter flat ')
#        s = s.replace('♭', ' flat ')
#        s = s.replace('♯', ' sharp ')
#
#        # N-EDO Step Offsets (e.g., C+1, D-2)
#        s = re.sub(r'([A-G])\+(\d+)', r'\1 plus \2', s)
#        s = re.sub(r'([A-G])\-(\d+)', r'\1 minus \2', s)
#
#        # Standard flat/sharp symbol normalization
#        s = re.sub(r'([A-G])b\b', r'\1 flat', s)
#        s = re.sub(r'([A-G])#\b', r'\1 sharp', s)
#        s = s.replace('#', ' sharp ')
#
#        # EDO System pronunciation
#        s = re.sub(r'(\d+)-EDO', r'\1 E D O', s, flags=re.IGNORECASE)
#
#        # Chord quality expansion
#        s = re.sub(r'\bMaj7\b', ' Major 7', s)
#        s = re.sub(r'\bMaj\b', ' Major', s)
#        s = re.sub(r'\bmin7\b', ' minor 7', s)
#        s = re.sub(r'\bm7b5\b', ' minor 7 flat 5', s)
#        s = re.sub(r'\bm7\b', ' minor 7', s)
#        s = re.sub(r'\bm\(Maj7\)', ' minor Major 7', s)
#        s = re.sub(r'\bdim7\b', ' diminished 7', s)
#        s = re.sub(r'\bdim\b', ' diminished', s)
#        s = re.sub(r'\bsus4\b', ' suspended 4', s)
#        s = re.sub(r'\bsus2\b', ' suspended 2', s)
#
#        # Standalone 'm' after pitch root (e.g., 'Am', 'F#m')
#        s = re.sub(r'([A-G](?: flat| sharp| plus \d+| minus \d+)?)m(\d|\b)', r'\1 minor \2', s)
#
#        # Interval alterations (e.g., b5, #5)
#        s = re.sub(r'\bb(\d)\b', r' flat \1', s)
#
#        # Normalize whitespace
#        return re.sub(r'\s+', ' ', s).strip()
# ==============================================================================
# MUSICAL NOTATION PHONETIC TRANSLATOR (N-EDO COMPATIBLE)
# ==============================================================================
#class MicrotonalPhoneticTranslator:
#    """Translates chord quality codes, key names, and N-EDO microtonal accidentals
#    into spoken English text for PyTTSx3.
#    """
#
#    @staticmethod
#    def clean_scale_name(text: str) -> str:
#        if not text:
#            return ""
#        # Remove "Mode X: " prefixes
#        cleaned = re.sub(r'Mode\s+\d+:\s*', '', str(text))
#        # Remove octave suffixes like "_4" in N-EDO pitch names
#        cleaned = re.sub(r'_\d+', '', cleaned)
#        return cleaned.strip()
#
#    @classmethod
#    def phoneticize(cls, text: str) -> str:
#        if not text:
#            return ""
#
#        s = cls.clean_scale_name(text)
#
#        # Microtonal 24-EDO Unicode accidental translation
#        s = s.replace('𝄳', ' quarter sharp ')
#        s = s.replace('𝄲', ' quarter flat ')
#        s = s.replace('♭', ' flat ')
#        s = s.replace('♯', ' sharp ')
#
#        # N-EDO Step Offsets (e.g., C+1, D-2)
#        s = re.sub(r'([A-G])\+(\d+)', r'\1 plus \2', s)
#        s = re.sub(r'([A-G])\-(\d+)', r'\1 minus \2', s)
#
#        # Standard flat/sharp symbol normalization
#        s = re.sub(r'([A-G])b\b', r'\1 flat', s)
#        s = re.sub(r'([A-G])#\b', r'\1 sharp', s)
#        s = s.replace('#', ' sharp ')
#
#        # EDO System pronunciation
#        s = re.sub(r'(\d+)-EDO', r'\1 E D O', s, flags=re.IGNORECASE)
#
#        # 1. Complex & Parenthetical Chord Qualities (Evaluated before generic Maj/m expansions)
#        s = re.sub(r'\bm\s*\(\s*Maj(?:or)?\s*7\s*\)\s*b5\b', ' minor Major 7 flat 5', s, flags=re.IGNORECASE)
#        s = re.sub(r'\bm\s*\(\s*Maj(?:or)?\s*7\s*\)', ' minor Major 7', s, flags=re.IGNORECASE)
#        s = re.sub(r'\bm\s*\(\s*Maj(?:or)?\s*\)', ' minor Major', s, flags=re.IGNORECASE)
#
#        # 2. Specific Compound Chord Qualities
#        s = re.sub(r'\bm7b5\b', ' minor 7 flat 5', s)
#        s = re.sub(r'\bMaj7#5\b', ' Major 7 sharp 5', s)
#        s = re.sub(r'\bMaj7b5\b', ' Major 7 flat 5', s)
#        s = re.sub(r'\b7#5\b', ' 7 sharp 5', s)
#        s = re.sub(r'\b7b5\b', ' 7 flat 5', s)
#        s = re.sub(r'\b7sus4\b', ' 7 suspended 4', s)
#        s = re.sub(r'\b7sus2\b', ' 7 suspended 2', s)
#        s = re.sub(r'\bsus4\b', ' suspended 4', s)
#        s = re.sub(r'\bsus2\b', ' suspended 2', s)
#        s = re.sub(r'\bdim7\b', ' diminished 7', s)
#        s = re.sub(r'\bdim\b', ' diminished', s)
#
#        # 3. Standard Quality Abbreviations
#        s = re.sub(r'\bMaj7\b', ' Major 7', s)
#        s = re.sub(r'\bMaj\b', ' Major', s)
#        s = re.sub(r'\bmin7\b', ' minor 7', s)
#        s = re.sub(r'\bmin\b', ' minor', s)
#        s = re.sub(r'\bm7\b', ' minor 7', s)
#
#        # 4. Standalone 'm' after root pitch (e.g., 'F m', 'Fm', 'D minus 1 m')
#        s = re.sub(r'(\b[A-G](?:\s+(?:flat|sharp|plus\s+\d+|minus\s+\d+))?)\s*m(?=\s+|\d|\b)', r'\1 minor ', s)
#
#        # 5. Interval alterations (e.g., b5, #5)
#        s = re.sub(r'\bb(\d)\b', r' flat \1', s)
#
#        # Normalize whitespace
#        return re.sub(r'\s+', ' ', s).strip()
# ==============================================================================
# MUSICAL NOTATION PHONETIC TRANSLATOR (N-EDO COMPATIBLE)
# ==============================================================================
#class MicrotonalPhoneticTranslator:
#    """Translates chord quality codes, key names, and N-EDO microtonal accidentals
#    into spoken English text for PyTTSx3.
#    """
#
#    @staticmethod
#    def clean_scale_name(text: str) -> str:
#        if not text:
#            return ""
#        # Remove "Mode X: " prefixes
#        cleaned = re.sub(r'Mode\s+\d+:\s*', '', str(text))
#        # Remove octave suffixes like "_4" in N-EDO pitch names
#        cleaned = re.sub(r'_\d+', '', cleaned)
#        return cleaned.strip()
#
#    @classmethod
#    def phoneticize(cls, text: str) -> str:
#        if not text:
#            return ""
#
#        s = cls.clean_scale_name(text)
#
#        # Microtonal 24-EDO Unicode accidental translation
#        s = s.replace('𝄳', ' quarter sharp ')
#        s = s.replace('𝄲', ' quarter flat ')
#        s = s.replace('♭', ' flat ')
#        s = s.replace('♯', ' sharp ')
#
#        # N-EDO Step Offsets (e.g., C+1, D-2)
#        s = re.sub(r'([A-G])\+(\d+)', r'\1 plus \2', s)
#        s = re.sub(r'([A-G])\-(\d+)', r'\1 minus \2', s)
#
#        # Standard flat/sharp symbol normalization attached to root pitches
#        s = re.sub(r'([A-G])b(?=[a-z0-9\(]|\b)', r'\1 flat ', s)
#        s = re.sub(r'([A-G])#(?=[a-z0-9\(]|\b)', r'\1 sharp ', s)
#        s = re.sub(r'([A-G])b\b', r'\1 flat', s)
#        s = re.sub(r'([A-G])#\b', r'\1 sharp', s)
#
#        # Separate glued root pitches (e.g., 'Am7b5' -> 'A m7b5', 'GMaj7' -> 'G Maj7', 'C7sus4' -> 'C 7sus4')
#        s = re.sub(
#            r'(\b[A-G](?:\s+(?:flat|sharp|quarter\s+flat|quarter\s+sharp|plus\s+\d+|minus\s+\d+))?)(?=[a-z0-9\(])',
#            r'\1 ',
#            s,
#            flags=re.IGNORECASE
#        )
#
#        # Replace standalone '#' symbol
#        s = s.replace('#', ' sharp ')
#
#        # EDO System pronunciation
#        s = re.sub(r'(\d+)-EDO', r'\1 E D O', s, flags=re.IGNORECASE)
#
#        # 1. Complex & Parenthetical Chord Qualities (Evaluated before generic Maj/m expansions)
#        s = re.sub(r'\bm\s*\(\s*Maj(?:or)?\s*7\s*\)\s*b5\b', ' minor Major 7 flat 5', s, flags=re.IGNORECASE)
#        s = re.sub(r'\bm\s*\(\s*Maj(?:or)?\s*7\s*\)', ' minor Major 7', s, flags=re.IGNORECASE)
#        s = re.sub(r'\bm\s*\(\s*Maj(?:or)?\s*\)', ' minor Major', s, flags=re.IGNORECASE)
#
#        # 2. Specific Compound Chord Qualities
#        s = re.sub(r'\bm7b5\b', ' minor 7 flat 5', s)
#        s = re.sub(r'\bMaj7#5\b', ' Major 7 sharp 5', s)
#        s = re.sub(r'\bMaj7\s*sharp\s*5\b', ' Major 7 sharp 5', s, flags=re.IGNORECASE)
#        s = re.sub(r'\bMaj7b5\b', ' Major 7 flat 5', s)
#        s = re.sub(r'\bMaj7\s*flat\s*5\b', ' Major 7 flat 5', s, flags=re.IGNORECASE)
#        s = re.sub(r'\b7#5\b', ' 7 sharp 5', s)
#        s = re.sub(r'\b7b5\b', ' 7 flat 5', s)
#        s = re.sub(r'\b7sus4\b', ' 7 suspended 4', s)
#        s = re.sub(r'\b7sus2\b', ' 7 suspended 2', s)
#        s = re.sub(r'\bsus4\b', ' suspended 4', s)
#        s = re.sub(r'\bsus2\b', ' suspended 2', s)
#        s = re.sub(r'\bdim7\b', ' diminished 7', s)
#        s = re.sub(r'\bdim\b', ' diminished', s)
#
#        # 3. Standard Quality Abbreviations
#        s = re.sub(r'\bMaj7\b', ' Major 7', s)
#        s = re.sub(r'\bMaj\b', ' Major', s)
#        s = re.sub(r'\bmin7\b', ' minor 7', s)
#        s = re.sub(r'\bmin\b', ' minor', s)
#        s = re.sub(r'\bm7\b', ' minor 7', s)
#
#        # 4. Standalone 'm' after root pitch (e.g., 'F m', 'Fm', 'D minus 1 m')
#        s = re.sub(r'(\b[A-G](?:\s+(?:flat|sharp|plus\s+\d+|minus\s+\d+))?)\s*m(?=\s+|\d|\b)', r'\1 minor ', s)
#
#        # 5. Interval alterations (e.g., b5, #5)
#        s = re.sub(r'\bb(\d)\b', r' flat \1', s)
#        s = re.sub(r'\b#(\d)\b', r' sharp \1', s)
#
#        # Normalize whitespace
#        return re.sub(r'\s+', ' ', s).strip()
# ==============================================================================
# MUSICAL NOTATION PHONETIC TRANSLATOR (N-EDO COMPATIBLE)
# ==============================================================================
#class MicrotonalPhoneticTranslator:
#    """Translates chord quality codes, key names, and N-EDO microtonal accidentals
#    into spoken English text for PyTTSx3.
#    """
#
#    @staticmethod
#    def clean_scale_name(text: str) -> str:
#        if not text:
#            return ""
#        # Remove "Mode X: " prefixes
#        cleaned = re.sub(r'Mode\s+\d+:\s*', '', str(text))
#        # Remove octave suffixes like "_4" in N-EDO pitch names
#        cleaned = re.sub(r'_\d+', '', cleaned)
#        return cleaned.strip()
#
#    @classmethod
#    def phoneticize(cls, text: str) -> str:
#        if not text:
#            return ""
#
#        s = cls.clean_scale_name(text)
#
#        # 1. EDO System pronunciation (e.g. 31-EDO -> 31 E D O)
#        s = re.sub(r'(\d+)-EDO\b', r'\1 E D O', s, flags=re.IGNORECASE)
#
#        # 2. Microtonal & Unicode accidental symbol translation
#        s = s.replace('𝄳', ' quarter sharp ')
#        s = s.replace('𝄲', ' quarter flat ')
#        s = s.replace('♭', ' flat ')
#        s = s.replace('♯', ' sharp ')
#
#        # 3. N-EDO Step Offsets (e.g., C+1, D-2)
#        s = re.sub(r'([A-G])\+(\d+)', r'\1 plus \2', s)
#        s = re.sub(r'([A-G])\-(\d+)', r'\1 minus \2', s)
#
#        # 4. Standard flat/sharp accidental symbols attached to root pitches
#        s = re.sub(r'([A-G])b(?=[a-z0-9\(]|\b)', r'\1 flat ', s)
#        s = re.sub(r'([A-G])#(?=[a-z0-9\(]|\b)', r'\1 sharp ', s)
#
#        # 5. Separate glued root pitches (e.g., 'Am7b5' -> 'A m7b5', 'GMaj7' -> 'G Maj7')
#        # Do NOT use re.IGNORECASE here so lowercase 'f', 'e', 'b' in words are not matched as pitch roots!
#        s = re.sub(
#            r'(\b[A-G](?:\s+(?:flat|sharp|quarter\s+flat|quarter\s+sharp|plus\s+\d+|minus\s+\d+))?)(?=[a-z0-9\(])',
#            r'\1 ',
#            s
#        )
#
#        # 6. Replace remaining standalone '#'
#        s = s.replace('#', ' sharp ')
#
#        # 7. Complex & Parenthetical Chord Qualities (Evaluated before generic Maj/m expansions)
#        s = re.sub(r'\bm\s*\(\s*Maj(?:or)?\s*7\s*\)\s*b5\b', ' minor Major 7 flat 5', s, flags=re.IGNORECASE)
#        s = re.sub(r'\bm\s*\(\s*Maj(?:or)?\s*7\s*\)', ' minor Major 7', s, flags=re.IGNORECASE)
#        s = re.sub(r'\bm\s*\(\s*Maj(?:or)?\s*\)', ' minor Major', s, flags=re.IGNORECASE)
#
#        # 8. Specific Compound Chord Qualities
#        s = re.sub(r'\bm7b5\b', ' minor 7 flat 5', s)
#        s = re.sub(r'\bMaj7#5\b', ' Major 7 sharp 5', s)
#        s = re.sub(r'\bMaj7\s*sharp\s*5\b', ' Major 7 sharp 5', s, flags=re.IGNORECASE)
#        s = re.sub(r'\bMaj7b5\b', ' Major 7 flat 5', s)
#        s = re.sub(r'\bMaj7\s*flat\s*5\b', ' Major 7 flat 5', s, flags=re.IGNORECASE)
#        s = re.sub(r'\b7#5\b', ' 7 sharp 5', s)
#        s = re.sub(r'\b7b5\b', ' 7 flat 5', s)
#        s = re.sub(r'\b7sus4\b', ' 7 suspended 4', s)
#        s = re.sub(r'\b7sus2\b', ' 7 suspended 2', s)
#        s = re.sub(r'\bsus4\b', ' suspended 4', s)
#        s = re.sub(r'\bsus2\b', ' suspended 2', s)
#        s = re.sub(r'\bdim7\b', ' diminished 7', s)
#        s = re.sub(r'\bdim\b', ' diminished', s)
#
#        # 9. Standard Quality Abbreviations
#        s = re.sub(r'\bMaj7\b', ' Major 7', s)
#        s = re.sub(r'\bMaj\b', ' Major', s)
#        s = re.sub(r'\bmin7\b', ' minor 7', s)
#        s = re.sub(r'\bmin\b', ' minor', s)
#        s = re.sub(r'\bm7\b', ' minor 7', s)
#
#        # 10. Standalone 'm' after root pitch (e.g., 'F m', 'Fm', 'D minus 1 m')
#        s = re.sub(r'(\b[A-G](?:\s+(?:flat|sharp|plus\s+\d+|minus\s+\d+))?)\s*m(?=\s+|\d|\b)', r'\1 minor ', s)
#
#        # 11. Interval alterations (e.g., b5, #5)
#        s = re.sub(r'\bb(\d)\b', r' flat \1', s)
#        s = re.sub(r'\b#(\d)\b', r' sharp \1', s)
#
#        # Normalize whitespace
#        return re.sub(r'\s+', ' ', s).strip()
# ==============================================================================
# MUSICAL NOTATION PHONETIC TRANSLATOR (N-EDO COMPATIBLE)
# ==============================================================================
class MicrotonalPhoneticTranslator:
    """Translates chord quality codes, key names, and N-EDO microtonal accidentals
    into spoken English text for PyTTSx3.
    """

    @staticmethod
    def clean_scale_name(text: str) -> str:
        if not text:
            return ""
        # Remove "Mode X: " prefixes
        cleaned = re.sub(r'Mode\s+\d+:\s*', '', str(text))
        # Remove octave suffixes like "_4" in N-EDO pitch names
        cleaned = re.sub(r'_\d+', '', cleaned)
        return cleaned.strip()

    @classmethod
    def phoneticize(cls, text: str) -> str:
        if not text:
            return ""

        s = cls.clean_scale_name(text)

        # 1. EDO System pronunciation (e.g. 31-EDO -> 31 E D O)
        s = re.sub(r'(\d+)-EDO\b', r'\1 E D O', s, flags=re.IGNORECASE)

        # 2. Microtonal & Unicode accidental symbol translation
        s = s.replace('𝄳', ' quarter sharp ')
        s = s.replace('𝄲', ' quarter flat ')
        s = s.replace('♭', ' flat ')
        s = s.replace('♯', ' sharp ')

        # 3. N-EDO Step Offsets (e.g., C+1, D-2)
        s = re.sub(r'([A-G])\+(\d+)', r'\1 plus \2', s)
        s = re.sub(r'([A-G])\-(\d+)', r'\1 minus \2', s)

        # 4. Standard flat/sharp accidental symbols attached to root pitches
        s = re.sub(r'([A-G])b(?=[a-zA-Z0-9\(]|\b)', r'\1 flat ', s)
        s = re.sub(r'([A-G])#(?=[a-zA-Z0-9\(]|\b)', r'\1 sharp ', s)

        # 5. Separate glued root pitches (e.g., 'Am7b5' -> 'A m7b5', 'GMaj7' -> 'G Maj7')
        # Case-sensitive [A-G] prevents lowercase letters ('f', 'e', 'b') from matching as pitch roots
        s = re.sub(
            r'(\b[A-G](?:\s+(?:flat|sharp|quarter\s+flat|quarter\s+sharp|plus\s+\d+|minus\s+\d+))?)(?=[a-zA-Z0-9\(])',
            r'\1 ',
            s
        )

        # 6. Replace remaining standalone '#'
        s = s.replace('#', ' sharp ')

        # 7. Complex & Parenthetical Chord Qualities (Evaluated before generic Maj/m expansions)
        s = re.sub(r'\bm\s*\(\s*Maj(?:or)?\s*7\s*\)\s*b5\b', ' minor Major 7 flat 5', s, flags=re.IGNORECASE)
        s = re.sub(r'\bm\s*\(\s*Maj(?:or)?\s*7\s*\)', ' minor Major 7', s, flags=re.IGNORECASE)
        s = re.sub(r'\bm\s*\(\s*Maj(?:or)?\s*\)', ' minor Major', s, flags=re.IGNORECASE)

        # 8. Specific Compound Chord Qualities
        s = re.sub(r'\bm7b5\b', ' minor 7 flat 5', s)
        s = re.sub(r'\bMaj7#5\b', ' Major 7 sharp 5', s)
        s = re.sub(r'\bMaj7\s*sharp\s*5\b', ' Major 7 sharp 5', s, flags=re.IGNORECASE)
        s = re.sub(r'\bMaj7b5\b', ' Major 7 flat 5', s)
        s = re.sub(r'\bMaj7\s*flat\s*5\b', ' Major 7 flat 5', s, flags=re.IGNORECASE)
        s = re.sub(r'\b7#5\b', ' 7 sharp 5', s)
        s = re.sub(r'\b7b5\b', ' 7 flat 5', s)
        s = re.sub(r'\b7sus4\b', ' 7 suspended 4', s)
        s = re.sub(r'\b7sus2\b', ' 7 suspended 2', s)
        s = re.sub(r'\bsus4\b', ' suspended 4', s)
        s = re.sub(r'\bsus2\b', ' suspended 2', s)
        s = re.sub(r'\bdim7\b', ' diminished 7', s)
        s = re.sub(r'\bdim\b', ' diminished', s)

        # 9. Standard Quality Abbreviations
        s = re.sub(r'\bMaj7\b', ' Major 7', s)
        s = re.sub(r'\bMaj\b', ' Major', s)
        s = re.sub(r'\bmin7\b', ' minor 7', s)
        s = re.sub(r'\bmin\b', ' minor', s)
        s = re.sub(r'\bm7\b', ' minor 7', s)

        # 10. Standalone 'm' after root pitch (e.g., 'F m', 'Fm', 'D minus 1 m')
        s = re.sub(r'(\b[A-G](?:\s+(?:flat|sharp|plus\s+\d+|minus\s+\d+))?)\s*m(?=\s+|\d|\b)', r'\1 minor ', s)

        # 11. Interval alterations (e.g., b5, #5)
        s = re.sub(r'\bb(\d)\b', r' flat \1', s)
        s = re.sub(r'\b#(\d)\b', r' sharp \1', s)

        # Normalize whitespace
        return re.sub(r'\s+', ' ', s).strip()

# ==============================================================================
# BAND DIRECTOR NARRATOR ENGINE
# ==============================================================================
class BandDirectorNarrator:
    """Band Director Narrator calling polychords every minute and key transitions

    every 7 minutes on beat (120 BPM).
    """

    def __init__(self, ws_url: str = "ws://127.0.0.1:65432", bpm: int = 120):
        self.ws_url = ws_url
        self.bpm = bpm
        self.lock = threading.Lock()

        # Initialize pyttsx3 TTS Engine with Band Director voice profile
        self.tts_engine = pyttsx3.init()
        # 120 BPM cadence matching quarter notes / 8th note rhythm
        self.tts_engine.setProperty('rate', self.bpm)
        self._configure_band_director_voice()

        # WebSocket & State Tracking
        self.current_ws_state = None
        self.last_announced_chord_bucket = -1
        self.last_announced_key_bucket = -1

        self.previous_key = ""
        self.current_key = ""
        self.current_polychord = ""

        # Public App State for Web/API UI
        self.app_state = {
            "current_action": "Initializing Band Director...",
            "last_narration": "Awaiting clock sync...",
            "audio_file": None,
            "audio_id": 0,
            "polychord": "",
            "current_key": "",
            "previous_key": "",
            "edo_system": "31-EDO",
            "bpm": self.bpm
        }

    def _configure_band_director_voice(self):
        """Selects a distinct voice for the Band Director compared to other narrators."""
        try:
            voices = self.tts_engine.getProperty('voices')
            if not voices:
                return

            # Preference order: Male/Deep authoritative voices or secondary voice index
            preferred_keywords = ['male', 'david', 'george', 'alex', 'daniel', 'en-us']
            selected_voice = None

            for keyword in preferred_keywords:
                for v in voices:
                    if keyword in v.name.lower() or keyword in getattr(v, 'id', '').lower():
                        selected_voice = v.id
                        break
                if selected_voice:
                    break

            if not selected_voice and len(voices) > 1:
                selected_voice = voices[1].id
            elif not selected_voice:
                selected_voice = voices[0].id

            self.tts_engine.setProperty('voice', selected_voice)
        except Exception as e:
            print(f"[NARRATOR VOICE] Warning configuring voice: {e}")

    def _pad_wav_with_silence(self, filepath: str, silence_duration_sec: float = 0.25):
        """Appends trailing silence to prevent sound card truncation on beat."""
        try:
            sr, data = wavfile.read(filepath)
            silence_samples = int(sr * silence_duration_sec)

            if data.ndim == 1:
                silence = np.zeros(silence_samples, dtype=data.dtype)
            else:
                silence = np.zeros((silence_samples, data.shape[1]), dtype=data.dtype)

            padded_data = np.concatenate((data, silence))
            wavfile.write(filepath, sr, padded_data)
        except Exception as e:
            print(f"[AUDIO] Error padding audio: {e}")

    def generate_tts_wav(self, text: str, filename: str) -> str:
        """Generates a TTS WAV file from text in the cache directory."""
        filepath = os.path.join(CACHE_DIR, filename)
        self.tts_engine.save_to_file(text, filepath)
        self.tts_engine.runAndWait()
        self._pad_wav_with_silence(filepath, silence_duration_sec=0.25)
        return filename

    def get_wav_duration(self, filepath: str) -> float:
        try:
            with wave.open(filepath, 'r') as f:
                frames = f.getnframes()
                rate = f.getframerate()
                return frames / float(rate)
        except Exception:
            return 1.5

    def speak_phrase(self, text: str, filename_prefix: str):
        """Generates narration audio and exposes it to connected clients."""
        print(f"[BAND DIRECTOR] {text}")
        filename = f"{filename_prefix}_{int(time.time())}.wav"
        filepath = os.path.join(CACHE_DIR, filename)

        self.generate_tts_wav(text, filename)
        duration = self.get_wav_duration(filepath)

        with self.lock:
            self.app_state["current_action"] = "Calling out"
            self.app_state["last_narration"] = text
            self.app_state["audio_file"] = filename
            self.app_state["audio_id"] += 1

        time.sleep(duration)

        with self.lock:
            self.app_state["current_action"] = "Listening on beat"

    def format_polychord(self, state: dict) -> str:
        """Extracts polychord text handling both single and dual hand progressions."""
        lh_chord = state.get("left_hand", {}).get("chord_name", "Unknown Chord")
        rh_chord = state.get("right_hand", {}).get("chord_name", "")

        if rh_chord and rh_chord != lh_chord:
            return f"{lh_chord} over {rh_chord}"
        return lh_chord

    def format_polykey(self, state: dict) -> str:
        """Extracts polykey/key text handling parameterized EDO state layouts."""
        lh_key = state.get("left_hand", {}).get("key", "")
        if not lh_key:
            lh_key = state.get("left_hand", {}).get("meta", {}).get("key", "Unknown Key")

        rh_key = state.get("right_hand", {}).get("key", "")
        if not rh_key:
            rh_key = state.get("right_hand", {}).get("meta", {}).get("key", "")

        if rh_key and rh_key != lh_key:
            return f"{lh_key} against {rh_key}"
        return lh_key

    def start_ws_listener(self):
        """Listens to WebSocket updates from the chimes clock server."""
        async def listen():
            while True:
                try:
                    async with websockets.connect(self.ws_url) as ws:
                        print(f"[WS CLIENT] Connected to Chimes Clock Server at {self.ws_url}")
                        async for msg in ws:
                            data = json.loads(msg)
                            with self.lock:
                                self.current_ws_state = data
                except Exception as e:
                    print(f"[WS ERROR] Connection offline ({e}). Retrying in 2 seconds...")
                    await asyncio.sleep(2.0)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(listen())

    def start_narration_loop(self):
        """Monitors tick boundaries for minute chord changes and 7-minute key changes."""
        while True:
            with self.lock:
                state = self.current_ws_state

            if not state:
                time.sleep(0.1)
                continue

            current_tick = state.get("tick", int(time.time()))
            chord_bucket = current_tick // CHORD_INTERVAL_SEC
            key_bucket = current_tick // KEY_INTERVAL_SEC

            raw_polychord = self.format_polychord(state)
            raw_key = self.format_polykey(state)
            edo_sys = state.get("edo_system", "31-EDO")

            with self.lock:
                self.app_state["polychord"] = raw_polychord
                self.app_state["edo_system"] = edo_sys
                if not self.current_key:
                    self.current_key = raw_key
                self.app_state["current_key"] = self.current_key
                self.app_state["previous_key"] = self.previous_key

            # First initialization on clock sync
            if self.last_announced_chord_bucket == -1:
                self.last_announced_chord_bucket = chord_bucket
                self.last_announced_key_bucket = key_bucket
                self.current_key = raw_key
                self.current_polychord = raw_polychord
                time.sleep(0.2)
                continue

            # ------------------------------------------------------------------
            # 1. 7-MINUTE KEY CHANGE ANNOUNCEMENT
            #    "Tells us the key we just heard and the key we're now beginning"
            # ------------------------------------------------------------------
            if key_bucket > self.last_announced_key_bucket:
                self.previous_key = self.current_key
                self.current_key = raw_key

                spoken_prev_key = MicrotonalPhoneticTranslator.phoneticize(self.previous_key)
                spoken_new_key = MicrotonalPhoneticTranslator.phoneticize(self.current_key)

                key_script = (
                    f"Key completed: {spoken_prev_key}. "
                    f"Now beginning key: {spoken_new_key}."
                )

                self.speak_phrase(key_script, "key_change")
                self.last_announced_key_bucket = key_bucket

            # ------------------------------------------------------------------
            # 2. EVERY MINUTE CHORD CHANGE ANNOUNCEMENT
            #    "Tells us the new polychord"
            # ------------------------------------------------------------------
#            if chord_bucket > self.last_announced_chord_bucket:
#                self.current_polychord = raw_polychord
#                spoken_polychord = MicrotonalPhoneticTranslator.phoneticize(self.current_polychord)
#
#                chord_script = f"New polychord: {spoken_polychord}."
#
#                self.speak_phrase(chord_script, "chord_change")
#                self.last_announced_chord_bucket = chord_bucket
            # ------------------------------------------------------------------
            # 2. EVERY MINUTE CHORD CHANGE ANNOUNCEMENT
            #    Directly announces the chord
            # ------------------------------------------------------------------
            if chord_bucket > self.last_announced_chord_bucket:
                self.current_polychord = raw_polychord
                spoken_polychord = MicrotonalPhoneticTranslator.phoneticize(self.current_polychord)

                chord_script = f"{spoken_polychord}."

                self.speak_phrase(chord_script, "chord_change")
                self.last_announced_chord_bucket = chord_bucket

            time.sleep(0.1)
