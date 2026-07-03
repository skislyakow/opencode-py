# Changelog

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
