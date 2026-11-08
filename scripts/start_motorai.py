"""Start the existing local application; no installation, migrations or configuration edits."""

import argparse
import json
import os
import queue
import shutil
import socket
import subprocess
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from contextlib import contextmanager
from datetime import UTC
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND_URL = "http://127.0.0.1:8002"
FRONTEND_URL = "http://127.0.0.1:5174"
APPLICATION_TITLE = "AI Car Diagnostic Assistant"


class StartupError(Exception):
    """A sanitized message that can be shown without exposing environment values."""


def listening(port):
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.5):
            return True
    except OSError:
        return False


def get(url, *, timeout=5):
    # Local checks must not use corporate HTTP proxies or follow redirects.
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, request, response, code, message, headers, newurl):
            return None

    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    try:
        with opener.open(url, timeout=timeout) as response:
            body = response.read(2 * 1024 * 1024 + 1)
            if len(body) > 2 * 1024 * 1024:
                return None
            return body.decode("utf-8")
    except (OSError, urllib.error.URLError, UnicodeError):
        return None


def api_identity(base_url):
    body = get(base_url + "/openapi.json")
    try:
        schema = json.loads(body) if body else {}
        return schema.get("info", {}).get("title") == APPLICATION_TITLE and all(
            path in schema.get("paths", {})
            for path in ("/api/v1/health", "/api/v1/vehicles", "/api/v1/parts/search")
        )
    except (ValueError, AttributeError, TypeError):
        return False


class Launcher:
    def __init__(self, root=ROOT, notify=lambda message: None):
        self.root = Path(root)
        self.notify = notify
        self.logs = self.root / ".local-tools" / "logs"

    def start_process(self, command, directory, name, env=None):
        self.logs.mkdir(parents=True, exist_ok=True)
        try:
            with (self.logs / f"launcher-{name}.log").open("ab") as log:
                return subprocess.Popen(
                    [str(item) for item in command],
                    cwd=directory,
                    env=env,
                    stdin=subprocess.DEVNULL,
                    stdout=log,
                    stderr=log,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
        except OSError:
            raise StartupError(
                f"Could not start {name}. Check the local application environment."
            ) from None

    def wait_until(self, check, process, name, timeout=90):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if check():
                return
            if process is not None and process.poll() is not None:
                raise StartupError(
                    f"The {name} stopped during startup. Details are in .local-tools/logs/launcher-{name}.log."
                )
            time.sleep(0.5)
        raise StartupError(
            f"The {name} did not become ready. Check .local-tools/logs and try again."
        )

    def node(self):
        executable = shutil.which("node")
        if not executable:
            executable = next(
                (
                    p
                    for p in (self.root / ".local-tools").glob("node-*/node.exe")
                    if p.is_file()
                ),
                None,
            )
        if not executable:
            raise StartupError(
                "Node.js is missing. Restore the project's portable Node environment."
            )
        return executable

    def frontend_identity(self):
        html = get(FRONTEND_URL + "/")
        return bool(html and "Motor" in html and "Diagnostic Assistant</title>" in html)

    def run(self, *, open_browser=True):
        self.notify("Checking the backend...")
        if listening(8002):
            if not api_identity(BACKEND_URL):
                raise StartupError(
                    "Port 8002 is occupied by another or unresponsive application. Nothing was stopped."
                )
        else:
            interpreter = Path(
                "Scripts/python.exe" if os.name == "nt" else "bin/python"
            )
            python = next(
                (
                    base / interpreter
                    for base in (self.root / "backend/.venv", self.root / ".venv")
                    if (base / interpreter).is_file()
                ),
                self.root / "backend/.venv" / interpreter,
            )
            if not python.is_file() or not (self.root / "backend" / ".env").is_file():
                raise StartupError(
                    "The backend environment or backend/.env is missing. Existing configuration was not changed."
                )
            self.notify("Starting the backend...")
            process = self.start_process(
                [python, "-m", "app"], self.root / "backend", "backend"
            )
            self.wait_until(lambda: api_identity(BACKEND_URL), process, "backend")

        self.notify("Checking PostgreSQL and application services...")
        body = get(BACKEND_URL + "/api/v1/health", timeout=35)
        try:
            health = json.loads(body) if body else {}
        except ValueError:
            health = {}
        if health.get("status") != "ok" or health.get("persistence") != "postgresql":
            raise StartupError(
                "The backend cannot confirm its PostgreSQL connection. Check your network and try again. "
                "No database or API settings were changed."
            )

        self.notify("Checking the website...")
        if listening(5174):
            if not self.frontend_identity():
                raise StartupError(
                    "Port 5174 is occupied by another or unresponsive application. Nothing was stopped."
                )
        else:
            vite = self.root / "frontend" / "node_modules" / "vite" / "bin" / "vite.js"
            if not vite.is_file():
                raise StartupError(
                    "Frontend dependencies are missing. Restore the project's existing frontend environment."
                )
            env = {
                **os.environ,
                "API_PROXY_TARGET": BACKEND_URL,
                "VITE_API_BASE_URL": "/api/v1",
            }
            self.notify("Starting the website...")
            process = self.start_process(
                [
                    self.node(),
                    vite,
                    "--host",
                    "127.0.0.1",
                    "--port",
                    "5174",
                    "--strictPort",
                ],
                self.root / "frontend",
                "frontend",
                env,
            )
            self.wait_until(self.frontend_identity, process, "frontend")

        # Check the actual frontend proxy; never open a disconnected browser demo.
        self.notify("Checking the website connection...")
        proxy_body = get(FRONTEND_URL + "/api/v1/health", timeout=35)
        try:
            proxy_health = json.loads(proxy_body) if proxy_body else {}
        except ValueError:
            proxy_health = {}
        if (
            proxy_health.get("status") != "ok"
            or proxy_health.get("persistence") != "postgresql"
        ):
            raise StartupError(
                "The website cannot reach the backend. Check the frontend proxy configuration."
            )
        self.notify("Opening MotorAI...")
        if open_browser and not webbrowser.open(FRONTEND_URL + "/", new=2):
            raise StartupError(
                "The app is running. Open http://127.0.0.1:5174 in your browser."
            )
        return {"ready": True, "url": FRONTEND_URL + "/"}


@contextmanager
def startup_lock():
    # Only lock startup, so subsequent double-clicks can reopen the ready app.
    import msvcrt

    folder = ROOT / ".local-tools" / "logs"
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / "motorai-startup.lock").open("a+b") as lock:
        lock.seek(0, 2)
        if lock.tell() == 0:
            lock.write(b"0")
            lock.flush()
        lock.seek(0)
        try:
            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            raise StartupError(
                "MotorAI is already starting. Please wait for the first launch to finish."
            ) from None
        try:
            yield
        finally:
            lock.seek(0)
            msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)


