"""Demonstrate typed SSE stream events with opencode.

Usage:
    python live_stream_events.py "Your prompt here"

Shows how to subscribe to raw SSE events and use the typed Pydantic models
(StreamEvent, MessagePartDeltaProps, MessageUpdatedProps, etc.)
"""

import sys
from typing import Any

import httpx

from opencode import Opencode
from opencode._stream_events import (
    MessagePartDeltaProps,
    MessagePartUpdatedProps,
    MessageUpdatedProps,
    SessionStatusProps,
    parse_stream_event,
)


def main(prompt: str) -> None:
    with Opencode() as ai:
        session = ai.create_session()
        body: dict[str, Any] = {"parts": [{"type": "text", "text": prompt}]}

        # Subscribe to raw SSE stream before sending
        response = ai.client.event_subscribe()
        assert isinstance(response, httpx.Response)

        ai.client.session_send(session.id, body)

        assistant_text = ""
        part_types: dict[str, str] = {}
        parts_with_deltas: set[str] = set()
        assistant_started = False

        for line in response.iter_lines():
            if not line.startswith("data: "):
                continue

            # --- Typed parsing ---
            event = parse_stream_event(line[6:])
            props = event.properties

            # Skip other sessions
            sid = props.get("sessionID")
            if sid is not None and sid != session.id:
                continue

            # --- Pattern-match on typed models ---
            if event.type == "message.updated":
                p_msg = MessageUpdatedProps.model_construct(**props)
                if p_msg.info.get("role") == "assistant" and not assistant_started:
                    assistant_started = True
                    print("[assistant started]")

            elif event.type == "message.part.updated":
                p_part = MessagePartUpdatedProps.model_construct(**props)
                part_id = p_part.part.get("id", "")
                part_type = p_part.part.get("type", "")
                if part_id and part_type:
                    part_types[part_id] = part_type
                if part_type == "reasoning":
                    continue
                if assistant_started and part_type == "text":
                    text = p_part.part.get("text", "")
                    if text and part_id not in parts_with_deltas:
                        print(text, end="", flush=True)
                        assistant_text += text

            elif event.type == "message.part.delta":
                p_delta = MessagePartDeltaProps.model_construct(**props)
                part_id = p_delta.partID
                part_type = part_types.get(part_id)
                if assistant_started and part_type == "text" and p_delta.delta:
                    parts_with_deltas.add(part_id)
                    print(p_delta.delta, end="", flush=True)
                    assistant_text += p_delta.delta

            elif event.type == "session.status":
                p_status = SessionStatusProps.model_construct(**props)
                if p_status.status.get("type") == "idle":
                    print()
                    break

            elif event.type == "session.idle":
                print()
                break

        # Show typed properties summary
        print(f"\n--- Response length: {len(assistant_text)} chars ---")
        print(f"--- Event types seen: {event.type} ---")
        print(f"--- Properties keys: {list(props.keys())} ---")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python live_stream_events.py \"your prompt\"")
        sys.exit(1)
    main(sys.argv[1])
