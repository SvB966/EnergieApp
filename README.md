
# EnergieApp Notebook Suite

## Introductie

De **EnergieApp Notebook Suite** is een verzameling Jupyter-notebooks (uitgerold als Voila-webapps) en SQL Server stored procedures om energie-meetdata te analyseren, visualiseren en beheren. Gebruikers filteren op EAN, periode en kanaal, waarna de notebooks datasets ophalen, grafieken tonen of exports genereren. Zo biedt de EnergieApp een centrale en gebruiksvriendelijke interface voor data-analisten en beheerders.

---

## Projectstructuur

```

EnergieApp/
├── 1. Notebooks/
│   ├── 000\_Start\_UI.ipynb
│   ├── 001\_All\_Types.ipynb
│   ├── 002\_Data\_export.ipynb
│   ├── 003\_VMNED\_Data\_Export.ipynb
│   ├── 004\_Factorupdate.ipynb
│   ├── 005\_MV\_Switch.ipynb
│   ├── 006\_Vervanging\_Tool.ipynb
│   ├── 007\_Storage\_Method.ipynb
│   ├── 201\_launch\_app.bat
│   ├── 202\_launch\_app.py
│   ├── Innax\_logo.jpg
│   ├── caching.py
│   ├── common\_imports.py
│   ├── custom.css
│   ├── dataset\_utils.py
│   ├── db\_connection.py
│   ├── db\_utils.py
│   ├── environment.yml
│   ├── frequency\_utils.py
│   ├── mappings.py
│   ├── progress\_bar\_widget.py
│   ├── run\_app\_001.bat
│   ├── time\_utils.py
│   ├── verify\_env\_deps.py
│   └── **pycache**/
├── 2. Stored Procedures/
│   ├── usp\_GetConnectionDataFull.sql
│   ├── usp\_GetConnectionDataFull\_OnlyLDNODN.sql
│   ├── usp\_GetMinMaxPeriodForEAN.sql
│   └── usp\_GetMinMaxPeriod\_OnlyLDNODN.sql

```

---

## Bestandsanalyse

| Bestand                   | Functie                                                      |
|---------------------------|--------------------------------------------------------------|
| 000_Start_UI.ipynb        | Hoofd-dashboard, toegang tot alle notebooks                  |
| 001_All_Types.ipynb       | Energiemonitor, analyse, Plotly-visualisatie                |
| 002_Data_export.ipynb     | Zelfbedienings-export (CSV/XLS, pivot)                       |
| 003_VMNED_Data_Export.ipynb | VMNED-specifieke export                                  |
| 004_Factorupdate.ipynb    | Tool voor batch-factorupdates                                |
| 005_MV_Switch.ipynb       | Middenspanning data switch, export                          |
| 006_Vervanging_Tool.ipynb | Wizard voor meter/registervervanging                         |
| 007_Storage_Method.ipynb  | Opslagmethode beheer, datacorrectie                         |
| 201_launch_app.bat        | Windows launcher voor notebooks                              |
| 202_launch_app.py         | Start notebooks direct via Voila op vaste poorten           |
| Innax_logo.jpg            | Logo voor branding                                           |
| caching.py                | (TTL) caching van metadata en datasets                      |
| common_imports.py         | Gedeelde imports, CSS-styling                               |
| custom.css                | Styling voor UI                                              |
| dataset_utils.py          | Helpers voor datatransformatie en export                    |
| db_connection.py          | SQL Server connectie (SQLAlchemy + pyodbc)                  |
| db_utils.py               | Query-helpers & batch update utilities                      |
| environment.yml           | Conda/Python environment specification                      |
| frequency_utils.py        | Interval en resampling utilities                            |
| mappings.py               | TypeID mappings, check-logica                               |
| progress_bar_widget.py    | Voortgangsbalk & ETA-widget                                 |
| run_app_001.bat           | Batch script voor run-app                                   |
| time_utils.py             | Tijdvalidatie en helpers                                    |
| verify_env_deps.py        | Controle op omgeving en dependencies                        |
| __pycache__/              | (Wordt aanbevolen te .gitignore-en, bevat bytecode caches)  |

---

## Stored Procedures

| Script                                      | Doel                                 |
|----------------------------------------------|--------------------------------------|
| usp_GetConnectionDataFull.sql                | Haalt volledige connectiedata op     |
| usp_GetConnectionDataFull_OnlyLDNODN.sql     | Connectiedata subset                 |
| usp_GetMinMaxPeriodForEAN.sql                | Haalt min/max periode voor EAN op    |
| usp_GetMinMaxPeriod_OnlyLDNODN.sql           | Min/max periode subset               |

---

## Workflow (Hoog Over)

1. **Start-up:**  
   - Via `202_launch_app.py` of `201_launch_app.bat` (of als Docker-stack met eigen compose).
2. **Gebruiker:**  
   - Start op `000_Start_UI.ipynb` → kiest tool → voert filters in.
3. **Datalaag:**  
   - Via notebooks en helpers (db_utils, db_connection) worden stored procs aangesproken.
4. **Transform & Visualisatie:**  
   - Helpers (`dataset_utils`, `mappings`, `frequency_utils`) bouwen en tonen de output.
5. **Export & Monitoring:**  
   - `progress_bar_widget`, caching en environment checks ondersteunen stabiliteit en snelheid.

---

## Omgevingsbeheer & Git-best-practices

- Gebruik altijd `environment.yml` voor een consistente Python/Conda-omgeving.
- Voeg `__pycache__/` en `*.pyc` toe aan je `.gitignore`:
```

**pycache**/
\*.pyc

```
- Controleer de `README.md` bij elke (structurele) update van de repo.

---

## Meer informatie

- **Energie_app branch:** [link](https://github.com/SvB966/EnergieApp/tree/Energie_app)
- **Main branch:** [link](https://github.com/SvB966/EnergieApp/tree/main)

---

```

---

