import threading
import sublime, sublime_plugin

class HistoryList(list):
    """List type for storing the history - fairly
    inefficient, but useful.
    """

    SIZE = 256
    index = 0

    def append(self, item, update_index=True):
        self.insert(0, item)
        if update_index:
            self.index = 0
        if len(self) > self.SIZE:
            del self[self.SIZE:]
    
    def current(self):
        if len(self) == 0:
            return None
        return self[self.index]
    
    def next(self):
        if self.index > 0:
            self.index -= 1
    
    def previous(self):
        if self.index < len(self) - 1:
            self.index += 1

_LOCK = threading.RLock()
_HISTORY = HistoryList()

class ClipboardHistoryBase(sublime_plugin.TextCommand):

    def update_clipboard(self, content):
        sublime.set_clipboard(content)

    def next(self):
        with _LOCK:
            _HISTORY.next()
            self.update_clipboard(_HISTORY.current())

    def previous(self):
        with _LOCK:
            _HISTORY.previous()
            self.update_clipboard(_HISTORY.current())

    def appendClipboard(self):
        with _LOCK:
            # append the contents of the clipboard to the history if it is unique
            if not self.onCurrent():
                _HISTORY.append(sublime.get_clipboard())

    def onCurrent(self):
        return sublime.get_clipboard() == _HISTORY.current()

class ClipboardHistoryPaste(ClipboardHistoryBase):
    def run(self, edit):
        # If the user pastes something that was copied in a different program, it will not be in sublime's buffer, so we attempt to append every time
        self.appendClipboard()
        self.view.run_command('paste')

class ClipboardHistoryPasteAndIndent(ClipboardHistoryBase):
    def run(self, edit):
        self.appendClipboard()
        self.view.run_command('paste_and_indent')

class ClipboardHistoryCut(ClipboardHistoryBase):
    def run(self, edit):
        # First run sublime's command to extract the selected text.
        # This will set the cut/copy'd data on the clipboard which we can easily steal without recreating the cut/copy logic.
        self.view.run_command('cut')
        self.appendClipboard()

class ClipboardHistoryCopy(ClipboardHistoryBase):
    def run(self, edit):
        self.view.run_command('copy')
        self.appendClipboard()

class ClipboardHistoryNext(ClipboardHistoryBase):
    def run(self, edit):
        self.next()

class ClipboardHistoryPrevious(ClipboardHistoryBase):
    def run(self, edit):
        self.previous()

class ClipboardHistoryPreviousAndPaste(ClipboardHistoryBase):
    def run(self, edit):
        self.previous()
        self.view.run_command('paste')

class ClipboardHistoryChooseAndPaste(ClipboardHistoryBase):
    def run(self, edit):
        
        def on_done(idx):
            if idx >= 0:
                with _LOCK:
                    _HISTORY.index = idx
                    self.update_clipboard(_HISTORY.current())
            self.view.run_command('paste')
        
        def format(line):
            return line.replace('\n', '$ ')[:64]

        lines = map(format, _HISTORY)
        sublime.active_window().show_quick_panel(lines, on_done)
