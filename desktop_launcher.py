from __future__ import annotations

import argparse
import html
import json
import os
import re
import signal
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

APP_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(APP_DIR))

from fleet_core.app_paths import APP_NAME, ensure_user_dirs

URL_PATTERN = re.compile(r"Open Solar Expanse Fleet Manager at (http://\S+)")
CONFIG_FILE_NAME = "desktop_config.json"
WINDOW_WIDTH = 1420
WINDOW_HEIGHT = 920
WINDOW_MIN_SIZE = (980, 680)
DEFAULT_CONFIG = {
    "host": "127.0.0.1",
    "port": 8080,
    "port_scan_limit": 20,
    "strict_port": False,
}


@dataclass
class LaunchState:
    url: str | None = None
    last_line: str = ""
    error: str | None = None


class FleetManagerServer:
    def __init__(self, server_command: list[str] | None = None) -> None:
        self.app_data_dir = ensure_user_dirs()
        self.log_path = self.app_data_dir / "logs" / "desktop_launcher.log"
        self.config_path = self.app_data_dir / CONFIG_FILE_NAME
        self.state = LaunchState()
        self.process: subprocess.Popen[str] | None = None
        self._server_command = server_command
        self._output_thread: threading.Thread | None = None
        self._lock = threading.Lock()

    def is_running(self) -> bool:
        with self._lock:
            return self.process is not None and self.process.poll() is None

    def start(self) -> None:
        with self._lock:
            if self.process and self.process.poll() is None:
                return
            self.state = LaunchState()
            env = self._server_env()
            self.process = subprocess.Popen(
                self._server_command or _default_server_command(),
                cwd=str(APP_DIR),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                creationflags=_subprocess_creationflags(),
                start_new_session=(os.name != "nt"),
            )
            self._output_thread = threading.Thread(target=self._capture_output, daemon=True)
            self._output_thread.start()

    def stop(self) -> None:
        with self._lock:
            process = self.process
        if not process or process.poll() is not None:
            self.state = LaunchState(last_line="Fleet Manager server is stopped.")
            if process:
                _close_process_streams(process)
            with self._lock:
                self.process = None
            return
        _terminate_process_tree(process)
        _close_process_streams(process)
        self.state = LaunchState(last_line="Fleet Manager server is stopped.")
        with self._lock:
            self.process = None

    def restart(self) -> None:
        self.stop()
        self.start()

    def wait_for_url(self, timeout: float = 45.0) -> str:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.state.url and _url_is_ready(self.state.url):
                return self.state.url
            process = self.process
            if process is None:
                raise RuntimeError("Fleet Manager server is not running.")
            if process and process.poll() is not None:
                raise RuntimeError(self.state.error or self.state.last_line or "Fleet Manager server exited during startup.")
            time.sleep(0.2)
        raise RuntimeError(self.state.last_line or "Fleet Manager server did not become ready before the startup timeout.")

    def open_browser(self) -> None:
        if self.state.url:
            webbrowser.open(self.state.url)

    def open_when_ready(self) -> None:
        try:
            self.start()
            url = self.wait_for_url()
        except RuntimeError as exc:
            self.state.error = str(exc)
            return
        webbrowser.open(url)

    def copy_url(self) -> bool:
        if not self.state.url:
            return False
        return _copy_text_to_clipboard(self.state.url)

    def open_logs(self) -> None:
        _open_path(self.log_path)

    def open_config(self) -> None:
        self.ensure_config()
        _open_path(self.config_path)

    def ensure_config(self) -> dict[str, object]:
        if not self.config_path.exists():
            self.config_path.write_text(json.dumps(DEFAULT_CONFIG, indent=2) + "\n", encoding="utf-8")
            return dict(DEFAULT_CONFIG)
        try:
            loaded = json.loads(self.config_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            backup = self.config_path.with_suffix(".invalid.json")
            try:
                self.config_path.replace(backup)
            except OSError:
                pass
            self.config_path.write_text(json.dumps(DEFAULT_CONFIG, indent=2) + "\n", encoding="utf-8")
            self.state.error = f"Invalid desktop config was reset. Previous file: {backup}"
            return dict(DEFAULT_CONFIG)
        if not isinstance(loaded, dict):
            loaded = {}
        config = dict(DEFAULT_CONFIG)
        config.update({key: value for key, value in loaded.items() if key in DEFAULT_CONFIG})
        return config

    def _server_env(self) -> dict[str, str]:
        env = os.environ.copy()
        config = self.ensure_config()
        self._apply_config_to_env(env, config)
        env.setdefault("PYTHONUNBUFFERED", "1")
        return env

    def _apply_config_to_env(self, env: dict[str, str], config: dict[str, object]) -> None:
        env.setdefault("FLEET_MANAGER_HOST", str(config.get("host") or DEFAULT_CONFIG["host"]))
        env.setdefault("FLEET_MANAGER_PORT", str(config.get("port") or DEFAULT_CONFIG["port"]))
        env.setdefault(
            "FLEET_MANAGER_PORT_SCAN_LIMIT",
            str(config.get("port_scan_limit") or DEFAULT_CONFIG["port_scan_limit"]),
        )
        if bool(config.get("strict_port")):
            env.setdefault("FLEET_MANAGER_STRICT_PORT", "1")

    def _capture_output(self) -> None:
        process = self.process
        if process is None or process.stdout is None:
            return
        with self.log_path.open("a", encoding="utf-8") as log:
            log.write(f"\n--- Fleet Manager desktop launcher {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n")
            for line in process.stdout:
                clean = line.rstrip()
                self.state.last_line = clean
                if "could not start" in clean.lower():
                    self.state.error = clean
                match = URL_PATTERN.search(clean)
                if match:
                    self.state.url = match.group(1)
                log.write(line)
                log.flush()


def _subprocess_creationflags() -> int:
    if os.name != "nt":
        return 0
    return getattr(subprocess, "CREATE_NO_WINDOW", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)


def _default_server_command() -> list[str]:
    if getattr(sys, "frozen", False):
        return [sys.executable, "--server"]
    return [sys.executable, str(Path(__file__).resolve()), "--server"]


def _terminate_process_tree(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    if os.name == "nt":
        try:
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
        except OSError:
            process.terminate()
    else:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            return
        except OSError:
            process.terminate()
    try:
        process.wait(timeout=8)
    except subprocess.TimeoutExpired:
        if os.name == "nt":
            process.kill()
        else:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            except OSError:
                process.kill()
        process.wait(timeout=5)


def _close_process_streams(process: subprocess.Popen[str]) -> None:
    for stream in (process.stdout, process.stderr, process.stdin):
        if stream:
            try:
                stream.close()
            except OSError:
                pass


def _url_is_ready(url: str) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=1.0) as response:
            return response.status < 500
    except (OSError, urllib.error.URLError):
        return False


def _copy_text_to_clipboard(text: str) -> bool:
    if os.name == "nt":
        try:
            subprocess.run("clip", input=text, text=True, check=True, shell=True)
            return True
        except (OSError, subprocess.CalledProcessError):
            return False
    for command in (("xclip", "-selection", "clipboard"), ("xsel", "--clipboard", "--input")):
        try:
            subprocess.run(command, input=text, text=True, check=True)
            return True
        except (OSError, subprocess.CalledProcessError):
            continue
    return False


def _open_path(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.touch()
    if os.name == "nt":
        os.startfile(path)  # type: ignore[attr-defined]
        return
    webbrowser.open(path.resolve().as_uri())


def _run_server_mode() -> None:
    from app import run_server

    run_server()


def _open_webview(url: str) -> bool:
    try:
        import webview
    except ImportError:
        return False

    try:
        webview.create_window(APP_NAME, url, width=WINDOW_WIDTH, height=WINDOW_HEIGHT, min_size=WINDOW_MIN_SIZE)
        webview.start()
    except Exception as exc:
        print(f"Could not open embedded Fleet Manager window: {exc}", file=sys.stderr, flush=True)
        return False
    return True


def _open_recovery_window(message: str, server: FleetManagerServer) -> bool:
    try:
        import webview
    except ImportError:
        return False

    body = _recovery_html(message, server)
    try:
        webview.create_window(
            f"{APP_NAME} - Recovery",
            html=body,
            width=760,
            height=560,
            min_size=(620, 440),
        )
        webview.start()
    except Exception as exc:
        print(f"Could not open Fleet Manager recovery window: {exc}", file=sys.stderr, flush=True)
        return False
    return True


def _recovery_html(message: str, server: FleetManagerServer) -> str:
    escaped_message = html.escape(message)
    config_path = html.escape(str(server.config_path))
    log_path = html.escape(str(server.log_path))
    last_line = html.escape(server.state.last_line or "No server output was captured.")
    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>{html.escape(APP_NAME)} Recovery</title>
  <style>
    :root {{
      color-scheme: dark;
      font-family: "Segoe UI", Arial, sans-serif;
      background: #020910;
      color: #e8f7ff;
    }}
    body {{
      margin: 0;
      min-height: 100vh;
      background:
        linear-gradient(120deg, rgba(53, 216, 255, 0.08), transparent 42%),
        #020910;
    }}
    main {{ padding: 32px; }}
    h1 {{ margin: 0 0 10px; font-size: 26px; }}
    p {{ color: #a8bfca; line-height: 1.45; }}
    code, pre {{
      color: #e8f7ff;
      background: rgba(8, 30, 42, 0.85);
      border: 1px solid rgba(86, 179, 214, 0.38);
      border-radius: 4px;
    }}
    code {{ padding: 2px 5px; }}
    pre {{ padding: 12px; white-space: pre-wrap; }}
    .panel {{
      margin-top: 18px;
      padding: 18px;
      border: 1px solid rgba(86, 179, 214, 0.42);
      background: rgba(6, 22, 32, 0.88);
    }}
    .accent {{ color: #35d8ff; font-weight: 700; }}
  </style>
</head>
<body>
  <main>
    <h1>Fleet Manager could not start</h1>
    <p class="accent">{escaped_message}</p>
    <div class="panel">
      <p>Use the tray menu to restart the server after changing configuration, or open these files directly:</p>
      <p>Config: <code>{config_path}</code></p>
      <p>Logs: <code>{log_path}</code></p>
    </div>
    <div class="panel">
      <p>Last server output:</p>
      <pre>{last_line}</pre>
    </div>
  </main>
</body>
</html>"""


def _run_tray(server: FleetManagerServer) -> bool:
    try:
        import pystray
        from PIL import Image, ImageDraw
    except ImportError:
        return False

    def icon_image() -> Image.Image:
        image = Image.new("RGBA", (64, 64), (2, 9, 16, 255))
        draw = ImageDraw.Draw(image)
        draw.ellipse((18, 18, 46, 46), fill=(53, 216, 255, 255))
        draw.ellipse((26, 26, 38, 38), fill=(180, 247, 255, 255))
        return image

    def run_background(action: Callable[[], None]) -> None:
        threading.Thread(target=action, daemon=True).start()

    def status_text(_: object = None) -> str:
        if server.state.url:
            return f"URL: {server.state.url}"
        if server.state.error:
            return "Status: startup needs attention"
        return "Status: starting or stopped"

    def open_app(_: object = None) -> None:
        run_background(server.open_when_ready)

    def open_browser(_: object = None) -> None:
        run_background(server.open_when_ready)

    def copy_url(_: object = None) -> None:
        server.copy_url()

    def restart(_: object = None) -> None:
        def action() -> None:
            server.restart()
            try:
                server.wait_for_url()
            except RuntimeError as exc:
                server.state.error = str(exc)

        run_background(action)

    def stop(_: object = None) -> None:
        run_background(server.stop)

    def open_logs(_: object = None) -> None:
        server.open_logs()

    def open_config(_: object = None) -> None:
        server.open_config()

    def quit_app(icon: pystray.Icon, _: object = None) -> None:
        icon.stop()
        server.stop()

    menu = pystray.Menu(
        pystray.MenuItem(status_text, None, enabled=False),
        pystray.MenuItem("Open Fleet Manager", open_app, default=True),
        pystray.MenuItem("Open in Browser", open_browser),
        pystray.MenuItem("Copy URL", copy_url),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Restart Server", restart),
        pystray.MenuItem("Stop Server", stop),
        pystray.MenuItem("Change Port / Configure Port", open_config),
        pystray.MenuItem("Open Logs", open_logs),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Quit", quit_app),
    )
    icon = pystray.Icon("SolarExpanseFleetManager", icon_image(), APP_NAME, menu)
    threading.Thread(target=icon.run, daemon=True).start()
    return True


def run_browser_mode() -> int:
    server = FleetManagerServer()
    server.start()
    _run_tray(server)
    try:
        url = server.wait_for_url()
    except RuntimeError as exc:
        message = _clean_startup_error(str(exc))
        print(f"{APP_NAME} could not start: {message}", file=sys.stderr, flush=True)
        print(f"Open {server.config_path} to change port settings, then restart Fleet Manager.", file=sys.stderr)
        print(f"Open {server.log_path} for server logs.", file=sys.stderr)
        server.stop()
        return 2
    print(f"Opening {url} in your browser.", flush=True)
    webbrowser.open(url)
    try:
        while server.process and server.process.poll() is None:
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        server.stop()
    return 0


def _clean_startup_error(message: str) -> str:
    prefix = f"{APP_NAME} could not start: "
    if message.startswith(prefix):
        return message[len(prefix) :]
    return message


def run_desktop(open_browser_fallback: bool = True) -> int:
    server = FleetManagerServer()
    server.start()
    _run_tray(server)
    try:
        url = server.wait_for_url()
    except RuntimeError as exc:
        message = _clean_startup_error(str(exc))
        print(f"{APP_NAME} could not start: {message}", file=sys.stderr, flush=True)
        if not _open_recovery_window(message, server):
            print(f"Open {server.config_path} to change port settings, then restart Fleet Manager.", file=sys.stderr)
            print(f"Open {server.log_path} for server logs.", file=sys.stderr)
        server.stop()
        return 2

    opened_window = _open_webview(url)
    if not opened_window:
        print(f"pywebview is not installed; opening {url} in your browser.", flush=True)
        if open_browser_fallback:
            webbrowser.open(url)
        try:
            while server.process and server.process.poll() is None:
                time.sleep(0.5)
        except KeyboardInterrupt:
            pass
        finally:
            server.stop()
    else:
        server.stop()
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Solar Expanse Fleet Manager desktop launcher")
    parser.add_argument("--server", action="store_true", help="internal mode: run the NiceGUI server")
    parser.add_argument("--browser", action="store_true", help="run the server and open the browser instead of pywebview")
    parser.add_argument("--config", action="store_true", help="open the desktop launcher port config file")
    parser.add_argument("--logs", action="store_true", help="open the desktop launcher log file")
    parser.add_argument("--no-browser-fallback", action="store_true", help="do not open a browser if pywebview is unavailable")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(list(argv or sys.argv[1:]))
    if args.server:
        _run_server_mode()
        return 0
    if args.config:
        FleetManagerServer().open_config()
        return 0
    if args.logs:
        FleetManagerServer().open_logs()
        return 0
    if args.browser:
        return run_browser_mode()
    return run_desktop(open_browser_fallback=not args.no_browser_fallback)


if __name__ in {"__main__", "__mp_main__"}:
    raise SystemExit(main())
