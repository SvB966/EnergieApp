CREATE OR ALTER PROCEDURE [dbo].[usp_GetMinMaxPeriodForEAN]
(
    @EAN_ConnectionPoint VARCHAR(255),
    @AllowedTypeIDs      VARCHAR(MAX),
    @StartDateStr        VARCHAR(50),
    @EndDateStr          VARCHAR(50),
    @SearchMethod        VARCHAR(20) = 'transferpoint'
)
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    DECLARE @ErrMsg        NVARCHAR(4000);
    DECLARE @StartDateTime DATETIME;
    DECLARE @EndDateTime   DATETIME;

    -- 1. Datums parsen (dd/mm/yyyy HH:MM verwacht)
    BEGIN TRY
        SET @StartDateTime = CONVERT(DATETIME, @StartDateStr, 103);
        SET @EndDateTime   = CONVERT(DATETIME, @EndDateStr, 103);
    END TRY
    BEGIN CATCH
        SET @ErrMsg = N'Ongeldig datumformaat. Verwacht: dd/mm/yyyy HH:MM - Input: '
                      + @StartDateStr + N', ' + @EndDateStr;
        THROW 50000, @ErrMsg, 1;
    END CATCH;

    -- 2. Zet AllowedTypeIDs in temp-table
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

    -- 3. Afhankelijk van @SearchMethod zoeken in TBL_Register / TBL_ConnectionPoint
    IF @SearchMethod = 'registerid'
    BEGIN
        DECLARE @RegisterID BIGINT = TRY_CAST(@EAN_ConnectionPoint AS BIGINT);
        IF @RegisterID IS NULL
        BEGIN
            SET @ErrMsg = 'Geen geldig registerID opgegeven (' + @EAN_ConnectionPoint + ')';
            THROW 50000, @ErrMsg, 1;
        END;

        SELECT
            MIN(d.utcperiod) AS MinUTCPeriod,
            MAX(d.utcperiod) AS MaxUTCPeriod
        FROM dbo.TBL_Data d
        INNER JOIN dbo.TBL_Register r ON r.ID = d.RegisterID
        WHERE r.ID = @RegisterID
          AND r.TypeId IN (SELECT TypeID FROM #AllowedTypes)
          AND d.utcperiod BETWEEN @StartDateTime AND @EndDateTime;
    END
    ELSE IF @SearchMethod = 'registratorid'
    BEGIN
        DECLARE @RegistratorID BIGINT = TRY_CAST(@EAN_ConnectionPoint AS BIGINT);
        IF @RegistratorID IS NULL
        BEGIN
            SET @ErrMsg = 'Geen geldig registratorID opgegeven (' + @EAN_ConnectionPoint + ')';
            THROW 50000, @ErrMsg, 1;
        END;

        SELECT
            MIN(d.utcperiod) AS MinUTCPeriod,
            MAX(d.utcperiod) AS MaxUTCPeriod
        FROM dbo.TBL_Data d
        INNER JOIN dbo.TBL_Register r ON r.ID = d.registerID
        WHERE r.RegistratorID = @RegistratorID
          AND r.TypeId IN (SELECT TypeID FROM #AllowedTypes)
          AND d.utcperiod BETWEEN @StartDateTime AND @EndDateTime;
    END
    ELSE IF @SearchMethod = 'objectid'
    BEGIN
        DECLARE @SearchObjectID BIGINT;
        SELECT TOP 1 @SearchObjectID = cp.ObjectId
        FROM dbo.TBL_ConnectionPoint cp
        WHERE cp.EAN_ConnectionPoint = @EAN_ConnectionPoint;

        IF @SearchObjectID IS NULL
        BEGIN
            SET @ErrMsg = 'Geen ConnectionPoint gevonden voor EAN=' + @EAN_ConnectionPoint;
            THROW 50000, @ErrMsg, 1;
        END;

        SELECT
            MIN(d.utcperiod) AS MinUTCPeriod,
            MAX(d.utcperiod) AS MaxUTCPeriod
        FROM dbo.TBL_Data d
        INNER JOIN dbo.TBL_Register r ON r.ID = d.registerID
        WHERE r.ConnectionPointId IN
        (
            SELECT cp.ID
            FROM dbo.TBL_ConnectionPoint cp
            WHERE cp.ObjectId = @SearchObjectID
        )
          AND r.TypeId IN (SELECT TypeID FROM #AllowedTypes)
          AND d.utcperiod BETWEEN @StartDateTime AND @EndDateTime;
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
            SET @ErrMsg = 'Geen ConnectionPoint gevonden voor EAN=' + @EAN_ConnectionPoint;
            THROW 50000, @ErrMsg, 1;
        END;

        SELECT
            MIN(d.utcperiod) AS MinUTCPeriod,
            MAX(d.utcperiod) AS MaxUTCPeriod
        FROM dbo.TBL_Data d
        WHERE d.utcperiod BETWEEN @StartDateTime AND @EndDateTime
          AND d.RegisterID IN
          (
              SELECT r.ID
              FROM dbo.TBL_Register r
              INNER JOIN dbo.TBL_ConnectionPoint cp ON cp.ID = r.ConnectionPointId
              WHERE (cp.ID = @SearchID OR cp.TransferPointID = @SearchID)
                AND r.TypeId IN (SELECT TypeID FROM #AllowedTypes)
          );
    END;

    IF OBJECT_ID('tempdb..#AllowedTypes') IS NOT NULL
        DROP TABLE #AllowedTypes;
END;
GO

