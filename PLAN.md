# Plan: borrow ideas from opencode-runtime

## Tasks

### Task 1: Ephemeral port selection ✅
- [x] In `OpendcodeServer.__init__()`, change `port` default from `4096` to `None`
- [x] In `start()`, if `port is None`: `socket.bind(("", 0))` → extract port → close socket → pass to subprocess
- [x] If port is explicitly given, use it as-is (backward compat)
- [x] Store chosen port in `self.port`
- [x] Update `OpendcodeServer` tests to verify auto-port works
- [x] Update README

### Task 2: Response dataclass with raw events
- [ ] Add `OpencodeResponse` dataclass (or NamedTuple): `text: str`, `events: list[Any]`
- [ ] Modify `ask_stream()` to also collect all raw events
- [ ] Add `collect=True/False` param — when True, returns all events alongside text
- [ ] `Session.prompt()` can optionally return `OpencodeResponse` instead of bare string
- [ ] Tests for event collection

### Task 3: V2 session prompt via SSE (replace V1 polling)
- [ ] Audit `/global/event` SSE endpoint reliability in current opencode server
- [ ] If reliable: rework `Session.prompt()` to use `POST /session/{id}/prompt` + `/event` subscription
- [ ] Keep V1 as fallback
- [ ] Benchmark: polling vs SSE latency difference

## Not planned
- Multi-tenant pool, HOME isolation, registry, materials CLI fleet management — overkill for single-user SDK
