SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE   PROCEDURE [dbo].[usp_GetConnectionDataFull_OnlyLDNODN]
(
    @EAN_ConnectionPoint VARCHAR(255),
    @StartDate DATETIME,
    @EndDate DATETIME
)
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    -- Controleer of het opgegeven EAN bestaat
    IF NOT EXISTS (
        SELECT 1
        FROM dbo.TBL_ConnectionPoint
        WHERE [EAN_ConnectionPoint] = @EAN_ConnectionPoint
    )
    BEGIN
        RAISERROR('Specified EAN does not exist.',16,1);
        RETURN;
    END;

    ------------------------------------------------------------------------------
    -- Bepaal de dynamische lijst met kolommen (Descriptions) voor de PIVOT
    ------------------------------------------------------------------------------
    DECLARE @cols       VARCHAR(MAX);
    DECLARE @sqlCols    NVARCHAR(MAX);
    DECLARE @cols_out   VARCHAR(MAX);

    SET @sqlCols = N'
        SELECT @cols_out = STRING_AGG(QUOTENAME([Description]), '','')
        FROM (
            SELECT DISTINCT r.[Description]
            FROM dbo.TBL_Data d
            INNER JOIN dbo.TBL_Register r         ON d.[registerid] = r.[ID]
            INNER JOIN dbo.TBL_ConnectionPoint cp ON r.[ConnectionPointId] = cp.[ID]
            WHERE cp.[EAN_ConnectionPoint] = @EAN_ConnectionPoint
              AND d.[utcperiod] BETWEEN @StartDate AND @EndDate
              AND r.[TypeId] IN (1000,1007,1050,1051,1075,1076,1088,1094,
                                 1001,1005,1077,1078,1089)
        ) AS t;
    ';

    EXEC sp_executesql 
         @sqlCols,
         N'@EAN_ConnectionPoint VARCHAR(255), @StartDate DATETIME, @EndDate DATETIME, @cols_out VARCHAR(MAX) OUTPUT',
         @EAN_ConnectionPoint = @EAN_ConnectionPoint,
         @StartDate = @StartDate,
         @EndDate = @EndDate,
         @cols_out = @cols_out OUTPUT;

    SET @cols = @cols_out;

    IF @cols IS NULL
    BEGIN
        RAISERROR('No data found for the specified parameters.',16,1);
        RETURN;
    END;

    ------------------------------------------------------------------------------
    -- Bouw de dynamische PIVOT-query (vervanging van de CTE door inline subselect)
    ------------------------------------------------------------------------------
    DECLARE @sql NVARCHAR(MAX);

    SET @sql = N'
        SELECT
            [utcperiod],
            ' + @cols + '
        FROM
        (
            SELECT
                d.[utcperiod],
                r.[Description],
                d.[consumption]
            FROM dbo.TBL_Data d
            INNER JOIN dbo.TBL_Register r         ON d.[registerid] = r.[ID]
            INNER JOIN dbo.TBL_ConnectionPoint cp ON r.[ConnectionPointId] = cp.[ID]
            WHERE cp.[EAN_ConnectionPoint] = @EAN_ConnectionPoint
              AND d.[utcperiod] BETWEEN @StartDate AND @EndDate
              AND r.[TypeId] IN (1000,1007,1050,1051,1075,1076,1088,1094,
                                 1001,1005,1077,1078,1089)
        ) AS Src
        PIVOT
        (
            MAX([consumption])
            FOR [Description] IN (' + @cols + ')
        ) AS Pvt
        ORDER BY [utcperiod];
    ';

    EXEC sp_executesql @sql,
         N'@EAN_ConnectionPoint VARCHAR(255), @StartDate DATETIME, @EndDate DATETIME',
         @EAN_ConnectionPoint = @EAN_ConnectionPoint,
         @StartDate = @StartDate,
         @EndDate = @EndDate;
END;
GO
