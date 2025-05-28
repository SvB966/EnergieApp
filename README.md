````markdown
# EnergieApp Notebook Suite

## Introductie

De **EnergieApp Notebook Suite** is een verzameling Jupyter-notebooks (uitgerold als Voila-webapps) én SQL-Server stored procedures om energie-meetdata te analyseren, visualiseren en beheren. Gebruikers filteren op EAN, periode en kanaal; de notebooks halen vervolgens de juiste datasets op, tonen interactieve grafieken of genereren exports. Zo biedt de EnergieApp een centrale en gebruiksvriendelijke interface voor data-analisten en beheerders.

---

## Projectstructuur

```text
EnergieApp/
├── 1. Notebooks/
│   ├── 000_Start_UI.ipynb
│   ├── 001_All_Types.ipynb
│   ├── 002_Data_export.ipynb
│   ├── 003_VMNED_Data_Export.ipynb
│   ├── 004_Factorupdate.ipynb
│   ├── 005_MV_Switch.ipynb
│   ├── 006_Vervanging_Tool.ipynb
│   ├── 007_Storage_Method.ipynb
│   ├── 201_launch_app.bat
│   ├── 202_launch_app.py
│   ├── Innax_logo.jpg
│   ├── caching.py
│   ├── common_imports.py
│   ├── custom.css
│   ├── dataset_utils.py
│   ├── db_connection.py
│   ├── db_utils.py
│   ├── environment.yml
│   ├── frequency_utils.py
│   ├── mappings.py
│   ├── progress_bar_widget.py
│   ├── run_app_001.bat
│   ├── time_utils.py
│   ├── verify_env_deps.py
│   └── __pycache__/
├── 2. Stored Procedures/
│   ├── usp_GetConnectionDataFull.sql
│   ├── usp_GetConnectionDataFull_OnlyLDNODN.sql
│   ├── usp_GetMinMaxPeriodForEAN.sql
│   └── usp_GetMinMaxPeriod_OnlyLDNODN.sql
├── docker-compose.yml
├── Dockerfile
├── launch_energieapp.bat
├── launch_energieapp.command
└── run_app.sh
````

---

## End-to-End Workflow

```text
(1) Gebruiker kiest EAN & filters ─┐
    │ time_utils & frequency_utils valideren invoer
    │ SQL ① usp_GetMinMaxPeriodForEAN
┌─────────────────────────────────┐ ├────────> [MinUTC, MaxUTC]

(2) Gebruiker klikt “Zoeken” ───────┐
    │ db_utils → db_connection → SQL ② usp_GetConnectionDataFull
    │ caching slaat metadata tijdelijk op
┌─────────────────────────────────┐ ├────────> [ConnectionData, TypeIDs]

(3) dataset_utils bouwt dataset ──┐
    │ db_utils → SQL ③ usp_GetRawData
    │ mappings groepeert kolommen
    │ frequency_utils past resampling toe
    │ progress_bar_widget toont voortgang
┌─────────────────────────────────┐ ├────────> [DataFrame / Grafiek]

(4) Run Voila-dashboards ──────────┐
    │ verify_env_deps.py checkt deps
    │ run_app.sh maakt logs-mapje
    │ start notebooks als webapps (poorten 8866–8873)
