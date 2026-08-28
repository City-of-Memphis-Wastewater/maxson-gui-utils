#!/usr/bin/env python3
# src/maxson_gui_utils/streams.py

class GuiStream:
    """
    File-like stream that forwards writes to a callback.
    Used to redirect stdout/stderr into a TextPane.
    """

    def __init__(self, callback):
        self.callback = callback

    def write(self, text):
        if text.strip():
            self.callback(text)
        return len(text)

    def flush(self):
        pass


class TeeStream:
    """
    Duplicate writes to multiple streams.
    """

    def __init__(self, *streams):
        self.streams = streams

    def write(self, text):
        for s in self.streams:
            s.write(text)
        return len(text)

    def flush(self):
        for s in self.streams:
            s.flush()
