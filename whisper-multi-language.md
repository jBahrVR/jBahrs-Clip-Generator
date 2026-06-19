# Local Whisper Multi-Language Support

## Goal
Provide full local Whisper multi-language support by defining configuration defaults, ensuring backward-compatible migrations, fixing OS-specific test issues on Windows, and adding comprehensive unit testing.

## Tasks
- [x] Task 1: Add `"whisper_language": "Auto-Detect"` to `get_default_config()` in [config_manager.py](file:///D:/Dev%20Projects/Clipgen/jBahrs-Clip-Generator/config_manager.py) → Verify: Assert new key in `test_config_manager.py` checks.
- [x] Task 2: Fix POSIX-specific file permission assertion in `test_config_manager.py` by skipping owner permission checks on Windows (where permissions are mapped to 0o666) → Verify: Run `python test_config_manager.py` and see it pass.
- [x] Task 3: Implement migration default for `whisper_language` in `load_config()` of [config_manager.py](file:///D:/Dev%20Projects/Clipgen/jBahrs-Clip-Generator/config_manager.py) → Verify: Add test assertions for migration defaulting to `Auto-Detect`.
- [x] Task 4: Add new unit tests in [test_editor.py](file:///D:/Dev%20Projects/Clipgen/jBahrs-Clip-Generator/test_editor.py) to verify that `_transcribe_audio_to_segments` correctly passes the specified `language` argument to Whisper's `model.transcribe()` → Verify: Run `python -m unittest test_editor.py`.

## Done When
- [x] All configuration unit tests pass successfully on Windows.
- [x] Editor unit tests verify that the `language` argument is correctly resolved and passed to Whisper's `transcribe` function.
