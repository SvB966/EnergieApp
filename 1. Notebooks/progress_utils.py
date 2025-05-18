# progress_utils.py
import time
import threading
from typing import Optional, Tuple

from ipywidgets import IntProgress, Label, HBox, Layout, VBox
from IPython.display import display


class ProgressDisplay:
    """Een klasse om een voortgangsbalk-widget te beheren."""
    def __init__(self, description: str = 'Voortgang:'):
        self.progress_bar = IntProgress(
            value=0, min=0, max=100, step=1, description=description,
            bar_style='info', orientation='horizontal',
            layout=Layout(width='auto', min_width='250px')
        )
        self.status_label = Label(
            value="", layout=Layout(width='auto', margin="0 0 0 10px", min_width='200px')
        )
        self.etr_label = Label(
            value="", layout=Layout(width='auto', margin="0 0 0 10px", min_width='200px')
        )
        self.progress_container = HBox(
            [self.progress_bar, self.status_label, self.etr_label],
            layout=Layout(visibility='hidden', align_items='center',
                          justify_content='flex-start', width='100%', margin="5px 0px")
        )
        self._progress_start_time: Optional[float] = None
        self._timer_thread: Optional[threading.Thread] = None
        self._progress_running: bool = False
        self._current_progress_val: int = 0
        self._current_status_msg: str = ""

    def _calculate_etr(self, elapsed: float, progress: int) -> str:
        if 0 < progress < 100:
            fraction_done = progress / 100.0
            estimated_total_time = elapsed / fraction_done
            remaining_time = estimated_total_time - elapsed
            if remaining_time < 0: remaining_time = 0
            m, s = divmod(remaining_time, 60)
            h, m = divmod(m, 60)
            if h >= 1: return f"ETR: {int(h)}u {int(m)}m {int(s)}s"
            elif m >=1: return f"ETR: {int(m)}m {int(s)}s"
            else: return f"ETR: {int(s)}s"
        return ""

    def _timer_loop(self):
        while self._progress_running:
            if self._progress_start_time is not None and self._current_progress_val > 0 and self._current_progress_val < 100:
                elapsed = time.time() - self._progress_start_time
                self.etr_label.value = self._calculate_etr(elapsed, self._current_progress_val)
            time.sleep(1)

    def update_progress(self, progress: int, status: str = "", error: bool = False):
        """Werk de voortgangsbalk bij."""
        if self.progress_container.layout.visibility == 'hidden':
            self.progress_container.layout.visibility = 'visible'
        if self._progress_start_time is None and progress > 0:
            self._progress_start_time = time.time()
            self._progress_running = True
            if self._timer_thread is None or not self._timer_thread.is_alive():
                self._timer_thread = threading.Thread(target=self._timer_loop, daemon=True)
                self._timer_thread.start()

        self._current_progress_val = progress
        self._current_status_msg = status
        self.progress_bar.value = progress
        self.status_label.value = f"{status} ({progress}%)" if status else f"{progress}%"

        if self._progress_start_time is not None:
            elapsed = time.time() - self._progress_start_time
            self.etr_label.value = self._calculate_etr(elapsed, progress)
        else:
            self.etr_label.value = ""

        if error: self.progress_bar.bar_style = "danger"
        elif progress >= 100:
            self.progress_bar.bar_style = "success"
            self._progress_running = False
            if self._timer_thread is not None and self._timer_thread.is_alive():
                 self._timer_thread.join(timeout=1.5)
        else: self.progress_bar.bar_style = "info"

    def finish_progress(self, final_status: Optional[str] = None, delay_seconds: float = 1.5):
        """Voltooi en verberg de voortgangsbalk."""
        self._progress_running = False
        if self._timer_thread is not None and self._timer_thread.is_alive():
            self._timer_thread.join(timeout=1.5)

        if final_status:
            self.update_progress(100, status=final_status)
        elif self.progress_bar.value < 100 :
             self.update_progress(100, status=self._current_status_msg if self._current_status_msg else "Voltooid")

        time.sleep(delay_seconds)
        self.progress_container.layout.visibility = 'hidden'
        self.progress_bar.value = 0
        self.status_label.value = ""
        self.etr_label.value = ""
        self.progress_bar.bar_style = "info"
        self._progress_start_time = None
        self._current_progress_val = 0
        self._current_status_msg = ""

    def display_widget(self):
        """Toon de voortgangsbalk-container."""
        display(self.progress_container)