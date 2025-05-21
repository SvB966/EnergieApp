import time
from ipywidgets import IntProgress, Label, HBox, Layout

class ProgressBarWidget:
    """
    Self-contained progress bar widget for Jupyter notebooks.
    Provides methods to show, update, and hide the progress bar,
    including ETA calculation and error/success coloring.
    """
    def __init__(self, width='220px'):
        self.etr_label = Label(value="", layout=Layout(width="auto", margin="0 0 0 10px"))
        self.progress_bar = IntProgress(
            value=0,
            min=0,
            max=100,
            step=1,
            description='Voortgang:',
            bar_style='info',
            layout=Layout(width=width)
        )
        self.status_label = Label(value="", layout=Layout(width="auto", margin="0 0 0 10px"))
        self.container = HBox(
            [self.progress_bar, self.status_label, self.etr_label],
            layout=Layout(visibility='hidden', align_items='center', justify_content='center', margin="10px 0px")
        )
        self._start_time = None

    def show(self, reset=True, status="Start..."):
        self.container.layout.visibility = 'visible'
        if reset:
            self._start_time = None
            self.update(0, status=status)

    def update(self, progress: int, status: str = "", error: bool = False):
        if self._start_time is None:
            self._start_time = time.time()
        elapsed = time.time() - self._start_time
        self.progress_bar.value = progress
        self.status_label.value = f"{status} ({progress}%)"

        # ETA
        if 0 < progress < 100:
            fraction_done = progress / 100.0
            estimated_total = elapsed / fraction_done
            remaining = estimated_total - elapsed
            m, s = divmod(remaining, 60)
            h, m = divmod(m, 60)
            if h >= 1:
                etr_str = f"Resterende tijd: {int(h)}u {int(m)}m {int(s)}s"
            else:
                etr_str = f"Resterende tijd: {int(m)}m {int(s)}s"
            self.etr_label.value = etr_str
        else:
            self.etr_label.value = ""

        # Bar style
        if error:
            self.progress_bar.bar_style = "danger"
        elif progress >= 100:
            self.progress_bar.bar_style = "success"
        else:
            self.progress_bar.bar_style = "info"

    def finish(self, delay=1.0):
        time.sleep(delay)
        self.container.layout.visibility = 'hidden'
        self.progress_bar.value = 0
        self.status_label.value = ""
        self.etr_label.value = ""
        self.progress_bar.bar_style = "info"
        self._start_time = None

    def widget(self):
        """Return the HBox widget for display."""
        return self.container
