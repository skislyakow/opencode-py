# Changelog

## Unreleased — opencode v2 API (breaking)

opencode v2 (tested with v2.3.2) removed the v1 HTTP API: every endpoint now
lives under `/api/*` behind HTTP Basic auth, so v1 calls such as
`POST /session` fail with `405 Method Not Allowed`.

- fix(server): `create_opencode_server()` generates a password, passes it via
  `OPENCODE_SERVER_PASSWORD` and exposes `server.password` / `server.username`
- feat(client): `password` / `username` on `OpencodeClient` and
  `AsyncOpendcodeClient` (Basic auth; defaults to `$OPENCODE_SERVER_PASSWORD`)
- fix(client): all methods rewritten for the v2 API; `{"data": ...}` envelope
  unwrapped, paginated lists return `PageResponse`, `directory` sent as
  `location[directory]`, SSE subscribe raises on HTTP errors
- fix(client): `copy()` / `with_options()` ignored overrides (inverted `is_given`)
- refactor(client): `_async_client.py` is generated from `_client.py`
- fix(session): `Session.prompt()` uses `POST /api/session/{id}/prompt` + `/api/event`
  until `session.execution.*`; multi-step assistant messages are merged; execution
  failures raise `OpencodeError`; `wait=False` returns the queued user message
- fix(opencode): `Opencode(model=...)` sets the model at session creation;
  `prompt(model=...)` switches it via `POST /api/session/{id}/model`
- fix(stream): `ask_stream()` yields `session.text.delta`
- refactor(tools): tools run on the server; `ToolExecutor` now answers
  `permission.asked` requests (`decide()`), local tool execution removed
- refactor(models): response models and ~100 SSE event models regenerated from
  the v2 `/openapi.json`
- chore(scripts): `check-upstream.py` checks every SDK endpoint against a spec
  (default: the local `opencode serve`)

Removed (no v2 equivalent): `workspace` option, structured output (`format=` now
raises), `session_send` / v1 message endpoints, `session_delete_message`,
`session_todo`, share/unshare, LSP/formatter/tool-list/question/TUI/sync/workspace
endpoints, `max_tool_rounds` / `poll_interval` / `references` parameters.
Renamed: `v2_session_*` -> `session_*`, `file_*` -> `fs_*`, `app_agents` ->
`agent_list`, `v2_model_list` -> `model_list`, `v2_provider_*` -> `provider_*`,
`session_abort` -> `session_interrupt`, `global_event` -> `event_subscribe`;
`health()` now returns `ServerInfoResponse` from `GET /api/info`.

## v0.5.1 (2026-07-05)

- feat(client): add `session_delete_message()` endpoint (`DELETE /session/{sessionID}/message/{messageID}`) — low-level + `Session.delete_message()` / `AsyncSession.delete_message()` convenience methods
- fix(client): replace `# type: ignore` with `cast()` for `RawResponse` return (mypy clean)
- docs(readme): document `session.delete_message()` with usage note about permanent deletion vs `revert()`/`fork()`
- chore(vscode): add `python.defaultInterpreterPath` for Pylance import resolution

## v0.5.0 (2026-07-05)

- feat(stream): add typed Pydantic models for all SSE events (~75 types) — `StreamEvent`, `parse_stream_event()`, `parse_typed_event()`, and `*Props` models for server lifecycle, session, message/part, `session.next.*`, account, catalog, permission, question, PTY, file, VCS, LSP, MCP, installation, project, command, todo, workspace, worktree, and IDE event categories
- refactor(stream): update `ask_stream` (sync + async) to use typed property models (`MessageUpdatedProps`, `MessagePartUpdatedProps`, `MessagePartDeltaProps`, `SessionStatusProps`)
- fix(client): add explicit type annotation for `_response` in `RawResponse`
- feat(demo): add `live_stream_events.py` — typed SSE event inspection demo
- docs(readme): document typed SSE events, `RawResponse`/`with_raw_response`, all demo scripts, `ruff`/`mypy` development commands
- chore(pyproject): ignore N815 in `_stream_events.py`
- chore(vscode): add `.vscode/settings.json` for mypy extension

## v0.4.1 (2026-07-05)

