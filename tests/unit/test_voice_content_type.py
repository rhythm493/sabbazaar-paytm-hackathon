"""Offline tests for the Sarvam audio content-type normalization helper."""

from sabbazaar_agents.voice import normalize_audio_content_type


def test_strips_codec_parameters():
    assert normalize_audio_content_type("audio/webm;codecs=opus", "cmd.webm") == "audio/webm"
    assert normalize_audio_content_type("audio/ogg;codecs=opus", "cmd.ogg") == "audio/ogg"


def test_remaps_x_aliases():
    assert normalize_audio_content_type("audio/x-webm", "cmd.webm") == "audio/webm"
    assert normalize_audio_content_type("audio/x-ogg", "cmd.ogg") == "audio/ogg"
    assert normalize_audio_content_type("Audio/Wave", "cmd.wav") == "audio/wav"


def test_passthrough_accepted_types():
    assert normalize_audio_content_type("audio/wav", "cmd.wav") == "audio/wav"
    assert normalize_audio_content_type("audio/mpeg", "cmd.mp3") == "audio/mpeg"


def test_falls_back_to_extension():
    assert normalize_audio_content_type(None, "clip.webm") == "audio/webm"
    assert normalize_audio_content_type("application/octet-stream", "clip.OGG") == "audio/ogg"
    assert normalize_audio_content_type("", "odd.wav") == "audio/wav"


def test_unknown_is_octet_stream():
    assert normalize_audio_content_type(None, "audio.bin") == "application/octet-stream"
    assert normalize_audio_content_type("application/octet-stream", "") == "application/octet-stream"
