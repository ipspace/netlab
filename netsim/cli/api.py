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
import threading
import time
import traceback
import urllib.parse
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable, Dict, List, Optional

from ..utils import log
from . import collect as netlab_collect
from . import create as netlab_create
from . import down as netlab_down
from . import status as netlab_status
from . import up as netlab_up

DATA_DIR = os.getenv("NETLAB_API_DATA_DIR", "/var/lib/netlab/api")
LOG_DIR = os.path.join(DATA_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

JOB_LOCK = threading.Lock()
JOBS: Dict[str, Dict[str, Any]] = {}

AUTH_USER: Optional[str] = None
AUTH_PASSWORD: Optional[str] = None

def now_iso() -> str:
  return dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


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

  header = handler.headers.get("Authorization", "")
  if not header.startswith("Basic "):
    send_unauthorized(handler)
    return False

  encoded = header[6:].strip()
  try:
    decoded = base64.b64decode(encoded.encode("ascii"), validate=True).decode("utf-8")
  except (binascii.Error, UnicodeDecodeError, ValueError):
    send_unauthorized(handler)
    return False

  if ":" not in decoded:
    send_unauthorized(handler)
    return False

  user, password = decoded.split(":", 1)
  auth_user = AUTH_USER
  auth_password = AUTH_PASSWORD
  if auth_user is None or auth_password is None:
    send_unauthorized(handler)
    return False

  if hmac.compare_digest(user, auth_user) and hmac.compare_digest(password, auth_password):
    return True

  send_unauthorized(handler)
  return False


def workspace_dir(payload: Dict[str, Any]) -> str:
  workdir = (payload.get("workdir") or "").strip()
  if workdir:
    if os.path.isabs(workdir):
      return workdir
    return os.path.join(os.getcwd(), workdir)

  root = (payload.get("workspaceRoot") or "").strip()
  if root:
    return root

  return os.getcwd()


def resolve_topology(payload: Dict[str, Any], workdir: str) -> str:
  topology_url = (payload.get("topologyUrl") or "").strip()
  if topology_url:
    return topology_url
  topology_path = (payload.get("topologyPath") or "").strip()
  if not topology_path:
    for candidate in ("netlab/topology.yml", "netlab/topology.yaml"):
      if os.path.exists(os.path.join(workdir, candidate)):
        topology_path = candidate
        break
  if not topology_path:
    raise ValueError("topologyPath or topologyUrl required")
  if os.path.isabs(topology_path):
    return topology_path
  return os.path.join(workdir, topology_path)


def list_templates(template_dir: str) -> List[Dict[str, str]]:
  results: List[Dict[str, str]] = []
  if not template_dir:
    return results
  for root, dirs, files in os.walk(template_dir):
    dirs[:] = [d for d in dirs if not d.startswith(".")]
    for name in sorted(files):
      if not name.endswith((".yml", ".yaml")):
        continue
      rel = os.path.relpath(os.path.join(root, name), template_dir)
      results.append({"name": rel, "path": rel})
    break
  return results


def run_netlab_action(payload: Dict[str, Any], log_fp: io.TextIOBase) -> None:
  action = (payload.get("action") or "up").strip().lower()
  workdir = workspace_dir(payload)
  def _run_with_output(fn: Callable[[List[str]], None], args: List[str]) -> None:
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
      fn(args)
    log_fp.write(out.getvalue())

  prev_cwd = os.getcwd()
  try:
    os.chdir(workdir)
    if action == "up":
      topology = resolve_topology(payload, workdir)
      _run_with_output(netlab_up.run, [topology])
    elif action == "create":
      topology = resolve_topology(payload, workdir)
      _run_with_output(netlab_create.run, [topology])
    elif action == "down":
      args: List[str] = []
      if payload.get("cleanup"):
        args.append("--cleanup")
      _run_with_output(netlab_down.run, args)
    elif action == "collect":
      args = []
      if payload.get("instance"):
        args += ["--instance", str(payload.get("instance"))]
      output_dir = payload.get("collectOutput")
      if output_dir:
        args += ["--output", output_dir]
      tarball = payload.get("collectTar")
      if tarball:
        args += ["--tar", tarball]
      if payload.get("collectCleanup"):
        args.append("--cleanup")
      _run_with_output(netlab_collect.run, args)
    elif action == "status":
      args = ["--all"]
      if payload.get("instance"):
        args = ["--instance", str(payload.get("instance"))]
      _run_with_output(netlab_status.run, args)
    else:
      raise ValueError(f"unknown action {action}")
  finally:
    os.chdir(prev_cwd)


def start_job(payload: Dict[str, Any]) -> Dict[str, Any]:
  job_id = f"job-{int(time.time() * 1000)}-{os.urandom(3).hex()}"
  log_path = os.path.join(LOG_DIR, f"{job_id}.log")
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
    job["state"] = "running"
    job["startedAt"] = now_iso()
    try:
      job["workdir"] = workspace_dir(payload)
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
  job["thread"] = thread
  with JOB_LOCK:
    JOBS[job_id] = job
  thread.start()
  return job


def parse_json_body(handler: BaseHTTPRequestHandler) -> Dict[str, Any]:
  length = int(handler.headers.get("Content-Length", "0") or "0")
  if not length:
    return {}
  raw = handler.rfile.read(length)
  if not raw:
    return {}
  return json.loads(raw.decode("utf-8"))


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

  def do_GET(self) -> None:
    if not require_auth(self):
      return
    parsed = urllib.parse.urlparse(self.path)
    parts = [p for p in parsed.path.strip("/").split("/") if p]
    if not parts:
      send_json(self, HTTPStatus.NOT_FOUND, {"error": "not found"})
      return

    if parts == ["healthz"]:
      send_json(self, HTTPStatus.OK, {"status": "ok"})
      return

    if parts == ["templates"]:
      query = urllib.parse.parse_qs(parsed.query)
      template_dir = query.get("dir", [""])[0]
      send_json(self, HTTPStatus.OK, {"templates": list_templates(template_dir)})
      return

    if parts == ["jobs"]:
      with JOB_LOCK:
        jobs = list(JOBS.values())
      send_json(self, HTTPStatus.OK, {"jobs": jobs})
      return

    if len(parts) >= 2 and parts[0] == "jobs":
      job_id = parts[1]
      with JOB_LOCK:
        job = JOBS.get(job_id)
      if job is None:
        send_json(self, HTTPStatus.NOT_FOUND, {"error": "not found"})
        return
      if len(parts) == 2:
        send_json(self, HTTPStatus.OK, job)
        return
      if len(parts) == 3 and parts[2] == "log":
        try:
          with open(job["logPath"], "r", encoding="utf-8") as fp:
            content = fp.read()
        except FileNotFoundError:
          content = ""
        send_json(self, HTTPStatus.OK, {"log": content})
        return

    if parts == ["status"]:
      out = io.StringIO()
      with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
        netlab_status.run(["--all"])
      send_json(self, HTTPStatus.OK, {"status": out.getvalue()})
      return

    send_json(self, HTTPStatus.NOT_FOUND, {"error": "not found"})

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
        job = JOBS.get(job_id)
        if job is None:
          send_json(self, HTTPStatus.NOT_FOUND, {"error": "not found"})
          return
        job["state"] = "canceled"
        job["finishedAt"] = now_iso()
      send_json(self, HTTPStatus.OK, job)
      return

    send_json(self, HTTPStatus.NOT_FOUND, {"error": "not found"})


def run(cli_args: List[str]) -> None:
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