- perf(client): use `model_construct()` instead of `model_validate()` for faster deserialization
- fix(demo): inline ternary to fix mypy assignment type error
- test(client): add 16 `with_raw_response` unit tests (sync + async)
- test(opencode): add 7 `ask_stream` unit tests
- chore(pyproject): ignore E501 (line length) in test files

## v0.4.0 (2026-07-05)

- feat(client): add `with_raw_response` context manager — returns `RawResponse[T]` with `.parsed`, `.status_code`, `.headers`, `.content` for every client method
- feat(client): add `RawResponse[T]` generic wrapper class (sync + async support)
- fix(streaming): filter out `"reasoning"` deltas, user message echo, and duplicate text in `ask_stream`
- chore(demo): add `live_raw.py` — interactive demo of `with_raw_response` with 7 scenarios

## v0.3.0 (2026-07-05)

- feat(client): add typed Pydantic response models (`cast_to`) to all ~75 client methods
- feat(client): add 30+ response model classes (AgentResponse, CommandResponse, ConfigResponse, FileNode, FindMatch, VcsInfo, PtyResponse, WorktreeResponse, WorkspaceResponse, etc.)
- feat(client): `_construct_type` handles generic `list[X]` via `get_origin/get_args` and `{"data": [...]}` response format
- fix(client): `AgentResponse.permission` changed from `dict` to `Any` (server returns list)
- fix(scripts): resolve mypy `no-any-return` in check-upstream.py
- fix(docs): correct web UI port in VERIFY.md (3000, not 8000)
- fix(tests): import SessionMessage from `_models`, not `_session`
- chore(lint): suppress N815 camelCase warnings for `_response_models.py`
- chore(docs): add VERIFY.md release checklist

## v0.2.2 (2026-07-04)

- docs: comprehensive README documentation in EN and RU (CLI flags, structured output, session methods, error hierarchy, ToolExecutor, binary management, OpencodeServer, config reference, async API, response models)
- fix(demo): Pydantic model compatibility
- fix(scripts): mypy errors in check-upstream.py
- docs(readme): clarify binary auto-download behavior (NOT system-wide, NOT in PATH)

## v0.2.1 (2026-07-04)

- fix: rename entry point to `opencode-py` to avoid conflict with the real `opencode` binary

## v0.2.0 (2026-07-03)

- feat: Pydantic response models (HealthResponse, SessionResponse, FileContentResponse, V1SessionResponse)
- feat: retry logic with exponential backoff and jitter
- feat: typed error hierarchy (15+ classes)
- feat: logging via OPENCODE_LOG env var
- feat: async full support (AsyncOpendcodeClient, AsyncSession, AsyncOpendcode)
- feat: streaming (ask_stream sync + async)
- feat: auto_tools mode with ToolExecutor and permissions
- feat: web UI with proxy server (zero dependencies)
- feat: structured output (format parameter)
- feat: OpencodeServer lifecycle management
- feat: binary auto-download (PATH → ~/.opencode/bin/ → GitHub)
- feat: check-upstream.py script for monitoring openapi.json changes
- feat: `.copy()` / `.with_options()` for immutable client cloning
- feat: py.typed marker for PEP 561 compliance

## v0.1.1 (2026-07-03)

- chore: add keywords to pyproject.toml and .gitattributes
- docs: add badges to README and MIT license file
- feat(tests): add Docker smoke test for clean-machine scenario
- chore: use importlib.metadata for `__version__`
- chore: bump version to 0.1.1 for author/URLs fix
- fix(publish): set author to Sergey Kislyakov, fix URLs

## v0.1.0 (2026-06-30)

- feat: initial Python SDK for Opencode
- fix: resolve npm .cmd wrappers to real .exe binary on Windows
- fix(session): use V1 sync prompt with model support instead of V2
- feat(sdk): add keep parameter for multi-turn conversations
- feat(sdk): add auto_tools mode with ToolExecutor and permissions
- feat(web): add zero-dependency web UI with proxy server
- feat(async): add AsyncOpendcodeClient, AsyncSession, AsyncOpendcode
- feat(stream): add live_streaming.py, SSE streaming via ask_stream
- feat(sdk): add async_opencode, structured output, check-upstream
