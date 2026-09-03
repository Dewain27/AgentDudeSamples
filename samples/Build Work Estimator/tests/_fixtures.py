#!/usr/bin/env python3
"""Synthetic session transcripts for the test suite.

Author: Dewain Robinson

Everything here is fabricated. No test reads real user history.
"""

__author__ = "Dewain Robinson"

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(HERE, "..", "skill", "build-work-estimator", "scripts")
sys.path.insert(0, SCRIPTS)


def assistant(request_id, model="claude-opus-5", inp=2, read=100000,
              w5=0, w1=5000, out=1200, files=(), timestamp="2026-02-01T10:00:00Z"):
    content = [{"type": "text", "text": "ok"}]
    for path in files:
        content.append({
            "type": "tool_use", "name": "Edit",
            "input": {"file_path": path},
        })
    return {
        "type": "assistant",
        "requestId": request_id,
        "uuid": request_id + "-u",
        "timestamp": timestamp,
        "message": {
            "role": "assistant",
            "model": model,
            "content": content,
            "usage": {
                "input_tokens": inp,
                "cache_read_input_tokens": read,
                "output_tokens": out,
                "cache_creation": {
                    "ephemeral_5m_input_tokens": w5,
                    "ephemeral_1h_input_tokens": w1,
                },
            },
        },
    }


def user(text="hi", timestamp="2026-02-01T10:00:00Z"):
    return {"type": "user", "timestamp": timestamp,
            "message": {"role": "user", "content": text}}


def write_session(root, project, session_id, records, subagent_records=None):
    """Write a session transcript, plus optional subagent transcripts."""
    project_dir = os.path.join(root, project)
    if not os.path.isdir(project_dir):
        os.makedirs(project_dir)
    path = os.path.join(project_dir, session_id + ".jsonl")
    with open(path, "w") as fh:
        for record in records:
            fh.write(json.dumps(record) + "\n")

    if subagent_records:
        sub_dir = os.path.join(project_dir, session_id, "subagents")
        os.makedirs(sub_dir)
        sub_path = os.path.join(sub_dir, "agent-aaa1.jsonl")
        with open(sub_path, "w") as fh:
            for record in subagent_records:
                fh.write(json.dumps(record) + "\n")
    return path


def simple_history(root):
    """A small but structurally complete history.

    One medium session (9 files) with subagents, one small session (3 files),
    and one exploration session (no edits).
    """
    write_session(
        root, "-proj-a", "11111111-1111-1111-1111-111111111111",
        [user()] + [
            assistant("r%d" % i, files=["/f/%d.py" % (i % 9)],
                      timestamp="2026-02-0%dT10:00:00Z" % ((i % 8) + 1))
            for i in range(40)
        ],
        subagent_records=[
            assistant("s%d" % i, model="claude-sonnet-5", read=40000, out=500)
            for i in range(12)
        ],
    )
    write_session(
        root, "-proj-a", "22222222-2222-2222-2222-222222222222",
        [user()] + [
            assistant("q%d" % i, files=["/g/%d.py" % (i % 3)],
                      timestamp="2026-02-10T11:00:00Z")
            for i in range(15)
        ],
    )
    write_session(
        root, "-proj-b", "33333333-3333-3333-3333-333333333333",
        [user()] + [
            assistant("e%d" % i, read=30000, out=400,
                      timestamp="2026-02-12T09:00:00Z")
            for i in range(8)
        ],
    )
    return root
