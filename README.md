
# EnergieApp Notebook Suite

## Introductie

De **EnergieApp Notebook Suite** is een set Jupyter‑notebooks (uitgerold als Voila‑webapps) plus SQL‑Server stored procedures om energie‑meetdata te analyseren, visualiseren en beheren. Gebruikers filteren op EAN, periode en kanaal, waarna de notebooks de juiste datasets ophalen, grafieken tonen of exports genereren. Zo levert de EnergieApp een centrale en gebruiksvriendelijke interface voor data‑analisten en beheerders.

---

## Projectstructuur

De repository is georganiseerd zoals hieronder weergegeven. Dit overzicht helpt nieuwe ontwikkelaars om snel de belangrijkste componenten te vinden.

```text
ENERGIEAPP/
├── 1.Notebooks/
│   ├── 000_Start_UI.ipynb
│   ├── 001_All_Types.ipynb
│   ├── 002_Data_export.ipynb
│   ├── 003_VMNE_Data_Export.ipynb
│   ├── 004_Facturupdate.ipynb
│   ├── 005_MV_Switch.ipynb
│   ├── 006_Vervanging_Tool.ipynb
│   ├── 007_Storage_Method.ipynb
│   ├── 201_launch_app.bat
│   ├── 202_launch_app.py
│   ├── caching.py
│   ├── common_imports.py
│   ├── custom.css
│   ├── dataset_utils.py
│   ├── db_connection.py
│   ├── db_utils.py
│   ├── frequency_utils.py
│   ├── Innax_logo.jpg
│   ├── mappings.py
│   ├── notebook_utils.py
│   ├── progress_bar_widget.py
│   ├── run_app_001.bat
│   └── time_utils.py
├── 2.Stored Procedures/
│   ├── usp_GetConnectionDataFull_OnlyLDN.sql
│   ├── usp_GetConnectionDataFull.sql
│   ├── usp_GetMinMaxPeriod_OnlyLDN.sql
│   └── usp_GetMinMaxPeriodForEAN.sql
├── docker-compose.yml
├── Dockerfile
├── launch_energieapp.bat
├── launch_energieapp.command
├── run_app.sh
└── environment.yml
```

---

## End‑to‑End Workflow

Onderstaand ASCII‑diagram toont de volledige workflow, conform het opgegeven sjabloon – van gebruikersinvoer tot draaiende Voila‑dashboards en database‑interactie.

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

(4) Run Voila‑dashboards ──────────┐
    │ run_app.sh maakt logs‑mapje
    │ start notebooks als webapps
└─> UI live op poorten 8866–8873 (hoofd‑UI: 8868)
```

---

## Bestandsanalyse

| Bestand | Functie | Interactie |
|---------|---------|------------|
| **run_app.sh** | Start alle Voila‑servers, schrijft logs en wacht tot de hoofd‑UI live is. | Wordt uitgevoerd als entry‑point in Docker. |
| **Dockerfile** | Bouwt het Docker‑image met Python‑omgeving, app‑code en Voila; stelt `run_app.sh` in als CMD. | Wordt gebruikt door *docker‑compose*. |
| **docker-compose.yml** | Orkestreert de container **energieapp**, mappt host‑poort 8868, mount logs/ en voert health‑check uit. | Aangeroepen door launch‑scripts. |
| **launch_energieapp.bat** | Windows‑launcher: controleert Docker, draait `docker compose up`, opent browser. | Gebruikt docker-compose.yml. |
| **launch_energieapp.command** | macOS/Linux‑variant van de launcher. | Zelfde flow als .bat. |
| **202_launch_app.py** | Start notebooks direct (zonder Docker) via Voila op vaste poorten. | Alternatief voor Docker‑start. |

---

## Notebook‑overzicht

| Notebook (poort) | Use‑Case | Kernlogica |
|------------------|----------|------------|
| 000_Start_UI (8868) | Hoofdinterface/dashboard | Menu met links naar overige notebooks. |
| 001_All_Types (8866) | Energiemonitor & analyse | Stored procs, resampling, caching, Plotly‑grafieken. |
| 002_Data_export (8867) | Zelfbedienings‑export | Filtert & exporteert data naar CSV/XLS, pivot. |
| 003_VMNE_Data_Export (8869) | VMNED‑specifieke export | Gelijkaardig aan 002 maar voor VMNED‑dataset. |
| 004_Facturupdate (8870) | Factor‑update tool | Berekent & werkt met batch‑updates de meetfactoren bij. |
| 005_MV_Switch (8871) | Middenspanning‑data switch | Haalt MV‑data op, voegt placeholders toe, exporteert. |
| 006_Vervanging_Tool (8872) | Vervanging meters/registers | Wizard voor vervangingen, transacties voor consistentie. |
| 007_Storage_Method (8873) | Opslagmethode beheer | Past storage‑interval & methode aan, repareert data. |

---

## Modules

| Module | Beschrijving | Toepassing |
|--------|--------------|-----------|
| db_connection.py | Maakt SQL‑Server‑verbinding (SQLAlchemy + pyodbc). | Gebruikt door alle notebooks. |
| common_imports.py | Laadt gedeelde imports en CSS‑styling. | Bovenaan elk notebook. |
| progress_bar_widget.py | Voortgangsbalk & ETA‑helpers. | Bij lange queries/updates. |
| frequency_utils.py | Interval‑helpers, automatische capping. | Analyse‑ en export‑notebooks. |
| db_utils.py | Query‑helpers & batch‑update utilities. | Factorupdate, Storage_Method, etc. |
| notebook_utils.py | Inputvalidatie & UI‑helpers. | Consistente foutafhandeling. |
| dataset_utils.py | Datatransformatie & export‑helpers. | Export‑ en analyse‑notebooks. |
| mappings.py | TypeID‑mappings & checks. | Analyse‑notebooks. |
| caching.py | Tijdelijke opslag van metadata/datasets (TTL). | Performance‑verbetering in alle notebooks. |

---

## Samenwerking

1. **Start‑up** – `run_app.sh` (of `202_launch_app.py`) lanceert per notebook een Voila‑service op een vaste poort.  
2. **Navigatie** – De gebruiker start op 000_Start_UI (8868) en kiest een tool.  
3. **Data‑laag** – Notebooks roepen stored procedures aan via `db_connection.py`.  
4. **Caching & performance** – `caching.py` slaat resultaten tijdelijk op; `frequency_utils.py` schaalt intervallen bij grote datasets.  
5. **Updates** – Tools die schrijven (004, 007) gebruiken transacties voor rollback bij fouten.  

De notebooks delen dezelfde util‑modules voor uniforme validatie, error‑handling en styling. Dankzij deze modulaire opzet kunnen nieuwe tools snel worden toegevoegd en wijzigingen centraal worden doorgevoerd.

---

## Controle & Validatie

Dit README is gesynchroniseerd met de huidige projectstructuur. Bestands‑ en mappenamen, poortnummers en modules zijn gecontroleerd op consistentie met de repo. Het workflow‑diagram volgt het aangeleverde sjabloon en weerspiegelt de daadwerkelijke applicatiestroom. Zorg bij code‑wijzigingen dat deze documentatie wordt bijgewerkt om afstemming tussen repo en README te behouden.
