# frequency_utils.py

from common_imports import pd, np, datetime, timedelta, pytz

# Centrale frequentie mapping
FREQS = {
    '5T':  {'label': 'Elke 5 minuten',  'minutes': 5,    'seconds': 300,      'pandas': '5min'},
    '15T': {'label': 'Elke 15 minuten', 'minutes': 15,   'seconds': 900,      'pandas': '15min'},
    'H':   {'label': 'Per uur',          'minutes': 60,   'seconds': 3600,     'pandas': 'h'},
    'D':   {'label': 'Dagelijks',        'minutes': 1440, 'seconds': 86400,    'pandas': 'D'},   # 'D' blijft geldig
    'W':   {'label': 'Wekelijks',        'minutes': 10080,'seconds': 604800,   'pandas': 'W'},   # 'W' blijft geldig
    'ME':  {'label': 'Maandelijks',      'minutes': 43200,'seconds': 2592000,  'pandas': 'ME'},
    'Y':   {'label': 'Jaarlijks',        'minutes': 525600,'seconds': 31536000,'pandas': 'YE'},
    'auto':{'label': 'Automatisch',      'minutes': -1,   'seconds': -1,       'pandas': None},
}

def get_freq_minutes(freq_key):
    return FREQS.get(freq_key, FREQS['5T'])['minutes']

def get_freq_seconds(freq_key):
    return FREQS.get(freq_key, FREQS['5T'])['seconds']

def get_pandas_freq(freq_key):
    return FREQS.get(freq_key, FREQS['5T'])['pandas']

def check_max_rows(start_dt, end_dt, freq_key, max_rows=8000):
    interval = get_freq_seconds(freq_key)
    duration = (end_dt - start_dt).total_seconds()
    nrows = int(duration // interval) + 1 if interval > 0 else 1
    return nrows <= max_rows, nrows

def round_datetime_to_freq(dt, freq_key, is_start, tz='Europe/Amsterdam'):
    tz_obj = pytz.timezone(tz)
    if dt.tzinfo is None:
        dt_ams = tz_obj.localize(dt)
    else:
        dt_ams = dt.astimezone(tz_obj)

    # -- Frequentie rounding logic --
    if freq_key == '5T':
        minute_rounded = (dt_ams.minute // 5) * 5
        return dt_ams.replace(minute=minute_rounded, second=0, microsecond=0)
    elif freq_key == '15T':
        minute_rounded = (dt_ams.minute // 15) * 15
        return dt_ams.replace(minute=minute_rounded, second=0, microsecond=0)
    elif freq_key == 'H':
        return dt_ams.replace(minute=0, second=0, microsecond=0)
    elif freq_key == 'D':
        base_dt = dt_ams.replace(hour=0, minute=0, second=0, microsecond=0)
        return base_dt if is_start else base_dt + timedelta(days=1)
    elif freq_key == 'W':
        start_of_week = (dt_ams - timedelta(days=dt_ams.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
        return start_of_week if is_start else start_of_week + timedelta(weeks=1)
    elif freq_key == 'ME':
        start_of_month = dt_ams.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if not is_start:
            next_month = start_of_month.month + 1
            year = start_of_month.year + (1 if next_month > 12 else 0)
            month = 1 if next_month > 12 else next_month
            return start_of_month.replace(year=year, month=month)
        return start_of_month
    elif freq_key == 'Y':
        start_of_year = dt_ams.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        return start_of_year if is_start else start_of_year.replace(year=start_of_year.year + 1)
    return dt_ams

def detect_auto_frequency(datetime_index):
    if len(datetime_index) < 2:
        return 'H'
    diffs = pd.Series(datetime_index).diff().dropna().dt.total_seconds().astype(int)
    mode_diff = diffs.mode()[0] if not diffs.empty else 3600
    for key, freq in FREQS.items():
        if freq['seconds'] > 0 and abs(freq['seconds'] - mode_diff) < 10:
            return key
    return 'H'

def resample_dataframe(df, freq_key, method='sum'):
    pandas_freq = get_pandas_freq(freq_key)
    if pandas_freq is None:
        return df
    # Sum by default, of course kun je hier 'mean', 'first', etc. doorgeven
    return getattr(df.resample(pandas_freq), method)()
