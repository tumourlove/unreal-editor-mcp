"""Tests for UE log line parsing."""

from unreal_editor_mcp.logs.parser import parse_log_line, LogEntry, SEVERITIES


class TestParseLogLine:
    def test_full_format_with_severity(self):
        line = "[2024.03.01-12.34.56:789][  0]LogTemp: Warning: Something happened"
        entry = parse_log_line(line)
        assert entry is not None
        assert entry.timestamp == "2024.03.01-12.34.56:789"
        assert entry.frame == 0
        assert entry.category == "LogTemp"
        assert entry.severity == "Warning"
        assert entry.message == "Something happened"

    def test_full_format_display_severity(self):
        line = "[2024.03.01-12.34.56:789][ 42]LogInit: Display: Engine initialized"
        entry = parse_log_line(line)
        assert entry is not None
        assert entry.category == "LogInit"
        assert entry.severity == "Display"
        assert entry.message == "Engine initialized"

    def test_format_without_explicit_severity(self):
        line = "[2024.03.01-12.34.56:789][  0]LogInit: Build version string"
        entry = parse_log_line(line)
        assert entry is not None
        assert entry.category == "LogInit"
        assert entry.severity == "Log"
        assert entry.message == "Build version string"

    def test_error_severity(self):
        line = "[2024.03.01-12.34.56:789][  0]LogTemp: Error: Null pointer access"
        entry = parse_log_line(line)
        assert entry is not None
        assert entry.severity == "Error"
        assert entry.message == "Null pointer access"

    def test_fatal_severity(self):
        line = "[2024.03.01-12.34.56:789][  0]LogCore: Fatal: Assertion failed"
        entry = parse_log_line(line)
        assert entry is not None
        assert entry.severity == "Fatal"

    def test_continuation_line(self):
        line = "    at SomeFunction (SomeFile.cpp:42)"
        entry = parse_log_line(line)
        assert entry is None

    def test_empty_line(self):
        entry = parse_log_line("")
        assert entry is None

    def test_large_frame_number(self):
        line = "[2024.03.01-12.34.56:789][999]LogNet: Warning: Connection timeout"
        entry = parse_log_line(line)
        assert entry is not None
        assert entry.frame == 999

    def test_message_with_colons(self):
        line = "[2024.03.01-12.34.56:789][  0]LogTemp: Warning: File: C:/path/to/file.cpp Line: 42"
        entry = parse_log_line(line)
        assert entry is not None
        assert entry.message == "File: C:/path/to/file.cpp Line: 42"

    def test_severities_constant(self):
        assert "Fatal" in SEVERITIES
        assert "Error" in SEVERITIES
        assert "Warning" in SEVERITIES
        assert "Display" in SEVERITIES
        assert "Log" in SEVERITIES
        assert "Verbose" in SEVERITIES
        assert "VeryVerbose" in SEVERITIES


class TestLogEntryRaw:
    def test_raw_preserves_original(self):
        line = "[2024.03.01-12.34.56:789][  0]LogTemp: Warning: test"
        entry = parse_log_line(line)
        assert entry is not None
        assert entry.raw == line
