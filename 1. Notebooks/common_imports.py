# common_imports.py
import os
from IPython.display import display, HTML, clear_output

# ── Injecteer optioneel custom notebook CSS ──
_css_path = os.path.join(os.getcwd(), 'custom.css')
if os.path.isfile(_css_path):
    with open(_css_path, 'r') as _f:
        _css = _f.read()
    display(HTML(f'<style>{_css}</style>'))
else:
    display(HTML(
        f'<p style="color:red;"><strong>custom.css niet gevonden:</strong> {_css_path}</p>'
    ))

# Standaard imports voor notebooks en utils
import io
import re
import time
import threading
import logging
import traceback
from datetime import datetime, date, timedelta
from pathlib import Path
from dateutil.relativedelta import relativedelta
from collections import deque
from typing import Tuple, Optional, Set, List, Dict, Callable

import pandas as pd
import numpy as np
import pytz

import sqlalchemy
from sqlalchemy import text
from sqlalchemy.pool import NullPool
import pyodbc
from sqlalchemy.exc import SQLAlchemyError
from pandas import read_sql_query
import urllib
from urllib import parse

import plotly.graph_objects as go
import plotly.io as pio
import ipywidgets as widgets
from ipywidgets import GridBox, Layout
from xlsxwriter.utility import xl_col_to_name
from ipyaggrid import Grid

# Database helper
from db_connection import get_engine

# UI helper functie direct in common_imports
def show_home_button(
    target_url: str = 'http://127.0.0.1:8868',
    button_width: str = '200px',
    button_height: str = '40px',
    button_style: str = 'info',
    icon: str = 'home'
) -> None:
    """
    Toont de 'Terug naar Startscherm'-knop in notebooks.
    Eenvoudig hergebruik in alle notebooks.
    """
    home_button = widgets.Button(
        description="Terug naar Startscherm",
        button_style=button_style,
        icon=icon,
        layout=widgets.Layout(width=button_width, height=button_height)
    )
    home_out = widgets.Output()

    def _on_click(_):
        with home_out:
            clear_output()
            display(HTML(f"""
            <script>
            window.open('{target_url}', '_self');
            </script>
            """))

    home_button.on_click(_on_click)
    display(widgets.HBox([home_button]), home_out)

# Exporteer alleen wat nodig is
__all__ = [
    # Standaard types en helpers
    'os', 'io', 're', 'time', 'threading', 'logging', 'traceback',
    'datetime', 'date', 'timedelta', 'relativedelta', 'deque', 'Path',
    'Tuple', 'Optional', 'Set', 'List', 'Dict', 'Callable',
    'pd', 'np', 'pytz', 'sqlalchemy', 'text', 'NullPool', 'pyodbc',
    'SQLAlchemyError', 'read_sql_query', 'urllib', 'parse',
    'go', 'pio', 'widgets', 'GridBox', 'Layout',
    'display', 'clear_output', 'HTML',
    'xl_col_to_name', 'Grid',
    # Database
    'get_engine',
    # UI
    'show_home_button',
]
