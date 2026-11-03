#!/usr/bin/env bash
#
# Tencent is pleased to support the open source community by making tRPC-Metrics-Runtime available.
#
# Copyright (C) 2026 Tencent. All rights reserved.
#
# tRPC-Metrics-Runtime is licensed under Apache-2.0.
#
# Start the example server, call Greeter.SayHello once, then stop the server.
#
# Usage:
#   ./run_examples.sh                  # same as "service" with trpc_python.yaml
#   ./run_examples.sh service [conf]   # start trpc_main.py, run test_service_rpc.py, stop the server
#   ./run_examples.sh modes            # "service" once per process/thread model config
#   ./run_examples.sh list             # list example names and config files
#
# A conf path is a file name under this directory, or an absolute path.
# The server listen port is 8000, matching the trpc_python*.yaml files.
#
# Environment:
#   PYTHON   interpreter to use (default: ../.venv/bin/python, then ../venv/bin/python, then python3)
set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PKG_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
# Package root first. A sibling checkout of the SDK (../trpc_sdk) is inserted
# ahead of site-packages so this example uses that source.
PYTHONPATH="${PKG_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
SDK_PARENT="$(cd "${PKG_DIR}/.." && pwd)"
if [[ -f "${SDK_PARENT}/trpc_sdk/__init__.py" ]]; then
  PYTHONPATH="${SDK_PARENT}:${PYTHONPATH}"
fi
export PYTHONPATH

if [[ -n "${PYTHON:-}" ]]; then
  PY="${PYTHON}"
elif [[ -x "${PKG_DIR}/.venv/bin/python" ]]; then
  PY="${PKG_DIR}/.venv/bin/python"
elif [[ -x "${PKG_DIR}/venv/bin/python" ]]; then
  PY="${PKG_DIR}/venv/bin/python"
else
  PY="$(command -v python3)"
fi

SERVER_LOG="${SCRIPT_DIR}/.server_run.log"
HELLO_LOG="${SCRIPT_DIR}/hello.log"
SERVER_PID=""
HOST="127.0.0.1"
PORT=8000
REPORTER_MARK="runtime metrics reporter started in pid"

CONFIGS=(
  trpc_python.yaml
  trpc_python_merge_threads.yaml
  trpc_python_separate_thread.yaml
  trpc_python_separate.yaml
  trpc_python_merge_processes.yaml
)

log() { printf '\n\033[1;34m==> %s\033[0m\n' "$*" >&2; }
ok()  { printf '\033[1;32m[PASS]\033[0m %s\n' "$*" >&2; }
bad() { printf '\033[1;31m[FAIL]\033[0m %s\n' "$*" >&2; }

port_open() {
  "${PY}" -c "import socket; s=socket.create_connection(('${HOST}', ${PORT}), 0.2); s.close()" >/dev/null 2>&1
}

wait_ready() {
  local tries=60
  while (( tries-- > 0 )); do
    port_open && return 0
    if [[ -n "${SERVER_PID}" ]] && ! kill -0 "${SERVER_PID}" 2>/dev/null; then
      return 1
    fi
    sleep 0.5
  done
  return 1
}

wait_port_free() {
  local tries=20
  while (( tries-- > 0 )); do
    port_open || return 0
    sleep 0.5
  done
  return 1
}

reporter_logged() {
  grep -q "${REPORTER_MARK}" "${SERVER_LOG}" 2>/dev/null && return 0
  grep -q "${REPORTER_MARK}" "${HELLO_LOG}" 2>/dev/null
}

wait_reporter() {
  local tries=20
  while (( tries-- > 0 )); do
    reporter_logged && return 0
    if [[ -n "${SERVER_PID}" ]] && ! kill -0 "${SERVER_PID}" 2>/dev/null; then
      break
    fi
    sleep 0.5
  done
  reporter_logged
}

resolve_conf() {
  local conf="${1:-${SCRIPT_DIR}/trpc_python.yaml}"
  if [[ "${conf}" != /* ]]; then
    if [[ -f "${SCRIPT_DIR}/${conf}" ]]; then
      conf="${SCRIPT_DIR}/${conf}"
    fi
  fi
  if [[ ! -f "${conf}" ]]; then
    bad "config not found: ${conf}"
    return 1
  fi
  printf '%s\n' "${conf}"
}

start_server() {
  local conf="$1"
  if port_open; then
    bad "port ${PORT} is already in use; stop that process first"
    return 1
  fi
  log "starting server: ${conf}"
  : > "${SERVER_LOG}"
  : > "${HELLO_LOG}"
  # `exec` makes the subshell become the python process, so $! is its pid.
  ( cd "${SCRIPT_DIR}" && exec "${PY}" trpc_main.py --conf "${conf}" ) >>"${SERVER_LOG}" 2>&1 &
  SERVER_PID=$!
  if ! wait_ready; then
    bad "server did not start listening on ${PORT}; last log lines:"
    tail -n 40 "${SERVER_LOG}" || true
    stop_server
    return 1
  fi
}

stop_server() {
  [[ -z "${SERVER_PID}" ]] && return 0
  pkill -TERM -P "${SERVER_PID}" 2>/dev/null || true
  kill -TERM "${SERVER_PID}" 2>/dev/null || true
  local _
  for _ in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20; do
    kill -0 "${SERVER_PID}" 2>/dev/null || break
    sleep 0.5
  done
  pkill -KILL -P "${SERVER_PID}" 2>/dev/null || true
  kill -KILL "${SERVER_PID}" 2>/dev/null || true
  wait "${SERVER_PID}" 2>/dev/null || true
  SERVER_PID=""
  if ! wait_port_free; then
    bad "port ${PORT} still in use after stopping the server"
    return 1
  fi
}

run_service() {
  local conf
  conf="$(resolve_conf "${1:-}")" || return 1
  start_server "${conf}" || return 1
  log "running example: service (test_service_rpc.py)"
  local rc=0
  local client_out=""
  client_out="$(cd "${SCRIPT_DIR}" && "${PY}" test_service_rpc.py 2>&1)" || rc=$?
  printf '%s\n' "${client_out}"
  if [[ ${rc} -eq 0 && "${client_out}" != *"hello: hello"* ]]; then
    bad "client reply missing hello: hello"
    rc=1
  fi
  if ! wait_reporter; then
    bad "server log missing '${REPORTER_MARK}'"
    tail -n 40 "${SERVER_LOG}" || true
    rc=1
  fi
  stop_server || rc=1
  if [[ ${rc} -eq 0 ]]; then
    ok "service $(basename "${conf}")"
  else
    bad "service $(basename "${conf}") (exit ${rc}); server log: ${SERVER_LOG}"
  fi
  return ${rc}
}

run_modes() {
  local rc=0 conf
  for conf in "${CONFIGS[@]}"; do
    run_service "${conf}" || rc=1
  done
  return ${rc}
}

trap 'stop_server' EXIT INT TERM

main() {
  case "${1:-service}" in
    list)
      echo "Available examples: service modes"
      echo "Configs:"
      printf '  %s\n' "${CONFIGS[@]}"
      ;;
    service)
      run_service "${2:-}"
      ;;
    modes)
      run_modes
      ;;
    *)
      bad "unknown example: $1 (try: ./run_examples.sh list)"
      return 2
      ;;
  esac
}

main "$@"