└─> UI live op poort 8868 (000_Start_UI)
```

---

## Bestandsanalyse

| Bestand                        | Functie                                                                                        | Interactie                                  |
| ------------------------------ | ---------------------------------------------------------------------------------------------- | ------------------------------------------- |
| **run\_app.sh**                | Start alle Voila-servers, schrijft logs en wacht tot de hoofd-UI live is.                      | Entry-point in Docker/CMD in Dockerfile.    |
| **Dockerfile**                 | Bouwt het Docker-image met Python-omgeving, app-code en Voila; zet `run_app.sh` als CMD.       | Gebruikt door *docker-compose*.             |
| **docker-compose.yml**         | Orkestreert de container **energieapp**, mappt host-poort 8868, mount *logs/* en health-check. | Aangeroepen door launcher-scripts.          |
| **launch\_energieapp.bat**     | Windows-launcher: controleert Docker, draait `docker compose up`, opent browser.               | Gebruikt *docker-compose.yml*.              |
| **launch\_energieapp.command** | macOS/Linux-launcher: zelfde flow als .bat.                                                    |                                             |
| **202\_launch\_app.py**        | Start notebooks lokaal (zonder Docker) via Voila op vaste poorten.                             | Alternatief voor Docker-flow.               |
| **environment.yml**            | Definitie van Conda-omgeving voor lokale setup en dependency management.                       | Gebruikt door `verify_env_deps.py` en devs. |
| **verify\_env\_deps.py**       | Controleert of de lokaal geïnstalleerde Python-packages overeenkomen met `environment.yml`.    | Draait vóór opstarten notebooks.            |

---

## Notebook-overzicht

| Notebook (poort)                    | Use-Case                    | Kernlogica                                               |
| ----------------------------------- | --------------------------- | -------------------------------------------------------- |
| **000\_Start\_UI** (8868)           | Hoofdinterface/dashboard    | Menu met links naar overige notebooks.                   |
| **001\_All\_Types** (8866)          | Energiemonitor & analyse    | Stored procs, resampling, caching, Plotly-grafieken.     |
| **002\_Data\_export** (8867)        | Zelfbedienings-export       | Filteren & exporteren naar CSV/XLS, pivot-tabellen.      |
| **003\_VMNED\_Data\_Export** (8869) | VMNED-specifieke export     | Zelfde flow als 002 maar op VMNED-dataset.               |
| **004\_Factorupdate** (8870)        | Factor-update tool          | Batch-updates van meetfactoren met transaction-rollback. |
| **005\_MV\_Switch** (8871)          | Middenspanning-data switch  | Ophalen MV-data, toevoegen placeholders, exporteren.     |
| **006\_Vervanging\_Tool** (8872)    | Vervanging meters/registers | Wizard-flow voor vervanging, consistente transacties.    |
| **007\_Storage\_Method** (8873)     | Opslagmethode beheer        | Aanpassen storage-interval/methode, reparatie van data.  |

---

## Modules

| Module                       | Beschrijving                                                              | Toepassing                                 |
| ---------------------------- | ------------------------------------------------------------------------- | ------------------------------------------ |
| **db\_connection.py**        | SQL-Server-verbinding (SQLAlchemy + pyodbc).                              | Gebruikt door alle notebooks.              |
| **common\_imports.py**       | Laadt gedeelde imports en CSS-styling.                                    | Bovenaan elk notebook.                     |
| **progress\_bar\_widget.py** | Voortgangsbalk & ETA-helpers.                                             | Bij lange queries/updates.                 |
| **frequency\_utils.py**      | Interval-helpers, automatische capping voor grote datumbereiken.          | In analyse- en export-notebooks.           |
| **db\_utils.py**             | Query-helpers & batch-update utilities.                                   | Factorupdate, Storage\_Method, etc.        |
| **notebook\_utils.py**       | Inputvalidatie & UI-helpers.                                              | Foutafhandeling en consistentie.           |
| **dataset\_utils.py**        | Datatransformatie & export-helpers.                                       | Export- en analyse-workflows.              |
| **mappings.py**              | TypeID-mappings & checks.                                                 | Analyse-notebooks.                         |
| **caching.py**               | Tijdelijke opslag van metadata/datasets (TTL).                            | Performance-verbetering in alle notebooks. |
| **time\_utils.py**           | Tijdvalidatie, conversies en UTC-capping.                                 | Start-UI en filtering.                     |
| **verify\_env\_deps.py**     | Controleert lokale Python-dependencies aan de hand van `environment.yml`. | Draait vóór notebooks-activatie.           |

---

## Samenwerking

1. **Start-up** – `run_app.sh` (of `202_launch_app.py`) lanceert per notebook een Voila-service op vooraf bepaalde poorten.
2. **Validatie** – `verify_env_deps.py` checkt dat alle Conda-dependencies aanwezig zijn.
3. **Navigatie** – De gebruiker start op 000\_Start\_UI (poort 8868) en kiest een tool.
4. **Data-laag** – Notebooks roepen stored procedures aan via `db_connection.py`.
5. **Caching & performance** – `caching.py` slaat resultaten tijdelijk op; `frequency_utils.py` past interval-capping toe.
6. **Schrijven** – Tools die data muteren (004, 007) gebruiken transacties met rollback-mechanisme.

De notebooks delen dezelfde util-modules voor uniforme validatie, foutafhandeling en styling. Dankzij deze modulaire opzet kunnen nieuwe tools snel worden toegevoegd en wijzigingen centraal worden doorgevoerd.

---
