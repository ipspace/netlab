#!/usr/bin/env python3
#
# netlab api command: lightweight HTTP wrapper for CLI actions
#
import argparse
import base64
import binascii
import contextlib
import datetime as dt
import hmac
import io
import json
import os
import ssl
import tempfile
import threading
import time
import traceback
import urllib.parse
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from ..utils import log
from . import collect as netlab_collect
from . import create as netlab_create
from . import down as netlab_down
from . import status as netlab_status
from . import up as netlab_up

DEFAULT_DATA_DIR = Path(tempfile.gettempdir()) / "netlab" / "api"

JOB_LOCK = threading.Lock()
JOBS: Dict[str, Dict[str, Any]] = {}
JOB_THREADS: Dict[str, threading.Thread] = {}
RUN_LOCK = threading.Lock()

AUTH_USER: Optional[str] = None
AUTH_PASSWORD: Optional[str] = None

def now_iso() -> str:
  return dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def data_dir() -> Path:
  return Path(os.getenv("NETLAB_API_DATA_DIR", str(DEFAULT_DATA_DIR))).expanduser()


def log_dir() -> Path:
  path = data_dir() / "logs"
  path.mkdir(parents=True, exist_ok=True)
  return path


def payload_str(payload: Dict[str, Any], key: str) -> Optional[str]:
  value = payload.get(key)
  if not isinstance(value, str):
    return None
  value = value.strip()
  return value or None


def resolve_path(path: str, base: Path) -> Path:
  candidate = Path(path).expanduser()
  if not candidate.is_absolute():
    candidate = base / candidate
  return candidate.resolve()


def parse_basic_auth(header: str) -> Optional[Tuple[str, str]]:
  if not header.startswith("Basic "):
    return None

  encoded = header[6:].strip()
  try:
    decoded = base64.b64decode(encoded.encode("ascii"), validate=True).decode("utf-8")
  except (binascii.Error, UnicodeDecodeError, ValueError):
    return None

  if ":" not in decoded:
    return None

  user, password = decoded.split(":", 1)
  return user, password


def auth_configured() -> bool:
  return AUTH_USER is not None and AUTH_PASSWORD is not None


def send_unauthorized(handler: BaseHTTPRequestHandler) -> None:
  payload = {"error": "unauthorized"}
  data = json.dumps(payload).encode("utf-8")
  handler.send_response(HTTPStatus.UNAUTHORIZED)
  handler.send_header("WWW-Authenticate", 'Basic realm="netlab api"')
  handler.send_header("Content-Type", "application/json")
  handler.send_header("Content-Length", str(len(data)))
  handler.end_headers()
  handler.wfile.write(data)


def require_auth(handler: BaseHTTPRequestHandler) -> bool:
  if not auth_configured():
    return True

  creds = parse_basic_auth(handler.headers.get("Authorization", ""))
  if creds is None:
    send_unauthorized(handler)
    return False

  user, password = creds
  auth_user = AUTH_USER
  auth_password = AUTH_PASSWORD
  if auth_user is None or auth_password is None:
    send_unauthorized(handler)
    return False

  if hmac.compare_digest(user, auth_user) and hmac.compare_digest(password, auth_password):
    return True

  send_unauthorized(handler)
  return False


def workspace_dir(payload: Dict[str, Any]) -> Path:
  base = Path.cwd()
  raw_path = payload_str(payload, "workdir") or payload_str(payload, "workspaceRoot") or str(base)
  return resolve_path(raw_path, base)


def resolve_topology(payload: Dict[str, Any], workdir: Path) -> str:
  topology_url = payload_str(payload, "topologyUrl")
  if topology_url:
    return topology_url
  topology_path = payload_str(payload, "topologyPath")
  if not topology_path:
    for candidate in ("netlab/topology.yml", "netlab/topology.yaml"):
      if (workdir / candidate).exists():
        topology_path = candidate
        break
  if not topology_path:
    raise ValueError("topologyPath or topologyUrl required")
  return str(resolve_path(topology_path, workdir))


def list_templates(template_dir: str) -> List[Dict[str, str]]:
  results: List[Dict[str, str]] = []
  if not template_dir:
    return results

  template_path = Path(template_dir).expanduser()
  if not template_path.is_dir():
    return results

  templates = list(template_path.glob("*.yml")) + list(template_path.glob("*.yaml"))
  for template in sorted(set(templates), key=lambda p: p.name):
    rel = template.relative_to(template_path).as_posix()
    results.append({"name": rel, "path": rel})
  return results


def add_flag(args: List[str], payload: Dict[str, Any], key: str, flag: str) -> None:
  if payload.get(key):
    args.append(flag)


def add_opt(args: List[str], payload: Dict[str, Any], key: str, opt: str) -> None:
  value = payload.get(key)
  if value is None or value == "":
    return
  args += [opt, str(value)]


