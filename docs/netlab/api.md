(netlab-api)=
# netlab API Server

The **netlab api** command starts a lightweight HTTP server that wraps common
CLI actions. It is intended for automation systems that need to invoke *netlab*
operations without shelling out to the CLI.

```text
netlab api [--bind <addr>] [--port <port>] [--auth-user <user>] [--auth-password <password>]
           [--tls-cert <path>] [--tls-key <path>]
```

## Endpoints

- `GET /healthz` – health check.
- `GET /templates?dir=<path>` – list YAML templates in a directory.
- `POST /jobs` – start a job. Body is JSON with fields such as `action`,
  `workdir`, `workspaceRoot`, `topologyPath`, or `topologyUrl`.
- `GET /jobs` – list jobs.
- `GET /jobs/{id}` – job details.
- `GET /jobs/{id}/log` – job log output.
- `POST /jobs/{id}/cancel` – mark a job as canceled.
- `GET /status` – netlab status output.

## Actions

`action` maps to CLI behaviors:

- `up`
- `create`
- `down`
- `collect`
- `status`

The API runs the same Python CLI modules used by `netlab`, so behavior and
output are consistent with the CLI.

## Authentication

If `NETLAB_API_USER` and `NETLAB_API_PASSWORD` (or the `--auth-user` and
`--auth-password` flags) are set, the server requires HTTP Basic Auth on
all endpoints.

## TLS

If `NETLAB_API_TLS_CERT` and `NETLAB_API_TLS_KEY` (or the `--tls-cert` and
`--tls-key` flags) are set, the server enables HTTPS using those files.

## Working Directory

The API uses the netlab working directory model:

- If `workdir` is set, it is used as the working directory.
- Else, if `workspaceRoot` is set, it becomes the working directory.
- Otherwise, the server's current working directory is used.
