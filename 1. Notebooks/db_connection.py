from __future__ import annotations
import os
import sys
import urllib.parse
import logging
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool

# --- Sanity-check voor Interpreter & dotenv-locatie ---
try:
    import dotenv
    print("▶ Python executable:", sys.executable)
    print("▶ dotenv module:", dotenv.__file__)
except ImportError:
    print("⚠️ WARNING: python-dotenv NIET gevonden in dit environment!")

# --- Laad .env indien aanwezig ---
try:
    from dotenv import load_dotenv
    load_dotenv()  # Negeert stil als .env ontbreekt
except ImportError:
    logging.getLogger(__name__).warning(
        "python-dotenv niet beschikbaar; .env wordt niet ingeladen."
    )

DEFAULT_HOST = "inn-vee-sql12"
DEFAULT_DB   = "EDS2"

def _build_conn_str() -> str:
    host     = os.getenv("DB_HOST", DEFAULT_HOST)
    database = os.getenv("DB_DATABASE", DEFAULT_DB)
    user     = os.getenv("DB_USER")
    pwd      = os.getenv("DB_PASSWORD")

    if not host or not database:
        raise EnvironmentError(
            "Zet minimaal DB_HOST en DB_DATABASE als env-vars of in .env"
        )

    if user and pwd:
        auth = f"UID={user};PWD={pwd};"
    else:
        auth = "Trusted_Connection=yes;"

    return (
        "DRIVER={ODBC Driver 17 for SQL Server};"
        f"SERVER={host};DATABASE={database};{auth}"
        "Encrypt=yes;TrustServerCertificate=yes;"
    )

def get_engine(*, autocommit: bool = False):
    """
    Retourneert een SQLAlchemy-engine.
    autocommit=True ⇒ isolation_level='AUTOCOMMIT'
    """
    conn_str = _build_conn_str()
    conn = urllib.parse.quote_plus(conn_str)

    kwargs = {
        "poolclass": NullPool,
        "connect_args": {"fast_executemany": True}
    }
    if autocommit:
        kwargs["isolation_level"] = "AUTOCOMMIT"

    engine = create_engine(f"mssql+pyodbc:///?odbc_connect={conn}", **kwargs)
    logging.getLogger(__name__).info(
        "SQL-engine aangemaakt voor %s/%s",
        os.getenv("DB_HOST", DEFAULT_HOST),
        os.getenv("DB_DATABASE", DEFAULT_DB)
    )
    return engine

# --- Test run (optioneel) ---
if __name__ == "__main__":
    # Simpele connectie-test
    try:
        eng = get_engine()
        with eng.connect() as conn:
            print("✅ Verbinding succesvol.")
    except Exception as e:
        print("❌ Verbindingsfout:", e)