def action_runner(payload: Dict[str, Any], workdir: Path) -> Tuple[Callable[..., Any], List[str]]:
  action = (payload.get("action") or "up").strip().lower()

  def run_up() -> Tuple[Callable[..., Any], List[str]]:
    return netlab_up.run, [resolve_topology(payload, workdir)]

  def run_create() -> Tuple[Callable[..., Any], List[str]]:
    return netlab_create.run, [resolve_topology(payload, workdir)]

  def run_down() -> Tuple[Callable[..., Any], List[str]]:
    args: List[str] = []
    add_flag(args, payload, "cleanup", "--cleanup")
    return netlab_down.run, args

  def run_collect() -> Tuple[Callable[..., Any], List[str]]:
    args: List[str] = []
    add_opt(args, payload, "instance", "--instance")
    add_opt(args, payload, "collectOutput", "--output")
    add_opt(args, payload, "collectTar", "--tar")
    add_flag(args, payload, "collectCleanup", "--cleanup")
    return netlab_collect.run, args

  def run_status() -> Tuple[Callable[..., Any], List[str]]:
    args: List[str] = ["--all"]
    if payload.get("instance"):
      args = ["--instance", str(payload.get("instance"))]
    return netlab_status.run, args

  handlers: Dict[str, Callable[[], Tuple[Callable[..., Any], List[str]]]] = {
    "up": run_up,
    "create": run_create,
    "down": run_down,
    "collect": run_collect,
    "status": run_status,
  }

  try:
    return handlers[action]()
  except KeyError as exc:
    raise ValueError(f"unknown action {action}") from exc


def run_netlab_action(payload: Dict[str, Any], log_fp: io.TextIOBase) -> None:
  workdir = workspace_dir(payload)

  def _run_with_output(fn: Callable[..., Any], args: List[str]) -> None:
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
      fn(args)
    log_fp.write(out.getvalue())

  prev_cwd = os.getcwd()
  try:
    os.chdir(workdir)
    fn, args = action_runner(payload, workdir)
    _run_with_output(fn, args)
  finally:
    os.chdir(prev_cwd)


def job_public(job: Dict[str, Any]) -> Dict[str, Any]:
  return {k: v for k, v in job.items() if k != "thread"}


def start_job(payload: Dict[str, Any]) -> Dict[str, Any]:
  job_id = f"job-{int(time.time() * 1000)}-{os.urandom(3).hex()}"
  log_path = str(log_dir() / f"{job_id}.log")
  job = {
    "id": job_id,
    "action": payload.get("action") or "up",
    "state": "queued",
    "createdAt": now_iso(),
    "startedAt": None,
    "finishedAt": None,
    "error": None,
    "workdir": None,
    "logPath": log_path,
  }

  def _runner() -> None:
    with JOB_LOCK:
      if job["state"] == "canceled":
        return
      job["state"] = "running"
      job["startedAt"] = now_iso()

    try:
      job["workdir"] = str(workspace_dir(payload))
      with RUN_LOCK:
        with open(log_path, "w", encoding="utf-8") as log_fp:
          run_netlab_action(payload, log_fp)
      job["state"] = "success"
    except Exception as exc:
      job["state"] = "failed"
      job["error"] = f"{exc}"
      with open(log_path, "a", encoding="utf-8") as log_fp:
        log_fp.write("\n")
        log_fp.write(traceback.format_exc())
    finally:
      job["finishedAt"] = now_iso()

  thread = threading.Thread(target=_runner, daemon=True)
  with JOB_LOCK:
    JOBS[job_id] = job
    JOB_THREADS[job_id] = thread
  thread.start()
  return job_public(job)


def parse_json_body(handler: BaseHTTPRequestHandler) -> Dict[str, Any]:
  length = int(handler.headers.get("Content-Length", "0") or "0")
  if not length:
    return {}
  raw = handler.rfile.read(length)
  if not raw:
    return {}
  try:
    return json.loads(raw.decode("utf-8"))
  except (json.JSONDecodeError, UnicodeDecodeError) as exc:
    raise ValueError("invalid JSON body") from exc


def send_json(handler: BaseHTTPRequestHandler, status: int, payload: Any) -> None:
  data = json.dumps(payload).encode("utf-8")
  handler.send_response(status)
  handler.send_header("Content-Type", "application/json")
  handler.send_header("Content-Length", str(len(data)))
  handler.end_headers()
  handler.wfile.write(data)


