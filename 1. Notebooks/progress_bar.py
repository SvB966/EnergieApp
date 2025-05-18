# progress_bar.py

"""
Unified progress-bar module for Jupyter notebooks.

Ondersteunt:
 - ipywidgets-gebaseerde progress bars (klassiek IntProgress + label)
 - tqdm-gebaseerde progress bars (notebook én console)
"""

# --- Imports ---
# ipywidgets-ondersteuning
try:
    import ipywidgets as widgets
    from IPython.display import display, clear_output
    _WIDGETS_OK = True
except ImportError:
    _WIDGETS_OK = False

# tqdm-ondersteuning
try:
    from tqdm.notebook import tqdm as notebook_tqdm
except ImportError:
    notebook_tqdm = None
from tqdm import tqdm as standard_tqdm

# --- Widget-based progress bar --------------------------------------------
class WidgetProgress:
    """
    Een eenvoudige IntProgress + Label progress bar.
    Usage:
        pb = WidgetProgress(description='Bezig...', max=100)
        pb.show()
        pb.update(25, '25% klaar')
        pb.finish()
    """
    def __init__(self, min=0, max=100, description='Progress', orientation='horizontal'):
        if not _WIDGETS_OK:
            raise ImportError("ipywidgets niet beschikbaar")
        self.bar = widgets.IntProgress(
            value=0, min=min, max=max,
            description=description,
            bar_style='info',
            orientation=orientation
        )
        self.label = widgets.Label(value='')
        self.container = widgets.VBox([self.bar, self.label])
        self.container.layout.visibility = 'hidden'

    def show(self):
        """Toont de progress bar in de notebook."""
        self.container.layout.visibility = 'visible'
        display(self.container)

    def update(self, value, msg=''):
        """
        Update de waarde en het label.
        - value: nieuwe integer waarde
        - msg: optioneel tekstbericht
        """
        self.bar.value = value
        self.label.value = msg
        # stijl aanpassen op basis van voortgang
        if value >= self.bar.max:
            self.bar.bar_style = 'success'
        elif value >= (self.bar.max / 2):
            self.bar.bar_style = 'info'
        else:
            self.bar.bar_style = 'warning'

    def finish(self, msg='Klaar!'):
        """Zet progress op max en verbergt de bar na afronding."""
        self.update(self.bar.max, msg)
        # optioneel: verberg de container
        self.container.layout.visibility = 'hidden'


# --- tqdm-based progress bar ------------------------------------------------
def loop_with_tqdm(iterable, total=None, desc=None, unit=None, notebook=True):
    """
    Returnt een tqdm-iterator:
      - notebook=True: gebruik tqdm.notebook (grafisch in Jupyter)
      - notebook=False: gebruik gewone tqdm (console)
    Other args: total=int, desc=str, unit=str
    """
    if notebook and notebook_tqdm is not None:
        return notebook_tqdm(iterable, total=total, desc=desc, unit=unit)
    else:
        return standard_tqdm(iterable, total=total, desc=desc, unit=unit)


# --- Helper voor chunked Excel-export met voortgang --------------------------
def export_with_chunks(df, writer, chunk_size=1000, **tqdm_kwargs):
    """
    Schrijft een grote DataFrame in chunks naar een ExcelWriter,
    met een tqdm-progress bar.
    Usage in notebook:
        from progress_bar import export_with_chunks
        with pd.ExcelWriter('out.xlsx') as w:
            export_with_chunks(df, w, chunk_size=500, desc='Schrijven')
    """
    total = len(df)
    for start in loop_with_tqdm(range(0, total, chunk_size), total=(total//chunk_size)+1, **tqdm_kwargs):
        df.iloc[start:start+chunk_size]\
          .to_excel(writer,
                    index=False,
                    header=(start == 0),
                    startrow=start if start > 0 else 0)


# --- Eventuele custom shortenings / aliases ----------------------------------
# Voor backwards compatibility met bestaande notebooks:
# from tqdm import tqdm
tqdm = loop_with_tqdm
WidgetProgressBar = WidgetProgress
