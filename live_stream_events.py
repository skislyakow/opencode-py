"""Demonstrate typed SSE stream events with opencode.

Usage:
    python live_stream_events.py "Your prompt here"

Subscribes to the raw v2 event stream (``GET /api/event``) and uses the typed
Pydantic models (StreamEvent, SessionTextDeltaProps, ...).
"""

import sys

from opencode import Opencode
from opencode._stream_events import (
    SessionExecutionFailedProps,
    SessionTextDeltaProps,
    SessionToolInputStartedProps,
    parse_stream_event,
)


def main(prompt: str) -> None:
    with Opencode() as ai:
        session = ai.create_session()

        # Subscribe to the raw SSE stream before sending
        stream = ai.client.event_subscribe()
        ai.client.session_prompt(session.id, prompt)

        assistant_text = ""
        seen: list[str] = []
        try:
            for line in stream.iter_lines():
                if not line.startswith("data:"):
                    continue
                event = parse_stream_event(line[5:].strip())
                if event.session_id != session.id:
                    continue
                seen.append(event.type)

                if event.type == "session.text.delta":
                    delta = SessionTextDeltaProps.model_construct(**event.properties).delta
                    print(delta, end="", flush=True)
                    assistant_text += delta
                elif event.type == "session.tool.input.started":
                    tool = SessionToolInputStartedProps.model_construct(**event.properties)
                    print(f"\n[tool] {tool.name}")
                elif event.type == "session.execution.failed":
                    failed = SessionExecutionFailedProps.model_construct(**event.properties)
                    print(f"\n[failed] {failed.error}")
                    break
                elif event.type in ("session.execution.succeeded", "session.execution.interrupted"):
                    print()
                    break
        finally:
            stream.close()

        print(f"\n--- Response length: {len(assistant_text)} chars ---")
        print(f"--- Event types seen: {sorted(set(seen))} ---")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('Usage: python live_stream_events.py "your prompt"')
        sys.exit(1)
    main(sys.argv[1])
