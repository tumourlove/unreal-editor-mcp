"""Tests for UBT/MSVC build error parsing."""

from unreal_editor_mcp.build.parser import parse_build_error, BuildError


class TestParseBuildError:
    def test_msvc_error(self):
        line = r"D:\Projects\Source\MyFile.cpp(42): error C2065: 'foo': undeclared identifier"
        err = parse_build_error(line)
        assert err is not None
        assert err.file == r"D:\Projects\Source\MyFile.cpp"
        assert err.line == 42
        assert err.severity == "error"
        assert err.code == "C2065"
        assert err.message == "'foo': undeclared identifier"

    def test_msvc_warning(self):
        line = r"D:\Projects\Source\MyFile.cpp(10): warning C4267: conversion from 'size_t' to 'int'"
        err = parse_build_error(line)
        assert err is not None
        assert err.severity == "warning"
        assert err.code == "C4267"

    def test_msvc_note(self):
        line = r"D:\Projects\Source\MyFile.cpp(10): note: see declaration of 'FVector'"
        err = parse_build_error(line)
        assert err is not None
        assert err.severity == "note"
        assert err.code == ""

    def test_msvc_error_with_column(self):
        line = r"D:\Projects\Source\MyFile.cpp(42,5): error C2065: 'foo': undeclared identifier"
        err = parse_build_error(line)
        assert err is not None
        assert err.line == 42
        assert err.column == 5

    def test_linker_error(self):
        line = r"MyFile.cpp.obj : error LNK2019: unresolved external symbol"
        err = parse_build_error(line)
        assert err is not None
        assert err.severity == "error"
        assert err.code == "LNK2019"

    def test_non_error_line(self):
        line = "Compiling MyFile.cpp..."
        err = parse_build_error(line)
        assert err is None

    def test_ue_header_error(self):
        line = "C:/Projects/Source/MyFile.h(100): error C2039: 'Foo': is not a member of 'UObject'"
        err = parse_build_error(line)
        assert err is not None
        assert err.file == "C:/Projects/Source/MyFile.h"
        assert err.line == 100


class TestBuildErrorFormatting:
    def test_to_dict(self):
        line = r"D:\Projects\Source\MyFile.cpp(42): error C2065: 'foo': undeclared"
        err = parse_build_error(line)
        assert err is not None
        d = err.to_dict()
        assert d["file"] == r"D:\Projects\Source\MyFile.cpp"
        assert d["line"] == 42
        assert d["severity"] == "error"
        assert d["code"] == "C2065"
        assert d["message"] == "'foo': undeclared"
