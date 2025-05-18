SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE   PROCEDURE [dbo].[usp_GetMinMaxPeriod_OnlyLDNODN]
(
    @EAN_ConnectionPoint VARCHAR(255),
    @StartDate DATETIME,
    @EndDate DATETIME
)
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    IF NOT EXISTS (
        SELECT 1
        FROM dbo.TBL_ConnectionPoint cp
        WHERE cp.[EAN_ConnectionPoint] = @EAN_ConnectionPoint
    )
    BEGIN
        DECLARE @ErrorMessage NVARCHAR(255) = N'Geen ConnectionPoint gevonden voor EAN=' + @EAN_ConnectionPoint;
        THROW 50000, @ErrorMessage, 1;
    END;

    SELECT
        MIN(d.[utcperiod]) AS MinPeriod,
        MAX(d.[utcperiod]) AS MaxPeriod
    FROM dbo.TBL_Data d
    WHERE d.[registerid] IN (
        SELECT r.ID
        FROM dbo.TBL_Register r
        INNER JOIN dbo.TBL_ConnectionPoint cp ON r.[ConnectionPointId] = cp.[ID]
        WHERE cp.[EAN_ConnectionPoint] = @EAN_ConnectionPoint
          AND r.[TypeId] IN (1000,1007,1050,1051,1075,1076,1088,1094,
                             1001,1005,1077,1078,1089)
    )
    AND d.[utcperiod] BETWEEN @StartDate AND @EndDate;
END;
GO