class NetlabHandler(BaseHTTPRequestHandler):
  def log_message(self, format: str, *args: Any) -> None:
    return

  def _not_found(self) -> None:
    send_json(self, HTTPStatus.NOT_FOUND, {"error": "not found"})

  def do_GET(self) -> None:
    if not require_auth(self):
      return
    parsed = urllib.parse.urlparse(self.path)
    parts = [p for p in parsed.path.strip("/").split("/") if p]
    if not parts:
      return self._not_found()

    def get_healthz() -> None:
      send_json(self, HTTPStatus.OK, {"status": "ok"})

    def get_templates() -> None:
      query = urllib.parse.parse_qs(parsed.query)
      template_dir = query.get("dir", [""])[0]
      send_json(self, HTTPStatus.OK, {"templates": list_templates(template_dir)})

    def get_jobs() -> None:
      with JOB_LOCK:
        jobs = [job_public(j) for j in JOBS.values()]
      send_json(self, HTTPStatus.OK, {"jobs": jobs})

    def get_status() -> None:
      out = io.StringIO()
      with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
        netlab_status.run(["--all"])
      send_json(self, HTTPStatus.OK, {"status": out.getvalue()})

    handlers: Dict[Tuple[str, ...], Callable[[], None]] = {
      ("healthz",): get_healthz,
      ("templates",): get_templates,
      ("jobs",): get_jobs,
      ("status",): get_status,
    }

    key = tuple(parts)
    if key in handlers:
      handlers[key]()
      return

    if parts[0] == "jobs" and len(parts) >= 2:
      job_id = parts[1]
      with JOB_LOCK:
        job: Optional[Dict[str, Any]] = JOBS.get(job_id)
      if job is None:
        return self._not_found()
      if len(parts) == 2:
        send_json(self, HTTPStatus.OK, job_public(job))
        return
      if len(parts) == 3 and parts[2] == "log":
        try:
          with open(job["logPath"], "r", encoding="utf-8") as fp:
            content = fp.read()
        except FileNotFoundError:
          content = ""
        send_json(self, HTTPStatus.OK, {"log": content})
        return

    self._not_found()

  def do_POST(self) -> None:
    if not require_auth(self):
      return
    parsed = urllib.parse.urlparse(self.path)
    parts = [p for p in parsed.path.strip("/").split("/") if p]
    if parts == ["jobs"]:
      try:
        payload = parse_json_body(self)
        job = start_job(payload)
      except ValueError as exc:
        send_json(self, HTTPStatus.BAD_REQUEST, {"error": str(exc)})
        return
      send_json(self, HTTPStatus.ACCEPTED, job)
      return

    if len(parts) == 3 and parts[0] == "jobs" and parts[2] == "cancel":
      job_id = parts[1]
      with JOB_LOCK:
        job_entry: Optional[Dict[str, Any]] = JOBS.get(job_id)
        if job_entry is None:
          return self._not_found()
        if job_entry["state"] != "queued":
          send_json(self, HTTPStatus.CONFLICT, {"error": "cannot cancel running or finished job"})
          return
        job_entry["state"] = "canceled"
        job_entry["finishedAt"] = now_iso()
      send_json(self, HTTPStatus.OK, job_public(job_entry))
      return

    self._not_found()


def api_parse_args() -> argparse.ArgumentParser:
  parser = argparse.ArgumentParser(description="netlab API server")
  parser.add_argument(
    "--bind",
    default=os.getenv("NETLAB_API_BIND", "127.0.0.1"),
    help="Bind address (NETLAB_API_BIND)",
  )
  parser.add_argument(
    "--port",
    type=int,
    default=int(os.getenv("NETLAB_API_PORT", "8090")),
    help="Listen port (NETLAB_API_PORT)",
  )
  parser.add_argument(
    "--auth-user",
    default=os.getenv("NETLAB_API_USER", ""),
    help="Basic auth username (NETLAB_API_USER)",
  )
  parser.add_argument(
    "--auth-password",
    default=os.getenv("NETLAB_API_PASSWORD", ""),
    help="Basic auth password (NETLAB_API_PASSWORD)",
  )
  parser.add_argument(
    "--tls-cert",
    default=os.getenv("NETLAB_API_TLS_CERT", ""),
    help="TLS certificate path (NETLAB_API_TLS_CERT)",
  )
  parser.add_argument(
    "--tls-key",
    default=os.getenv("NETLAB_API_TLS_KEY", ""),
    help="TLS private key path (NETLAB_API_TLS_KEY)",
  )
  return parser


def run(cli_args: List[str]) -> None:
  parser = api_parse_args()
  args = parser.parse_args(cli_args)
  auth_user = args.auth_user.strip() or None
  auth_password = args.auth_password.strip() or None
  if (auth_user is None) != (auth_password is None):
    log.fatal("Basic auth requires both user and password")
  global AUTH_USER, AUTH_PASSWORD
  AUTH_USER = auth_user
  AUTH_PASSWORD = auth_password

  tls_cert = args.tls_cert.strip() or None
  tls_key = args.tls_key.strip() or None
  if (tls_cert is None) != (tls_key is None):
    log.fatal("TLS requires both --tls-cert and --tls-key")
  server = ThreadingHTTPServer((args.bind, args.port), NetlabHandler)
  if tls_cert and tls_key:
    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    context.load_cert_chain(certfile=tls_cert, keyfile=tls_key)
    server.socket = context.wrap_socket(server.socket, server_side=True)
  log.section_header("Starting", f"netlab API on {args.bind}:{args.port}")
  server.serve_forever()
