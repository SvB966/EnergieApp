
CREATE OR ALTER PROCEDURE [dbo].[usp_GetConnectionDataFull]
(
    @EAN_ConnectionPoint  VARCHAR(255),
    @AllowedTypeIDs       VARCHAR(MAX),
    @StartDateStr         VARCHAR(50),
    @EndDateStr           VARCHAR(50),
    @SearchMethod         VARCHAR(20) = 'transferpoint',
    @IntervalMinutes      INT = 5,
    @IncludeStatus        BIT = 0
)
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    DECLARE @ErrMsg        NVARCHAR(4000);
    DECLARE @StartDateTime DATETIME;
    DECLARE @EndDateTime   DATETIME;

    -- 1. Datums parsen
    BEGIN TRY
        SET @StartDateTime = CONVERT(DATETIME, @StartDateStr, 103);
        SET @EndDateTime   = CONVERT(DATETIME, @EndDateStr, 103);
    END TRY
    BEGIN CATCH
        SET @ErrMsg = N'Ongeldig datumformaat. Verwacht: dd/mm/yyyy HH:MM - Input: '
                      + @StartDateStr + N', ' + @EndDateStr;
        THROW 50000, @ErrMsg, 1;
    END CATCH;

    -- 2. AllowedTypeIDs in temp-table
    IF OBJECT_ID('tempdb..#AllowedTypes') IS NOT NULL
        DROP TABLE #AllowedTypes;

    CREATE TABLE #AllowedTypes (TypeID BIGINT NOT NULL);

    INSERT INTO #AllowedTypes (TypeID)
    SELECT TRY_CAST([value] AS BIGINT)
    FROM STRING_SPLIT(@AllowedTypeIDs, ',')
    WHERE TRY_CAST([value] AS BIGINT) IS NOT NULL;

    -- Extra controle: indien geen geldige TypeIDs
    IF NOT EXISTS (SELECT 1 FROM #AllowedTypes)
    BEGIN
        SET @ErrMsg = 'Geen geldige TypeIDs opgegeven: ' + @AllowedTypeIDs;
        THROW 50000, @ErrMsg, 1;
    END;

    -- 3. #FilteredData aanmaken (aangepast: consumption nu FLOAT i.p.v. DECIMAL(18,6))
    IF OBJECT_ID('tempdb..#FilteredData') IS NOT NULL
        DROP TABLE #FilteredData;

    CREATE TABLE #FilteredData
    (
        utcperiod   DATETIME,
        registerid  BIGINT,
        consumption FLOAT,
        statusid    CHAR(1)
    );

    -- 4. Filtering op basis van @SearchMethod
    IF @SearchMethod = 'registerid'
    BEGIN
        DECLARE @RegisterID BIGINT = TRY_CAST(@EAN_ConnectionPoint AS BIGINT);
        IF @RegisterID IS NULL
        BEGIN
            SET @ErrMsg = CONCAT('Geen geldig registerID opgegeven (', @EAN_ConnectionPoint, ')');
            THROW 50000, @ErrMsg, 1;
        END;

        INSERT INTO #FilteredData (utcperiod, registerid, consumption, statusid)
        SELECT
            d.utcperiod,
            d.registerid,
            d.consumption,               -- Geen CAST naar DECIMAL(18,6)
            ISNULL(d.statusid, '')
        FROM dbo.TBL_Data d
        INNER JOIN dbo.TBL_Register r ON r.ID = d.registerid
        WHERE d.utcperiod BETWEEN @StartDateTime AND @EndDateTime
          AND r.ID = @RegisterID
          AND r.TypeId IN (SELECT TypeID FROM #AllowedTypes);
    END
    ELSE IF @SearchMethod = 'registratorid'
    BEGIN
        DECLARE @RegistratorID BIGINT = TRY_CAST(@EAN_ConnectionPoint AS BIGINT);
        IF @RegistratorID IS NULL
        BEGIN
            SET @ErrMsg = CONCAT('Geen geldig registratorID opgegeven (', @EAN_ConnectionPoint, ')');
            THROW 50000, @ErrMsg, 1;
        END;

        INSERT INTO #FilteredData (utcperiod, registerid, consumption, statusid)
        SELECT
            d.utcperiod,
            d.registerid,
            d.consumption,
            ISNULL(d.statusid, '')
        FROM dbo.TBL_Data d
        INNER JOIN dbo.TBL_Register r ON r.ID = d.registerid
        WHERE d.utcperiod BETWEEN @StartDateTime AND @EndDateTime
          AND r.RegistratorID = @RegistratorID
          AND r.TypeId IN (SELECT TypeID FROM #AllowedTypes);
    END
    ELSE IF @SearchMethod = 'objectid'
    BEGIN
        DECLARE @SearchObjectID BIGINT;
        SELECT TOP 1 @SearchObjectID = cp.ObjectId
        FROM dbo.TBL_ConnectionPoint cp
        WHERE cp.EAN_ConnectionPoint = @EAN_ConnectionPoint;

        IF @SearchObjectID IS NULL
        BEGIN
            SET @ErrMsg = CONCAT('Geen ConnectionPoint gevonden voor EAN=', @EAN_ConnectionPoint);
            THROW 50000, @ErrMsg, 1;
        END;

        INSERT INTO #FilteredData (utcperiod, registerid, consumption, statusid)
        SELECT
            d.utcperiod,
            d.registerid,
            d.consumption,
            ISNULL(d.statusid, '')
        FROM dbo.TBL_Data d
        INNER JOIN dbo.TBL_Register r ON r.ID = d.registerid
        WHERE d.utcperiod BETWEEN @StartDateTime AND @EndDateTime
          AND r.ConnectionPointId IN
          (
              SELECT cp.ID
              FROM dbo.TBL_ConnectionPoint cp
              WHERE cp.ObjectId = @SearchObjectID
          )
          AND r.TypeId IN (SELECT TypeID FROM #AllowedTypes);
    END
    ELSE
    BEGIN
        -- Default: 'transferpoint'
        DECLARE @SearchID BIGINT;
        SELECT TOP 1 @SearchID = cp.ID
        FROM dbo.TBL_ConnectionPoint cp
        WHERE cp.EAN_ConnectionPoint = @EAN_ConnectionPoint;

        IF @SearchID IS NULL
        BEGIN
            SET @ErrMsg = CONCAT('Geen ConnectionPoint gevonden voor EAN=', @EAN_ConnectionPoint);
            THROW 50000, @ErrMsg, 1;
        END;

        INSERT INTO #FilteredData (utcperiod, registerid, consumption, statusid)
        SELECT
            d.utcperiod,
            d.registerid,
            d.consumption,
            ISNULL(d.statusid, '')
        FROM dbo.TBL_Data d
        WHERE d.utcperiod BETWEEN @StartDateTime AND @EndDateTime
          AND d.registerid IN
          (
              SELECT r.ID
              FROM dbo.TBL_Register r
              INNER JOIN dbo.TBL_ConnectionPoint cp ON cp.ID = r.ConnectionPointId
              WHERE (cp.ID = @SearchID OR cp.TransferPointID = @SearchID)
                AND r.TypeId IN (SELECT TypeID FROM #AllowedTypes)
          );
    END;

    -- 5. Controleer of er data is
    DECLARE @PeriodBegin DATETIME, @PeriodEnd DATETIME;
    SELECT @PeriodBegin = MIN(utcperiod),
           @PeriodEnd   = MAX(utcperiod)
    FROM #FilteredData;

    IF @PeriodBegin IS NULL OR @PeriodEnd IS NULL
    BEGIN
        SET @ErrMsg = CONCAT('Geen data gevonden voor ', @EAN_ConnectionPoint,
                             ' en TypeIDs=', @AllowedTypeIDs);
        THROW 50001, @ErrMsg, 1;
    END;

    -- 6. Bepaal dynamische kolomnamen (distinct registers)
    IF OBJECT_ID('tempdb..#RegisterColumns') IS NOT NULL
        DROP TABLE #RegisterColumns;

    ;WITH DistinctRegisters AS
    (
        SELECT DISTINCT
            r.ID          AS RegisterID,
            r.Description AS RegisterDesc
        FROM #FilteredData fd
        INNER JOIN dbo.TBL_Register r ON r.ID = fd.registerid
    )
    SELECT
        [PivotCols] = STRING_AGG(QUOTENAME(CAST(RegisterID AS VARCHAR(50))), ','),
        [ConsumptionSelect] = STRING_AGG(
            'c.' + QUOTENAME(CAST(RegisterID AS VARCHAR(50)))
            + ' AS [' + RegisterDesc + ' (' + CAST(RegisterID AS VARCHAR(50)) + ') (consumption)]',
            ','
        ),
        [StatusSelect] = STRING_AGG(
            's.' + QUOTENAME(CAST(RegisterID AS VARCHAR(50)))
            + ' AS [' + RegisterDesc + ' (' + CAST(RegisterID AS VARCHAR(50)) + ') (status)]',
            ','
        )
    INTO #RegisterColumns
    FROM DistinctRegisters;

    DECLARE @PivotCols         NVARCHAR(MAX) = (SELECT [PivotCols]         FROM #RegisterColumns);
    DECLARE @SelectColsC       NVARCHAR(MAX) = (SELECT [ConsumptionSelect] FROM #RegisterColumns);
    DECLARE @SelectColsS       NVARCHAR(MAX) = (SELECT [StatusSelect]      FROM #RegisterColumns);

    -- 7. Dynamische pivot-query opbouwen & uitvoeren
    DECLARE @SQL NVARCHAR(MAX);

    IF @IncludeStatus = 1
    BEGIN
        SET @SQL = N'
        ;WITH cteSource AS
        (
            SELECT
                AggregatedUTCPeriod = CASE 
                    WHEN @IntervalMinutes = -1 THEN utcperiod
                    WHEN @IntervalMinutes = 43200 THEN DATEFROMPARTS(YEAR(utcperiod), MONTH(utcperiod), 1)
                    ELSE DATEADD(MINUTE,
                         (@IntervalMinutes - DATEPART(MINUTE, utcperiod) % @IntervalMinutes) % @IntervalMinutes,
                         utcperiod)
                END,
                registerid,
                SUM(consumption) AS consumption,   -- direct float
                MAX(statusid)    AS statusid
            FROM #FilteredData
            GROUP BY CASE 
                WHEN @IntervalMinutes = -1 THEN utcperiod
                WHEN @IntervalMinutes = 43200 THEN DATEFROMPARTS(YEAR(utcperiod), MONTH(utcperiod), 1)
                ELSE DATEADD(MINUTE,
                     (@IntervalMinutes - DATEPART(MINUTE, utcperiod) % @IntervalMinutes) % @IntervalMinutes,
                     utcperiod)
            END,
            registerid
        ),

        ctePivotC AS
        (
            SELECT
                AggregatedUTCPeriod AS utcperiod, ' + @PivotCols + N'
            FROM
            (
                SELECT AggregatedUTCPeriod, registerid, consumption
                FROM cteSource
            ) AS srcC
            PIVOT
            (
                MAX(consumption)
                FOR registerid IN (' + @PivotCols + N')
            ) AS pvtC
        ),

        ctePivotS AS
        (
            SELECT
                AggregatedUTCPeriod AS utcperiod, ' + @PivotCols + N'
            FROM
            (
                SELECT AggregatedUTCPeriod, registerid, statusid
                FROM cteSource
            ) AS srcS
            PIVOT
            (
                MAX(statusid)
                FOR registerid IN (' + @PivotCols + N')
            ) AS pvtS
        )

        SELECT
            c.utcperiod,
            ' + @SelectColsC + N',
            ' + @SelectColsS + N'
        FROM ctePivotC c
        INNER JOIN ctePivotS s
            ON c.utcperiod = s.utcperiod
        ORDER BY c.utcperiod
        OPTION (RECOMPILE);';

        EXEC sp_executesql @SQL,
            N'@IntervalMinutes INT',
            @IntervalMinutes = @IntervalMinutes;
    END
    ELSE
    BEGIN
        -- Alleen consumptie, geen statuskolommen
        DECLARE @SelectColsC2 NVARCHAR(MAX) = REPLACE(@SelectColsC, 'c.', 'pvt.');
        SET @SQL = N'
        ;WITH cteSource AS
        (
            SELECT
                AggregatedUTCPeriod = CASE 
                    WHEN @IntervalMinutes = -1 THEN utcperiod
                    WHEN @IntervalMinutes = 43200 THEN DATEFROMPARTS(YEAR(utcperiod), MONTH(utcperiod), 1)
                    ELSE DATEADD(MINUTE,
                         (@IntervalMinutes - DATEPART(MINUTE, utcperiod) % @IntervalMinutes) % @IntervalMinutes,
                         utcperiod)
                END,
                registerid,
                SUM(consumption) AS consumption
            FROM #FilteredData
            GROUP BY CASE 
                WHEN @IntervalMinutes = -1 THEN utcperiod
                WHEN @IntervalMinutes = 43200 THEN DATEFROMPARTS(YEAR(utcperiod), MONTH(utcperiod), 1)
                ELSE DATEADD(MINUTE,
                     (@IntervalMinutes - DATEPART(MINUTE, utcperiod) % @IntervalMinutes) % @IntervalMinutes,
                     utcperiod)
            END,
            registerid
        )
        SELECT
            pvt.AggregatedUTCPeriod AS utcperiod,
            ' + @SelectColsC2 + N'
        FROM
        (
            SELECT AggregatedUTCPeriod, registerid, consumption
            FROM cteSource
        ) AS src
        PIVOT
        (
            MAX(consumption)
            FOR registerid IN (' + @PivotCols + N')
        ) AS pvt
        ORDER BY pvt.AggregatedUTCPeriod
        OPTION (RECOMPILE);';

        EXEC sp_executesql @SQL,
            N'@IntervalMinutes INT',
            @IntervalMinutes = @IntervalMinutes;
    END;

    -- 8. Opschonen
    IF OBJECT_ID('tempdb..#FilteredData') IS NOT NULL
        DROP TABLE #FilteredData;

    IF OBJECT_ID('tempdb..#RegisterColumns') IS NOT NULL
        DROP TABLE #RegisterColumns;

    IF OBJECT_ID('tempdb..#AllowedTypes') IS NOT NULL
        DROP TABLE #AllowedTypes;
END;
GO