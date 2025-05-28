# progress_bar_widget.py

import ipywidgets as widgets
import threading
import time

class ProgressBarWidget:
    """
    Herbruikbare, thread-safe voortgangsbalk voor Jupyter/IPyWidgets-applicaties.
    Toont status, percentage én resterende tijd (ETR).
    """

    def __init__(self, description="Voortgang:", width="220px", show_etr=True):
        self.progress_bar = widgets.IntProgress(
            value=0,
            min=0,
            max=100,
            step=1,
            description=description,
            bar_style='info',
            layout=widgets.Layout(width=width)
        )
        self.status_label = widgets.Label(value="", layout=widgets.Layout(width='auto', margin="0 0 0 10px"))
        self.etr_label = widgets.Label(value="", layout=widgets.Layout(width='auto', margin="0 0 0 10px"))
        children = [self.progress_bar, self.status_label]
        if show_etr:
            children.append(self.etr_label)
        self.container = widgets.HBox(
            children,
            layout=widgets.Layout(visibility='hidden', align_items='center', justify_content='center', margin="10px 0px")
        )
        self._start_time = None
        self._progress = 0
        self._running = False
        self._msg = ""
        self._show_etr = show_etr
        self._lock = threading.Lock()
        self._timer_thread = None

    def widget(self):
        """
        Retourneert de HBox-widget die toegevoegd kan worden aan je UI-lay-out.
        """
        return self.container

    def show(self, status="", initial_value=0):
        """
        Zet de voortgangsbalk zichtbaar en initialiseert deze met status en startwaarde.
        """
        with self._lock:
            self.progress_bar.value = initial_value
            self.status_label.value = status
            if self._show_etr:
                self.etr_label.value = ""
            self.progress_bar.bar_style = "info"
            self.container.layout.visibility = 'visible'
            self._start_time = time.time()
            self._progress = initial_value
            self._msg = status
            self._running = True
            # Start timer thread indien nodig
            if self._timer_thread is None or not self._timer_thread.is_alive():
                self._timer_thread = threading.Thread(target=self._update_etr, daemon=True)
                self._timer_thread.start()

    def update(self, progress, status="", error=False):
        """
        Werk de voortgangsbalk bij met percentage en status. Toon evt. fout of success.
        """
        with self._lock:
            self.progress_bar.value = int(progress)
            self.status_label.value = status if status else self._msg
            self._progress = progress
            self._msg = status if status else self._msg
            if error:
                self.progress_bar.bar_style = "danger"
                self._running = False
            elif progress >= 100:
                self.progress_bar.bar_style = "success"
                self._running = False
            else:
                self.progress_bar.bar_style = "info"
            # ETR wordt automatisch bijgewerkt door de thread

    def finish(self):
        """
        Sluit de voortgangsbalk netjes af.
        """
        time.sleep(1)
        with self._lock:
            self.container.layout.visibility = 'hidden'
            self.progress_bar.value = 0
            self.status_label.value = ""
            if self._show_etr:
                self.etr_label.value = ""
            self.progress_bar.bar_style = "info"
            self._start_time = None
            self._progress = 0
            self._msg = ""
            self._running = False

    def _update_etr(self):
        """
        Thread-functie voor het tonen van resterende tijd (ETR).
        """
        while True:
            time.sleep(1)
            with self._lock:
                if not self._running or not self._show_etr or self._start_time is None:
                    if self._show_etr:
                        self.etr_label.value = ""
                    break
                if 0 < self._progress < 100:
                    elapsed = time.time() - self._start_time
                    fraction_done = self._progress / 100.0
                    if fraction_done > 0:
                        estimated_total = elapsed / fraction_done
                        remaining = max(0, estimated_total - elapsed)
                        m, s = divmod(remaining, 60)
                        h, m = divmod(m, 60)
                        if h >= 1:
                            etr_str = f"Resterende tijd: {int(h)}u {int(m)}m {int(s)}s"
                        else:
                            etr_str = f"Resterende tijd: {int(m)}m {int(s)}s"
                        self.etr_label.value = etr_str
                    else:
                        self.etr_label.value = ""
                else:
                    self.etr_label.value = ""

# Gebruik:
# from progress_bar_widget import ProgressBarWidget
# pb = ProgressBarWidget(description="Voortgang:", width="250px")
# pb.show("Starten...", 0)
# pb.update(30, "30% klaar")
# pb.finish()
