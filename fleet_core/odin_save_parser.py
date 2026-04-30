from __future__ import annotations

import gzip
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class SaveParseError(ValueError):
    """Raised when a save payload cannot be parsed."""


@dataclass(frozen=True)
class FStringRef:
    value: str


@dataclass(frozen=True)
class IRef:
    value: int


class OdinLikeParser:
    """Small parser for Solar Expanse's Odin JSON-ish save format.

    The format is mostly JSON, but it also contains tokens such as
    `$fstrref:"ResourceDefinition/id_resource_fuel"` and typed objects with
    anonymous scalar values. Anonymous object values are stored under
    `"$values"`.
    """

    def __init__(self, text: str) -> None:
        self.text = text
        self.i = 0
        self.n = len(text)

    def parse(self) -> Any:
        value = self._parse_value()
        self._skip_ws()
        if self.i != self.n:
            raise SaveParseError(f"Unexpected trailing data at byte {self.i}")
        return value

    def _skip_ws(self) -> None:
        while self.i < self.n and self.text[self.i] in " \t\r\n":
            self.i += 1

    def _peek(self) -> str:
        self._skip_ws()
        return self.text[self.i] if self.i < self.n else ""

    def _consume(self, expected: str) -> None:
        self._skip_ws()
        if self.i >= self.n or self.text[self.i] != expected:
            got = self.text[self.i : self.i + 20]
            raise SaveParseError(f"Expected {expected!r} at byte {self.i}, got {got!r}")
        self.i += 1

    def _parse_value(self) -> Any:
        self._skip_ws()
        if self.i >= self.n:
            raise SaveParseError("Unexpected end of input")
        ch = self.text[self.i]
        if ch == "{":
            return self._parse_object()
        if ch == "[":
            return self._parse_array()
        if ch == '"':
            return self._parse_string()
        if ch == "$":
            return self._parse_dollar_token()
        if ch == "-" or ch.isdigit():
            return self._parse_number()
        if self.text.startswith("true", self.i):
            self.i += 4
            return True
        if self.text.startswith("false", self.i):
            self.i += 5
            return False
        if self.text.startswith("null", self.i):
            self.i += 4
            return None
        if self.text.startswith("Infinity", self.i):
            self.i += len("Infinity")
            return float("inf")
        if self.text.startswith("-Infinity", self.i):
            self.i += len("-Infinity")
            return float("-inf")
        if self.text.startswith("NaN", self.i):
            self.i += len("NaN")
            return float("nan")
        got = self.text[self.i : self.i + 40]
        raise SaveParseError(f"Unexpected token at byte {self.i}: {got!r}")

    def _parse_object(self) -> dict[str, Any]:
        self._consume("{")
        result: dict[str, Any] = {}
        values: list[Any] = []
        first = True
        while True:
            self._skip_ws()
            if self._peek() == "}":
                self.i += 1
                if values:
                    result["$values"] = values
                return result
            if not first:
                self._consume(",")
                self._skip_ws()
                if self._peek() == "}":
                    self.i += 1
                    if values:
                        result["$values"] = values
                    return result
            first = False

            if self._peek() == '"':
                saved = self.i
                key = self._parse_string()
                self._skip_ws()
                if self.i < self.n and self.text[self.i] == ":":
                    self.i += 1
                    result[key] = self._parse_value()
                else:
                    self.i = saved
                    values.append(self._parse_value())
            else:
                values.append(self._parse_value())

    def _parse_array(self) -> list[Any]:
        self._consume("[")
        result: list[Any] = []
        first = True
        while True:
            self._skip_ws()
            if self._peek() == "]":
                self.i += 1
                return result
            if not first:
                self._consume(",")
            first = False
            result.append(self._parse_value())

    def _parse_string(self) -> str:
        self._consume('"')
        out: list[str] = []
        while self.i < self.n:
            ch = self.text[self.i]
            self.i += 1
            if ch == '"':
                return "".join(out)
            if ch != "\\":
                out.append(ch)
                continue
            if self.i >= self.n:
                raise SaveParseError("Unterminated escape sequence")
            esc = self.text[self.i]
            self.i += 1
            if esc == '"':
                out.append('"')
            elif esc == "\\":
                out.append("\\")
            elif esc == "/":
                out.append("/")
            elif esc == "b":
                out.append("\b")
            elif esc == "f":
                out.append("\f")
            elif esc == "n":
                out.append("\n")
            elif esc == "r":
                out.append("\r")
            elif esc == "t":
                out.append("\t")
            elif esc == "u":
                hex_value = self.text[self.i : self.i + 4]
                if len(hex_value) != 4:
                    raise SaveParseError("Short unicode escape")
                out.append(chr(int(hex_value, 16)))
                self.i += 4
            else:
                out.append(esc)
        raise SaveParseError("Unterminated string")

    def _parse_number(self) -> int | float:
        start = self.i
        if self.text[self.i] == "-":
            self.i += 1
        while self.i < self.n and self.text[self.i].isdigit():
            self.i += 1
        if self.i < self.n and self.text[self.i] == ".":
            self.i += 1
            while self.i < self.n and self.text[self.i].isdigit():
                self.i += 1
        if self.i < self.n and self.text[self.i] in "eE":
            self.i += 1
            if self.i < self.n and self.text[self.i] in "+-":
                self.i += 1
            while self.i < self.n and self.text[self.i].isdigit():
                self.i += 1
        raw = self.text[start : self.i]
        return float(raw) if any(c in raw for c in ".eE") else int(raw)

    def _parse_dollar_token(self) -> Any:
        self.i += 1
        start = self.i
        while self.i < self.n and (self.text[self.i].isalnum() or self.text[self.i] == "_"):
            self.i += 1
        name = self.text[start : self.i]
        self._skip_ws()
        if name == "fstrref" and self.i < self.n and self.text[self.i] == ":":
            self.i += 1
            return FStringRef(self._parse_value())
        if name == "iref" and self.i < self.n and self.text[self.i] == ":":
            self.i += 1
            value = self._parse_value()
            return IRef(int(value)) if isinstance(value, int) else IRef(-1)
        return f"${name}"


def parse_save_file(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    text = gzip.decompress(path.read_bytes()).decode("utf-8", "replace")
    parsed = OdinLikeParser(text).parse()
    if not isinstance(parsed, dict):
        raise SaveParseError(f"Expected save root object in {path}")
    return parsed