def execute(notify, open_browser):
    with startup_lock():
        result = Launcher(notify=notify).run(open_browser=open_browser)
        from datetime import datetime

        (ROOT / ".local-tools" / "logs" / "motorai-last-start.json").write_text(
            json.dumps({**result, "checked_at": datetime.now(UTC).isoformat()}) + "\n",
            encoding="utf-8",
        )
        return result


def show_error(message):
    import ctypes

    ctypes.windll.user32.MessageBoxW(None, message, "MotorAI", 0x10)


def window(open_browser):
    import tkinter as tk
    from tkinter import ttk

    root = tk.Tk()
    root.title("MotorAI")
    root.geometry("460x170")
    root.resizable(False, False)
    root.configure(bg="#081b23")
    root.attributes("-topmost", True)
    tk.Label(
        root, text="MotorAI", fg="#70e2e0", bg="#081b23", font=("Segoe UI", 22, "bold")
    ).pack(pady=(18, 5))
    status = tk.StringVar(value="Starting your workspace...")
    tk.Label(
        root, textvariable=status, fg="#e4edf0", bg="#081b23", font=("Segoe UI", 10)
    ).pack()
    bar = ttk.Progressbar(root, mode="indeterminate", length=390)
    bar.pack(pady=18)
    bar.start()
    events = queue.Queue()

    def work():
        try:
            execute(lambda message: events.put(("status", message)), open_browser)
            events.put(("done", None))
        except StartupError as error:
            events.put(("error", str(error)))
        except Exception:  # noqa: BLE001 - Final desktop boundary must not expose raw errors.
            events.put(
                (
                    "error",
                    "MotorAI could not start. Check the local project environment.",
                )
            )

    def poll():
        while not events.empty():
            kind, value = events.get()
            if kind in {"done", "error"}:
                root.destroy()
                if kind == "error":
                    show_error(value)
                return
            status.set(value)
        root.after(100, poll)

    threading.Thread(target=work, daemon=True).start()
    root.after(100, poll)
    root.mainloop()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Check/start services without opening a browser",
    )
    parser.add_argument(
        "--no-window", action="store_true", help="Console-only verification mode"
    )
    args = parser.parse_args()
    if args.no_window:
        try:
            print(json.dumps(execute(lambda message: None, not args.no_browser)))
            return 0
        except StartupError as error:
            print(json.dumps({"ready": False, "error": str(error)}))
            return 1
    try:
        window(not args.no_browser)
    except Exception:  # noqa: BLE001 - The GUI may be unavailable in a local Python build.
        show_error(
            "The MotorAI startup window could not open. Check the local Python environment."
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
