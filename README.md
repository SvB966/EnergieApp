# EnergieApp Notebook Suite

[![Python Version](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/release/python-311/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Status](https://img.shields.io/badge/status-development-green.svg)]()

## Korte Beschrijving

De EnergieApp Notebook Suite is een verzameling van Python Jupyter notebooks en SQL stored procedures, ontworpen voor het analyseren, visualiseren, en beheren van meetdata, zoals energieverbruik en -productie. [cite: 1, 122] Het stelt gebruikers in staat om via een intuïtieve UI filters in te stellen, data op te vragen, factoren bij te werken, en opslagmethodes te configureren. [cite: 3, 49, 75, 100, 124]

## Inhoudsopgave

- [Overzicht van Notebooks](#overzicht-van-notebooks)
- [Installatie & Vereisten](#installatie--vereisten)
- [Snelstart](#snelstart)
- [Configuratie-details](#configuratie-details)
- [Best Practices & Aandachtspunten](#best-practices--aandachtspunten)
- [Contributie-richtlijnen](#contributie-richtlijnen)
- [Licentie](#licentie)
- [Contact / Auteurs](#contact--auteurs)

## Overzicht van Notebooks

Deze suite bevat verschillende notebooks, elk met een specifieke focus:

### `001_All_Types.ipynb` (Energiemonitor & Data Analyse)

* **Doel**: Algemene analyse en visualisatie van diverse meetdata. [cite: 122, 124]
* **Kernfunctionaliteiten**:
    * Opvragen van data via `usp_GetMinMaxPeriodForEAN` en `usp_GetConnectionDataFull` stored procedures. [cite: 127, 136]
    * Filteren op EAN/ID, datumbereik, frequentie, en TypeID-groepen. [cite: 153]
    * Dataverwerking met Pandas voor resampling en aggregatie. [cite: 155]
    * Interactieve visualisaties (lijn, staaf, heatmap) met Plotly. [cite: 147, 156]
    * Caching van database-resultaten (TTLCache) om performance te verbeteren. [cite: 148]
    * Raw-data modus (`@IntervalMinutes = -1`) voor kwaliteitscontroles. [cite: 126]

### `002_Data_export.ipynb` (Data Export Functionaliteit)

* **Doel**: Gedetailleerde data-export mogelijkheden, inclusief statuskolommen en geavanceerde filtering. [cite: 17]
* **Kernfunctionaliteiten**:
    * Gebruikt `usp_GetMinMaxPeriodForEAN` en `usp_GetConnectionDataFull` voor data-extractie. [cite: 6, 17]
    * Optie om statuskolommen (`(status)`) mee te nemen in de export. [cite: 19, 23]
    * Data aggregatie op verschillende intervallen, inclusief een raw-modus (`@IntervalMinutes = -1`) en maand-aggregatie. [cite: 5, 19, 21]
    * Consumptiedata wordt als `FLOAT` behandeld om precisie te waarborgen. [cite: 20, 142]
    * Dynamische pivot-tabellen waarbij per tijdstempel één rij wordt gecreëerd. [cite: 2, 27, 123]

### `004_Factorupdate.ipynb` (Factor Update Tool)

* **Doel**: (Her)berekenen en bijwerken van meetfactoren voor registers, gekoppeld aan een `RegistratorID`. [cite: 46, 47]
* **Kernfunctionaliteiten**:
    * Ophalen van registers op basis van `RegistratorID`. [cite: 49, 57]
    * Interactief aanpassen van invoerwaarden (spanningen, stromen, netverlies, multiplier, datums). [cite: 49]
    * Berekenen van de "New Factor" via de SQL scalar-functie `CalculateFactorWithoutRegister`. [cite: 48, 49, 53]
    * Grafische (Plotly) en tabellarische vergelijking van de impact van factorwijzigingen. [cite: 49, 60, 61]
    * Bulk-update van factoren via `TBL_Register_Factor_Update` en de stored procedure `SP_EDS2_Register_Factor_Update`. [cite: 48, 54]
    * Transactiemanagement voor consistente updates. [cite: 56, 66]

### `005_MV_Switch.ipynb` (Middenspanning Data Switch)

* **Doel**: Faciliteren van het ophalen en exporteren van middenspanning (MV) datasets op basis van EAN en `RegistratorID`. [cite: 73, 74, 75]
* **Kernfunctionaliteiten**:
    * Invoeren van EAN om gerelateerde `RegistratorID`s op te halen (via `usp_GetRegistratorListForEAN` of vergelijkbaar). [cite: 76, 80]
    * Selectie van een specifieke `RegistratorID` uit een dropdown. [cite: 77, 81]
    * Ophalen van MV-dataset (via `usp_GetMVDataForSwitch` of vergelijkbaar). [cite: 86]
    * Optioneel toevoegen van een standaardbericht voor ontbrekende waarden. [cite: 77, 81, 82]
    * Exporteren van de dataset naar Excel (`.xlsx`) met opgemaakte headers en een metadata-sheet. [cite: 78, 84, 90, 91]

### `007_Storage_Method.ipynb` (Opslagmethode Beheer)

* **Doel**: Configureren van opslag- en collectie-instellingen (zoals `StorageMethod` en `CollectInterval`) per register en het repareren van data. [cite: 99, 100]
* **Kernfunctionaliteiten**:
    * Ophalen van `RegisterID`s op basis van een `RegistratorID` (via `usp_GetRegistratorRegisters`). [cite: 101, 104, 108]
    * Selectie van `StorageMethod` (e.g., "Interval", "Raw") en `CollectInterval` (5 of 15 minuten). [cite: 102, 105, 106]
    * Metadata-updates op `TBL_Register` voor de geselecteerde registers. [cite: 103, 109]
    * Uitvoeren van data-repairlogica via de stored procedure `usp_AdjustDataInterval` om timestamps aan te passen aan het nieuwe interval. [cite: 103, 110]
    * Batchverwerking voor updates voor transactionele veiligheid. [cite: 110, 117]

## Installatie & Vereisten

### Software Vereisten

* **Python**: Versie 3.11.11 (zie `environment.yml`).
* **Package Manager**: Conda wordt aanbevolen voor het beheren van de omgeving.
* **Afhankelijkheden**: Zie het `environment.yml` bestand voor een volledige lijst. Belangrijke packages zijn o.a. `pandas`, `numpy`, `sqlalchemy`, `pyodbc`, `plotly`, `ipywidgets`, `voila`, `xlsxwriter`, `python-dotenv`.

### Database Vereisten

* **SQL Server**: De applicatie is ontworpen om te werken met een Microsoft SQL Server database.
* **Stored Procedures**: De volgende stored procedures dienen in de database aanwezig te zijn:
    * `usp_GetMinMaxPeriodForEAN` [cite: 6, 127]
    * `usp_GetConnectionDataFull` [cite: 17, 136]
    * `usp_GetRegistratorListForEAN` (of equivalent, genoemd in `005_MV_Switch.docx`) [cite: 80]
    * `usp_GetMVDataForSwitch` (fictieve naam, genoemd in `005_MV_Switch.docx`) [cite: 86]
    * `usp_GetRegistratorRegisters` (genoemd in `007_Storage_Method.docx`) [cite: 104]
    * `usp_AdjustDataInterval` (genoemd in `007_Storage_Method.docx`) [cite: 110]
    * Scalar function: `CalculateFactorWithoutRegister` (genoemd in `004_Factorupdate.docx`) [cite: 48]
    * Stored procedure: `SP_EDS2_Register_Factor_Update` (genoemd in `004_Factorupdate.docx`) [cite: 48]
* **Omgevingsvariabelen**: Configureer een `.env` bestand in de root van het project met de volgende variabelen voor databaseconnectiviteit (zie `db_connection.py` [cite: 33, 149]):
    * `DB_HOST`: Hostnaam of IP-adres van de SQL Server.
    * `DB_DATABASE`: Naam van de database.
    * `DB_USER` (optioneel): Gebruikersnaam voor SQL Server authenticatie.
    * `DB_PASSWORD` (optioneel): Wachtwoord voor SQL Server authenticatie.
    * Indien `DB_USER` en `DB_PASSWORD` niet worden opgegeven, wordt Windows Trusted Connection gebruikt.
    * SSL-encryptie is standaard ingeschakeld (`Encrypt=yes;TrustServerCertificate=yes;`). [cite: 33, 149]

### Installatiestappen

1.  **Clone de repository**:
    ```bash
    git clone [https://github.com/jouwgebruikersnaam/EnergieApp.git](https://github.com/jouwgebruikersnaam/EnergieApp.git)
    cd EnergieApp
    ```
2.  **Maak de Conda omgeving aan**:
    ```bash
    conda env create -f "3. Configuration & Build/environment.yml"
    ```
3.  **Activeer de Conda omgeving**:
    ```bash
    conda activate energymonitor_env
    ```
4.  **Configureer `.env` bestand**:
    Maak een bestand genaamd `.env` in de root van het project en voeg de database verbindingsdetails toe zoals hierboven beschreven. Bijvoorbeeld:
    ```env
    DB_HOST=jouw_server_naam
    DB_DATABASE=jouw_database_naam
    # DB_USER=jouw_gebruikersnaam (optioneel)
    # DB_PASSWORD=jouw_wachtwoord (optioneel)
    ```
5.  **Installeer de Stored Procedures**: Zorg dat alle benodigde SQL stored procedures en functies (zie `2. Stored Procedures/` map) in de doel-database zijn geïnstalleerd.

## Snelstart

1.  Zorg dat alle installatiestappen zijn voltooid.
2.  Start de applicatie launcher:
    ```bash
    python "1. Notebooks/202_launch_app.py"
    ```
    Dit script start meerdere Voila-servers voor de verschillende notebooks.
3.  Open de hoofdinterface in je browser, deze wordt automatisch geopend of navigeer naar `http://127.0.0.1:8868` (of de poort gespecificeerd in `202_launch_app.py`).
4.  Vanuit de hoofdinterface (`000_Start_UI.ipynb`) kun je navigeren naar de verschillende tools/notebooks.

    Voorbeeld: Om direct een specifieke notebook (bijv. `001_All_Types.ipynb`) te draaien met Voila:
    ```bash
    voila "1. Notebooks/001_All_Types.ipynb" --port=8866
    ```

## Configuratie-details

### Stored Procedures

De applicatie is sterk afhankelijk van de correcte werking van de meegeleverde SQL stored procedures. [cite: 2, 123] Deze procedures zorgen voor efficiënte data-extractie en -manipulatie direct op de database server.

* `usp_GetMinMaxPeriodForEAN`: Bepaalt het datumbereik van beschikbare data voor een EAN/ID en TypeIDs. [cite: 6, 127]
* `usp_GetConnectionDataFull`: Haalt de daadwerkelijke meetdata op, gepivoteerd per register, en ondersteunt aggregatie en status-informatie. [cite: 17, 136] Kolomnamen volgen de conventie `<RegisterNaam> (<RegisterID>) (consumption)` en `<RegisterNaam> (<RegisterID>) (status)`. [cite: 23, 38, 143, 158]
* Andere specifieke stored procedures worden gebruikt door de respectievelijke notebooks voor factor updates, MV switch, en storage method aanpassingen.

### Caching

* Een `TTLCache` (Time-To-Live Cache) wordt gebruikt in de Python-laag om de resultaten van database queries (zoals min/max periodes en volledige datasets) tijdelijk op te slaan. [cite: 32, 148] Dit vermindert de belasting op de database en versnelt herhaalde aanvragen. De standaard TTL (Time-To-Live) is 300 seconden (5 minuten). [cite: 148]

### Kolomnaam Conventies

* Gepivoteerde datakolommen in de output van `usp_GetConnectionDataFull` en in de Python DataFrames volgen een duidelijke naamgevingsconventie:
    * Consumptiedata: `"<Register Beschrijving> (<RegisterID>) (consumption)"` [cite: 23, 38, 143, 158]
    * Statusdata (optioneel): `"<Register Beschrijving> (<RegisterID>) (status)"` [cite: 23, 38, 143, 158]
* In de `005_MV_Switch.ipynb` worden kolomnamen gestandaardiseerd naar kleine letters met underscores. [cite: 89]

### Datatype Precisie

* In `usp_GetConnectionDataFull` en de Python-laag wordt consumptiedata als `FLOAT` behandeld om afrondingsverschillen te voorkomen en volledige precisie te waarborgen. [cite: 20, 22, 142] Dit is een wijziging ten opzichte van eerdere versies waar `DECIMAL(18,6)` mogelijk werd gebruikt. [cite: 20]

## Best Practices & Aandachtspunten

* **Inputvalidatie**:
    * Valideer EANs/IDs op formaat en bestaan in de database. [cite: 94]
    * Datums moeten in het formaat `dd/MM/yyyy HH:mm` zijn. [cite: 9, 129] Strikte validatie is geïmplementeerd. [cite: 37, 157]
    * Zorg dat de einddatum niet voor de startdatum ligt.
    * Voorkom dat datums in de toekomst liggen.
    * Selecties voor `RegistratorID` in `005_MV_Switch.ipynb` moeten uit de dynamisch gevulde dropdown komen. [cite: 95]
* **Performance**:
    * De `TTLCache` helpt de database load te verminderen. [cite: 32, 148] Pas de TTL aan indien nodig. [cite: 37, 157]
    * Gebruik de `NullPool` in SQLAlchemy voor snellere verbindingen bij frequente, korte queries. [cite: 50]
    * De `fast_executemany=True` optie wordt gebruikt voor potentieel snellere bulk inserts/updates. [cite: 67]
    * Overweeg timeouts voor lange queries. [cite: 96, 119]
    * Bij de `004_Factorupdate.ipynb` worden updates in batches verwerkt. [cite: 117]
    * Data-requests worden gelimiteerd tot `MAX_ROWS` (standaard 8000 rijen) om performance problemen te voorkomen. De UI geeft waarschuwingen en past frequenties automatisch aan ("capping").
* **Security**:
    * `.env` bestanden met credentials mogen **nooit** in versiebeheer (Git) worden opgenomen. [cite: 39, 98, 159] Gebruik hiervoor de `.gitignore`.
    * Voor productieomgevingen, gebruik secrets management via CI/CD pipelines of orchestratieplatformen zoals Kubernetes. [cite: 39, 98, 159]
    * Alle SQL queries zijn geparameteriseerd om SQL-injectie te voorkomen. [cite: 118]
* **Foutafhandeling**:
    * De stored procedures gebruiken `THROW` voor duidelijke foutmeldingen (bijv., error 50000 voor ongeldige parameters, 50001 voor geen data). [cite: 24]
    * Python-code logt databasefouten en geeft feedback in de UI. [cite: 68]
    * Transacties in `004_Factorupdate.ipynb` en `007_Storage_Method.ipynb` zorgen voor rollback bij fouten. [cite: 69, 110, 118]
* **Styling & UX**:
    * `common_imports.py` injecteert `custom.css` voor een consistente look-and-feel. [cite: 33, 70, 114, 150]
    * `progress_utils.py` levert `ProgressDisplay` voor visuele feedback met ETA. [cite: 33, 52, 87, 112, 116, 151]
* **CI/CD**:
    * Overweeg een CI/CD pipeline die `poetry run python -m mappings` uitvoert om de uniciteit van TypeIDs in `mappings.py` te valideren. [cite: 39, 152, 159]

## Contributie-richtlijnen

Momenteel zijn er geen specifieke richtlijnen voor contributie. Voor interne projecten, volg de gangbare ontwikkelstandaarden van het team.

## Licentie

Dit project wordt uitgebracht onder de MIT Licentie. Zie het `LICENSE` bestand voor meer details.

## Contact / Auteurs

* **Afdeling**: Data Management, INNAX Meten B.V.
* **Contact**: (Voeg hier relevante contactinformatie of mailgroep toe)
