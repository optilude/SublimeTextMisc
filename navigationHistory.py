import sublime, sublime_plugin
from collections import deque

MAX_SIZE = 64
LINE_THRESHOLD = 2

class History(object):
    """Keep track of the history for a single window
    """

    def __init__(self, max_size=MAX_SIZE):
        self._back = deque([], max_size)
        self._forward = deque([], max_size)
        self._last_location = ("", -100,)
    
    def push(self, path, line):
        """Push the given path and line number to indicate the
        location has changed. Clear the forward history.
        """

        self._back.append((path, line,))
        self._forward.clear()
    
    def mark_location(self, path, line):
        """Remember the current location, for the purposes of being able
        to do a has_changed() check.
        """
        self._last_location = (path, line,)

    def has_changed(self, path, line):
        """Determine if the given path/line combination
        represents a significant enough change to warrant
        pushing history.
        """

        old_path, old_line = self._last_location

        if old_path != path:
            return True
        
        if abs(line - old_line) > LINE_THRESHOLD:
            return True
        
        return False
    
    def record_movement(self, path, line):
        """Record movement to the given location, pushing history if
        applicable
        """

        if path and line:
            if self.has_changed(path, line):
                self.push(path, line)
                print "pushed", path, line, self._back, self._forward
            self.mark_location(path, line)

    def back(self, path, line):
        """Move backward in history, returning the (path, line) tuple to
        jump to, or (None, None) if the history is empty. Should be passed
        the current path and line, which will be added to the forward deque.
        """

        if not self._back:
            return (None, None,)
        
        self._forward.appendleft((path, line,))
        new_path, new_line = self._back.pop()

        # We may still be within the same area as the last recorded jump,
        # in which case we really want to jump back one more
        if new_path == path and new_line == line:
            if self._back:
                new_path, new_line = self._back.pop()
        
        self.mark_location(new_path, new_line)
        return new_path, new_line

    def forward(self, path, line):
        """Move forward in history, returning the (path, line) tuple to
        jump to, or (None, None) if the history is empty. Should be passed
        the current path and line, which will be added to the back deque.
        """

        if not self._forward:
            return (None, None,)
        
        self._back.append((path, line))
        new_path, new_line = self._forward.popleft()

        # if new_path == path and new_line == line:
        #     if self._forward:
        #         new_path, new_line = self._forward.popleft()
        
        self.mark_location(new_path, new_line)
        return new_path, new_line

_histories = {} # window id -> History

def get_history():
    """Get a History object for the current window,
    creating a new one if required
    """

    window = sublime.active_window()
    if window is None:
        return None

    window_id = window.id()
    history = _histories.get(window_id, None)
    if history is None:
        _histories[window_id] = history = History()
    return history

class NavigationHistoryRecorder(sublime_plugin.EventListener):
    """Keep track of history
    """

    def on_selection_modified(self, view):
        """When the selection is changed, possibly record movement in the
        history
        """
        history = get_history()
        if history is None:
            return

        path = view.file_name()
        row, col = view.rowcol(view.sel()[0].a)
        line = row + 1

        # TODO: This mustn't happen when we move due to back() or
        # forward()
        history.record_movement(path, line)
    
    # def on_close(self, view):
    #     """When a view is closed, check to see if the window was closed too
    #     and clean up orphan histories
    #     """
    #
    #     # XXX: This doesn't work - event runs before window is removed
    #     # from sublime.windows()
    #
    #     windows_with_history = set(_histories.keys())
    #     window_ids = set([w.id() for w in sublime.windows()])
    #     closed_windows = windows_with_history.difference(window_ids)
    #     for window_id in closed_windows:
    #         del _histories[window_id]
    
class NavigationHistoryBack(sublime_plugin.TextCommand):
    """Go back in history
    """

    def run(self, edit):
        history = get_history()
        if history is None:
            return

        old_path = self.view.file_name()
        row, col = self.view.rowcol(self.view.sel()[0].a)
        old_line = row + 1

        path, line = history.back(old_path, old_line)

        if path is not None and line is not None:
            window = sublime.active_window()
            window.open_file("%s:%d" % (path, line,), sublime.ENCODED_POSITION)

class NavigationHistoryForward(sublime_plugin.TextCommand):
    """Go forward in history
    """

    def run(self, edit):
        history = get_history()
        if history is None:
            return

        old_path = self.view.file_name()
        row, col = self.view.rowcol(self.view.sel()[0].a)
        old_line = row + 1

        path, line = history.forward(old_path, old_line)

        if path is not None and line is not None:
            window = sublime.active_window()
            window.open_file("%s:%d" % (path, line,), sublime.ENCODED_POSITION)
