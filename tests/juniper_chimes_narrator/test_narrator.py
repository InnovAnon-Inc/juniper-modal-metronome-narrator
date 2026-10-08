import os
import pytest
from unittest.mock import MagicMock, patch
from juniper_chimes_narrator.narrator import (
    MicrotonalPhoneticTranslator,
    BandDirectorNarrator,
)


# ==============================================================================
# 1. TESTS FOR MicrotonalPhoneticTranslator
# ==============================================================================

class TestMicrotonalPhoneticTranslator:

    @pytest.mark.parametrize(
        "input_text, expected",
        [
            ("Mode 1: Locrian", "Locrian"),
            ("Mode 12: C_4", "C"),
            ("A_3", "A"),
            ("", ""),
            (None, ""),
        ],
    )
    def test_clean_scale_name(self, input_text, expected):
        assert MicrotonalPhoneticTranslator.clean_scale_name(input_text) == expected

    @pytest.mark.parametrize(
        "input_text, expected",
        [
            # Microtonal Accidentals
            ("C𝄳", "C quarter sharp"),
            ("D𝄲", "D quarter flat"),
            ("E♭", "E flat"),
            ("F♯", "F sharp"),
            # Pitch offsets (N-EDO)
            ("C+1", "C plus 1"),
            ("D-2", "D minus 2"),
            # Standard Sharps/Flats
            ("Db", "D flat"),
            ("C#", "C sharp"),
            # EDO System Pronunciation
            ("31-EDO", "31 E D O"),
            ("24-edo", "24 E D O"),
            # Complex & Parenthetical Qualities (No prefix leakage or 'm' fragmentation)
            ("F m(Maj7)", "F minor Major 7"),
            ("F m( Major 7)", "F minor Major 7"),
            ("D-1 7 over F m(Maj7)", "D minus 1 7 over F minor Major 7"),
            ("C m(Maj7)b5", "C minor Major 7 flat 5"),
            # Compound & Standard Qualities
            ("Am7b5", "A minor 7 flat 5"),
            ("GMaj7#5", "G Major 7 sharp 5"),
            ("C7sus4", "C 7 suspended 4"),
            ("Bdim7", "B diminished 7"),
            ("Edim", "E diminished"),
            ("Fm", "F minor"),
            ("F m", "F minor"),
        ],
    )
    def test_phoneticize(self, input_text, expected):
        translated = MicrotonalPhoneticTranslator.phoneticize(input_text)
        assert translated == expected


# ==============================================================================
# 2. TESTS FOR BandDirectorNarrator
# ==============================================================================

@pytest.fixture
def mock_narrator():
    """Fixture providing a BandDirectorNarrator with mocked TTS engine."""
    with patch("pyttsx3.init") as mock_init:
        mock_engine = MagicMock()
        mock_init.return_value = mock_engine
        
        narrator = BandDirectorNarrator(ws_url="ws://127.0.0.1:65432", bpm=120)
        yield narrator, mock_engine


class TestBandDirectorNarrator:

    def test_initialization(self, mock_narrator):
        narrator, mock_engine = mock_narrator
        assert narrator.bpm == 120
        assert narrator.last_announced_chord_bucket == -1
        assert narrator.last_announced_key_bucket == -1
        assert narrator.app_state["bpm"] == 120

    def test_format_polychord_single_hand(self, mock_narrator):
        narrator, _ = mock_narrator
        state = {
            "left_hand": {"chord_name": "C Major"},
            "right_hand": {"chord_name": "C Major"},
        }
        assert narrator.format_polychord(state) == "C Major"

    def test_format_polychord_dual_hand(self, mock_narrator):
        narrator, _ = mock_narrator
        state = {
            "left_hand": {"chord_name": "C Major"},
            "right_hand": {"chord_name": "G7"},
        }
        assert narrator.format_polychord(state) == "C Major over G7"

    def test_format_polykey_single_and_dual(self, mock_narrator):
        narrator, _ = mock_narrator
        single_state = {
            "left_hand": {"key": "C Major"},
            "right_hand": {"key": "C Major"},
        }
        assert narrator.format_polykey(single_state) == "C Major"

        dual_state = {
            "left_hand": {"key": "C Major"},
            "right_hand": {"key": "G Major"},
        }
        assert narrator.format_polykey(dual_state) == "C Major against G Major"

    @patch("juniper_chimes_narrator.narrator.wavfile.write")
    @patch("juniper_chimes_narrator.narrator.wavfile.read")
    @patch("wave.open")
    def test_speak_phrase(self, mock_wave_open, mock_wav_read, mock_wav_write, mock_narrator):
        narrator, mock_engine = mock_narrator

        # Mock WAV duration calculation
        mock_wave_file = MagicMock()
        mock_wave_file.getnframes.return_value = 44100
        mock_wave_file.getframerate.return_value = 44100
        mock_wave_open.return_value.__enter__.return_value = mock_wave_file

        # Mock numpy array reading for padding
        import numpy as np
        mock_wav_read.return_value = (44100, np.zeros(44100, dtype=np.int16))

        with patch("time.sleep"):  # Skip real sleeping during tests
            narrator.speak_phrase("D minus 1 7 over F minor Major 7.", "chord_change")

        assert narrator.app_state["last_narration"] == "D minus 1 7 over F minor Major 7."
        assert narrator.app_state["audio_id"] == 1
        assert "chord_change" in narrator.app_state["audio_file"]
        mock_engine.save_to_file.assert_called_once()
