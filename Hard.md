

# 🏢 10 Cross-Database Business Standard Queries

These are the kind of queries a business analyst, manager, or executive would run on a regular day — spanning multiple domains (sales, purchasing, manufacturing, HR, inventory) and touching many tables.

---

## Q1: "Daily Executive Dashboard — Sales, Procurement, and Manufacturing KPIs for the current month"

*Use case: CEO/COO morning briefing — one-stop snapshot of business health*

*12 tables touched*

```sql
WITH SalesKPIs AS (
    SELECT
        COUNT(DISTINCT soh.SalesOrderID) AS SalesOrders,
        ROUND(SUM(soh.TotalDue), 2) AS SalesRevenue,
        ROUND(AVG(soh.TotalDue), 2) AS AvgOrderValue,
        COUNT(DISTINCT soh.CustomerID) AS ActiveCustomers,
        SUM(CASE WHEN soh.OnlineOrderFlag = 1 THEN 1 ELSE 0 END) AS OnlineOrders,
        SUM(CASE WHEN soh.OnlineOrderFlag = 0 THEN 1 ELSE 0 END) AS RepOrders,
        SUM(CASE WHEN soh.ShipDate IS NULL THEN 1 ELSE 0 END) AS UnshippedOrders
    FROM SalesOrderHeader soh
    WHERE strftime('%Y-%m', soh.OrderDate) = strftime('%Y-%m', 'now')
),
ProcurementKPIs AS (
    SELECT
        COUNT(DISTINCT poh.PurchaseOrderID) AS PurchaseOrders,
        ROUND(SUM(poh.TotalDue), 2) AS ProcurementSpend,
        SUM(CASE WHEN poh.Status = 1 THEN 1 ELSE 0 END) AS PendingPOs,
        SUM(CASE WHEN poh.Status = 4 THEN 1 ELSE 0 END) AS CompletedPOs
    FROM PurchaseOrderHeader poh
    WHERE strftime('%Y-%m', poh.OrderDate) = strftime('%Y-%m', 'now')
),
ManufacturingKPIs AS (
    SELECT
        COUNT(*) AS WorkOrders,
        SUM(wo.OrderQty) AS PlannedQty,
        SUM(wo.StockedQty) AS ProducedQty,
        SUM(wo.ScrappedQty) AS ScrappedQty,
        ROUND(SUM(wo.ScrappedQty) * 100.0 / NULLIF(SUM(wo.OrderQty), 0), 2) AS ScrapRatePct,
        SUM(CASE WHEN wo.EndDate IS NULL THEN 1 ELSE 0 END) AS InProgressWOs
    FROM WorkOrder wo
    WHERE strftime('%Y-%m', wo.StartDate) = strftime('%Y-%m', 'now')
)
SELECT
    '📊 SALES' AS Domain,
    s.SalesOrders AS Volume,
    s.SalesRevenue AS DollarValue,
    s.AvgOrderValue AS AvgValue,
    s.ActiveCustomers AS KeyMetric1,
    s.OnlineOrders || ' online / ' || s.RepOrders || ' rep' AS KeyMetric2,
    s.UnshippedOrders || ' unshipped' AS Alert
FROM SalesKPIs s

UNION ALL

SELECT
    '🛒 PROCUREMENT',
    p.PurchaseOrders,
    p.ProcurementSpend,
    ROUND(p.ProcurementSpend / NULLIF(p.PurchaseOrders, 0), 2),
    p.CompletedPOs,
    p.PendingPOs || ' pending',
    NULL
FROM ProcurementKPIs p

UNION ALL

SELECT
    '🏭 MANUFACTURING',
    m.WorkOrders,
    NULL,
    NULL,
    m.ProducedQty,
    m.ScrapRatePct || '% scrap rate',
    m.InProgressWOs || ' in progress'
FROM ManufacturingKPIs m;
```

---

## Q2: "Revenue by Territory, Product Category, and Channel — for quarterly business review"

*Use case: VP of Sales — quarterly performance review across all dimensions*

*7 joins*

```sql
SELECT
    st.Name AS Territory,
    st."Group" AS TerritoryGroup,
    pcat.Name AS ProductCategory,
    CASE WHEN soh.OnlineOrderFlag = 1 THEN 'Online' ELSE 'Sales Rep' END AS Channel,
    COUNT(DISTINCT soh.SalesOrderID) AS Orders,
    SUM(sod.OrderQty) AS UnitsSold,
    ROUND(SUM(sod.LineTotal), 2) AS Revenue,
    ROUND(AVG(sod.UnitPrice), 2) AS AvgSellingPrice,
    ROUND(AVG(sod.UnitPriceDiscount) * 100, 2) AS AvgDiscountPct
FROM SalesOrderHeader soh
JOIN SalesOrderDetail sod ON soh.SalesOrderID = sod.SalesOrderID
JOIN SalesTerritory st ON soh.TerritoryID = st.TerritoryID
JOIN Product p ON sod.ProductID = p.ProductID
LEFT JOIN ProductSubcategory psub ON p.ProductSubcategoryID = psub.ProductSubcategoryID
LEFT JOIN ProductCategory pcat ON psub.ProductCategoryID = pcat.ProductCategoryID
WHERE strftime('%Y', soh.OrderDate) = strftime('%Y', 'now')
GROUP BY st.Name, st."Group", pcat.Name, soh.OnlineOrderFlag
ORDER BY Revenue DESC;
```

---

## Q3: "Salesperson Scorecard — Revenue vs. Quota, Order Count, Top Product, and Territory"

*Use case: Sales manager — weekly salesperson performance review*

*10 joins*

```sql
SELECT
    per.FirstName || ' ' || per.LastName AS SalesPersonName,
    e.JobTitle,
    d.Name AS Department,
    st.Name AS Territory,
    sp.SalesQuota AS CurrentQuota,
    sp.SalesYTD,
    ROUND(sp.SalesYTD - COALESCE(sp.SalesQuota, 0), 2) AS QuotaVariance,
    CASE
        WHEN sp.SalesYTD >= COALESCE(sp.SalesQuota, 0) THEN '✅ On/Above Quota'
        ELSE '⚠️ Below Quota'
    END AS QuotaStatus,
    sp.Bonus,
    sp.CommissionPct,
    COUNT(DISTINCT soh.SalesOrderID) AS OrdersThisYear,
    ROUND(SUM(soh.TotalDue), 2) AS RevenueThisYear,
    ROUND(AVG(soh.TotalDue), 2) AS AvgOrderValue
FROM SalesPerson sp
JOIN Employee e ON sp.BusinessEntityID = e.BusinessEntityID
JOIN Person per ON e.BusinessEntityID = per.BusinessEntityID
JOIN EmployeeDepartmentHistory edh ON e.BusinessEntityID = edh.BusinessEntityID
    AND edh.EndDate IS NULL
JOIN Department d ON edh.DepartmentID = d.DepartmentID
LEFT JOIN SalesTerritory st ON sp.TerritoryID = st.TerritoryID
LEFT JOIN SalesOrderHeader soh ON sp.BusinessEntityID = soh.SalesPersonID
    AND strftime('%Y', soh.OrderDate) = strftime('%Y', 'now')
GROUP BY per.FirstName, per.LastName, e.JobTitle, d.Name, st.Name,
         sp.SalesQuota, sp.SalesYTD, sp.Bonus, sp.CommissionPct
ORDER BY RevenueThisYear DESC;
```

---

## Q4: "Product Profitability Report — Buy Cost + Manufacturing Cost vs. Sell Price for Each Product"

*Use case: Finance / product management — full product P&L*

*10 joins*

```sql
SELECT
    p.Name AS ProductName,
    p.ProductNumber,
    pcat.Name AS Category,
    p.StandardCost,
    p.ListPrice,
    COALESCE(purchase.AvgBuyCost, 0) AS AvgPurchaseCost,
    COALESCE(mfg.AvgMfgCostPerUnit, 0) AS AvgMfgCostPerUnit,
    COALESCE(sales.AvgSellingPrice, 0) AS AvgActualSellingPrice,
    COALESCE(sales.TotalUnitsSold, 0) AS TotalUnitsSold,
    COALESCE(ROUND(sales.TotalRevenue, 2), 0) AS TotalRevenue,
    ROUND(
        COALESCE(sales.AvgSellingPrice, 0)
        - COALESCE(purchase.AvgBuyCost, 0)
        - COALESCE(mfg.AvgMfgCostPerUnit, 0), 2
    ) AS EstimatedMarginPerUnit,
    CASE
        WHEN COALESCE(sales.AvgSellingPrice, 0) <= COALESCE(purchase.AvgBuyCost, 0) + COALESCE(mfg.AvgMfgCostPerUnit, 0)
        THEN '🔴 UNPROFITABLE'
        ELSE '🟢 PROFITABLE'
    END AS ProfitabilityFlag
FROM Product p
LEFT JOIN ProductSubcategory psub ON p.ProductSubcategoryID = psub.ProductSubcategoryID
LEFT JOIN ProductCategory pcat ON psub.ProductCategoryID = pcat.ProductCategoryID
LEFT JOIN (
    SELECT ProductID, ROUND(AVG(UnitPrice), 2) AS AvgBuyCost
    FROM PurchaseOrderDetail GROUP BY ProductID
) purchase ON p.ProductID = purchase.ProductID
LEFT JOIN (
    SELECT wo.ProductID,
        ROUND(SUM(wor.ActualCost) / NULLIF(SUM(wo.StockedQty), 0), 2) AS AvgMfgCostPerUnit
    FROM WorkOrder wo
    JOIN WorkOrderRouting wor ON wo.WorkOrderID = wor.WorkOrderID
    GROUP BY wo.ProductID
) mfg ON p.ProductID = mfg.ProductID
LEFT JOIN (
    SELECT ProductID,
        ROUND(AVG(UnitPrice * (1 - UnitPriceDiscount)), 2) AS AvgSellingPrice,
        SUM(OrderQty) AS TotalUnitsSold,
        SUM(LineTotal) AS TotalRevenue
    FROM SalesOrderDetail GROUP BY ProductID
) sales ON p.ProductID = sales.ProductID
WHERE p.FinishedGoodsFlag = 1
ORDER BY EstimatedMarginPerUnit ASC;
```

---

## Q5: "Inventory Health Check — Current Stock vs. Reorder Point, with Recent Sales Velocity"

*Use case: Supply chain / warehouse manager — daily inventory review*

*6 joins*

```sql
SELECT
    p.Name AS ProductName,
    p.ProductNumber,
    pcat.Name AS Category,
    p.SafetyStockLevel,
    p.ReorderPoint,
    COALESCE(inv.TotalStock, 0) AS CurrentStock,
    COALESCE(inv.LocationCount, 0) AS StockedAtLocations,
    COALESCE(recent_sales.Last30DaysQty, 0) AS SoldLast30Days,
    COALESCE(recent_sales.Last30DaysRevenue, 0) AS RevenueLast30Days,
    CASE
        WHEN COALESCE(inv.TotalStock, 0) = 0 THEN '🔴 OUT OF STOCK'
        WHEN COALESCE(inv.TotalStock, 0) <= p.ReorderPoint THEN '🟡 REORDER NOW'
        WHEN COALESCE(inv.TotalStock, 0) <= p.SafetyStockLevel THEN '🟠 LOW STOCK'
        ELSE '🟢 OK'
    END AS StockStatus,
    CASE
        WHEN COALESCE(recent_sales.Last30DaysQty, 0) > 0
        THEN ROUND(COALESCE(inv.TotalStock, 0) * 1.0 / recent_sales.Last30DaysQty * 30, 0)
        ELSE NULL
    END AS EstimatedDaysOfStock
FROM Product p
LEFT JOIN ProductSubcategory psub ON p.ProductSubcategoryID = psub.ProductSubcategoryID
LEFT JOIN ProductCategory pcat ON psub.ProductCategoryID = pcat.ProductCategoryID
LEFT JOIN (
    SELECT ProductID, SUM(Quantity) AS TotalStock, COUNT(DISTINCT LocationID) AS LocationCount
    FROM ProductInventory GROUP BY ProductID
) inv ON p.ProductID = inv.ProductID
LEFT JOIN (
    SELECT sod.ProductID,
        SUM(sod.OrderQty) AS Last30DaysQty,
        ROUND(SUM(sod.LineTotal), 2) AS Last30DaysRevenue
    FROM SalesOrderDetail sod
    JOIN SalesOrderHeader soh ON sod.SalesOrderID = soh.SalesOrderID
    WHERE soh.OrderDate >= DATE('now', '-30 days')
    GROUP BY sod.ProductID
) recent_sales ON p.ProductID = recent_sales.ProductID
WHERE p.FinishedGoodsFlag = 1
    AND p.SellEndDate IS NULL
ORDER BY
    CASE
        WHEN COALESCE(inv.TotalStock, 0) = 0 THEN 1
        WHEN COALESCE(inv.TotalStock, 0) <= p.ReorderPoint THEN 2
        WHEN COALESCE(inv.TotalStock, 0) <= p.SafetyStockLevel THEN 3
        ELSE 4
    END,
    EstimatedDaysOfStock ASC;
```

---

## Q6: "Vendor Scorecard — Spend, Delivery, Quality, and Product Coverage per Vendor"

*Use case: Procurement manager — quarterly vendor performance review*

*8 joins*

```sql
SELECT
    v.Name AS VendorName,
    v.CreditRating,
    CASE WHEN v.PreferredVendorStatus = 1 THEN 'Preferred' ELSE 'Standard' END AS VendorTier,
    CASE WHEN v.ActiveFlag = 1 THEN 'Active' ELSE 'Inactive' END AS Status,
    a.City AS VendorCity,
    cr.Name AS VendorCountry,
    COUNT(DISTINCT pv.ProductID) AS ProductsSupplied,
    ROUND(AVG(pv.AverageLeadTime), 0) AS AvgLeadTimeDays,
    COUNT(DISTINCT poh.PurchaseOrderID) AS TotalPOs,
    ROUND(SUM(poh.TotalDue), 2) AS TotalSpend,
    ROUND(AVG(poh.TotalDue), 2) AS AvgPOValue,
    SUM(pod.ReceivedQty) AS TotalReceived,
    SUM(pod.RejectedQty) AS TotalRejected,
    ROUND(SUM(pod.RejectedQty) * 100.0 / NULLIF(SUM(pod.ReceivedQty), 0), 2) AS RejectionRatePct,
    CASE
        WHEN SUM(pod.RejectedQty) * 100.0 / NULLIF(SUM(pod.ReceivedQty), 0) > 5 THEN '🔴 HIGH REJECTION'
        WHEN SUM(pod.RejectedQty) * 100.0 / NULLIF(SUM(pod.ReceivedQty), 0) > 2 THEN '🟡 MODERATE'
        ELSE '🟢 GOOD'
    END AS QualityFlag
FROM Vendor v
LEFT JOIN ProductVendor pv ON v.BusinessEntityID = pv.BusinessEntityID
LEFT JOIN PurchaseOrderHeader poh ON v.BusinessEntityID = poh.VendorID
LEFT JOIN PurchaseOrderDetail pod ON poh.PurchaseOrderID = pod.PurchaseOrderID
LEFT JOIN BusinessEntityAddress bea ON v.BusinessEntityID = bea.BusinessEntityID
LEFT JOIN Address a ON bea.AddressID = a.AddressID
LEFT JOIN StateProvince sp ON a.StateProvinceID = sp.StateProvinceID
LEFT JOIN CountryRegion cr ON sp.CountryRegionCode = cr.CountryRegionCode
GROUP BY v.BusinessEntityID, v.Name, v.CreditRating, v.PreferredVendorStatus,
         v.ActiveFlag, a.City, cr.Name
ORDER BY TotalSpend DESC;
```

---

## Q7: "Customer Lifetime Value — Top 50 Customers by Total Spend, with Order Frequency and Recency"

*Use case: Marketing / CRM — high-value customer identification*

*8 joins*

```sql
SELECT
    c.CustomerID,
    COALESCE(per.FirstName || ' ' || per.LastName, s.Name) AS CustomerName,
    CASE
        WHEN c.PersonID IS NOT NULL AND c.StoreID IS NULL THEN 'Individual'
        WHEN c.StoreID IS NOT NULL THEN 'Store'
        ELSE 'Unknown'
    END AS CustomerType,
    st.Name AS Territory,
    ea.EmailAddress,
    COUNT(DISTINCT soh.SalesOrderID) AS LifetimeOrders,
    ROUND(SUM(soh.TotalDue), 2) AS LifetimeRevenue,
    ROUND(AVG(soh.TotalDue), 2) AS AvgOrderValue,
    MIN(soh.OrderDate) AS FirstOrderDate,
    MAX(soh.OrderDate) AS LastOrderDate,
    CAST(JULIANDAY('now') - JULIANDAY(MAX(soh.OrderDate)) AS INTEGER) AS DaysSinceLastOrder,
    CAST(JULIANDAY(MAX(soh.OrderDate)) - JULIANDAY(MIN(soh.OrderDate)) AS INTEGER) AS CustomerLifespanDays,
    CASE
        WHEN JULIANDAY('now') - JULIANDAY(MAX(soh.OrderDate)) <= 90 THEN '🟢 Active'
        WHEN JULIANDAY('now') - JULIANDAY(MAX(soh.OrderDate)) <= 365 THEN '🟡 At Risk'
        ELSE '🔴 Lapsed'
    END AS EngagementStatus
FROM Customer c
LEFT JOIN Person per ON c.PersonID = per.BusinessEntityID
LEFT JOIN Store s ON c.StoreID = s.BusinessEntityID
LEFT JOIN EmailAddress ea ON c.PersonID = ea.BusinessEntityID
JOIN SalesOrderHeader soh ON c.CustomerID = soh.CustomerID
JOIN SalesTerritory st ON soh.TerritoryID = st.TerritoryID
GROUP BY c.CustomerID, per.FirstName, per.LastName, s.Name, c.PersonID,
         c.StoreID, st.Name, ea.EmailAddress
ORDER BY LifetimeRevenue DESC
LIMIT 50;
```

---

## Q8: "HR Workforce Overview — Headcount, Tenure, Compensation, and Leave by Department"

*Use case: HR director — monthly workforce health report*

*6 joins*

```sql
SELECT
    d.Name AS Department,
    d.GroupName AS DepartmentGroup,
    sh.Name AS Shift,
    COUNT(*) AS Headcount,
    SUM(CASE WHEN e.Gender = 'M' THEN 1 ELSE 0 END) AS Male,
    SUM(CASE WHEN e.Gender = 'F' THEN 1 ELSE 0 END) AS Female,
    SUM(CASE WHEN e.SalariedFlag = 1 THEN 1 ELSE 0 END) AS Salaried,
    SUM(CASE WHEN e.SalariedFlag = 0 THEN 1 ELSE 0 END) AS Hourly,
    ROUND(AVG((JULIANDAY('now') - JULIANDAY(e.HireDate)) / 365.25), 1) AS AvgTenureYears,
    ROUND(AVG(eph.Rate), 2) AS AvgPayRate,
    ROUND(MIN(eph.Rate), 2) AS MinPayRate,
    ROUND(MAX(eph.Rate), 2) AS MaxPayRate,
    ROUND(AVG(e.VacationHours), 1) AS AvgVacationHrs,
    ROUND(AVG(e.SickLeaveHours), 1) AS AvgSickLeaveHrs,
    SUM(CASE WHEN e.VacationHours > 80 THEN 1 ELSE 0 END) AS HighVacationAccrual
FROM Employee e
JOIN EmployeeDepartmentHistory edh ON e.BusinessEntityID = edh.BusinessEntityID
    AND edh.EndDate IS NULL
JOIN Department d ON edh.DepartmentID = d.DepartmentID
JOIN Shift sh ON edh.ShiftID = sh.ShiftID
JOIN Person per ON e.BusinessEntityID = per.BusinessEntityID
JOIN EmployeePayHistory eph ON e.BusinessEntityID = eph.BusinessEntityID
    AND eph.RateChangeDate = (
        SELECT MAX(eph2.RateChangeDate)
        FROM EmployeePayHistory eph2
        WHERE eph2.BusinessEntityID = e.BusinessEntityID
    )
WHERE e.CurrentFlag = 1
GROUP BY d.Name, d.GroupName, sh.Name
ORDER BY Headcount DESC;
```

---

## Q9: "End-to-End Value Chain — From Vendor Purchase to Manufacturing to Customer Sale for Each Product"

*Use case: COO / operations — full supply chain visibility per product*

*12 joins*

```sql
SELECT
    p.Name AS ProductName,
    pcat.Name AS Category,
    CASE WHEN p.MakeFlag = 1 THEN 'Manufactured' ELSE 'Purchased' END AS SourceType,

    -- PROCUREMENT
    COALESCE(purch.VendorCount, 0) AS VendorCount,
    COALESCE(ROUND(purch.TotalPurchaseCost, 2), 0) AS TotalPurchaseCost,
    COALESCE(ROUND(purch.AvgPurchasePrice, 2), 0) AS AvgPurchasePrice,
    COALESCE(ROUND(purch.RejectionRate, 2), 0) AS PurchaseRejectionPct,

    -- MANUFACTURING
    COALESCE(mfg.WorkOrderCount, 0) AS WorkOrders,
    COALESCE(mfg.TotalProduced, 0) AS TotalManufactured,
    COALESCE(mfg.TotalScrapped, 0) AS TotalScrapped,
    COALESCE(ROUND(mfg.ScrapRate, 2), 0) AS MfgScrapPct,
    COALESCE(ROUND(mfg.TotalMfgCost, 2), 0) AS TotalMfgCost,

    -- INVENTORY
    COALESCE(inv.CurrentStock, 0) AS CurrentInventory,

    -- SALES
    COALESCE(sales.OrderCount, 0) AS SalesOrders,
    COALESCE(sales.TotalUnitsSold, 0) AS UnitsSold,
    COALESCE(ROUND(sales.TotalRevenue, 2), 0) AS TotalRevenue,
    COALESCE(ROUND(sales.AvgSellingPrice, 2), 0) AS AvgSellingPrice,

    -- MARGIN
    ROUND(
        COALESCE(sales.TotalRevenue, 0)
        - COALESCE(purch.TotalPurchaseCost, 0)
        - COALESCE(mfg.TotalMfgCost, 0), 2
    ) AS EstimatedGrossProfit

FROM Product p
LEFT JOIN ProductSubcategory psub ON p.ProductSubcategoryID = psub.ProductSubcategoryID
LEFT JOIN ProductCategory pcat ON psub.ProductCategoryID = pcat.ProductCategoryID

LEFT JOIN (
    SELECT pod.ProductID,
        COUNT(DISTINCT poh.VendorID) AS VendorCount,
        SUM(pod.LineTotal) AS TotalPurchaseCost,
        AVG(pod.UnitPrice) AS AvgPurchasePrice,
        SUM(pod.RejectedQty) * 100.0 / NULLIF(SUM(pod.ReceivedQty), 0) AS RejectionRate
    FROM PurchaseOrderDetail pod
    JOIN PurchaseOrderHeader poh ON pod.PurchaseOrderID = poh.PurchaseOrderID
    GROUP BY pod.ProductID
) purch ON p.ProductID = purch.ProductID

LEFT JOIN (
    SELECT wo.ProductID,
        COUNT(*) AS WorkOrderCount,
        SUM(wo.StockedQty) AS TotalProduced,
        SUM(wo.ScrappedQty) AS TotalScrapped,
        SUM(wo.ScrappedQty) * 100.0 / NULLIF(SUM(wo.OrderQty), 0) AS ScrapRate,
        SUM(wor.ActualCost) AS TotalMfgCost
    FROM WorkOrder wo
    LEFT JOIN WorkOrderRouting wor ON wo.WorkOrderID = wor.WorkOrderID
    GROUP BY wo.ProductID
) mfg ON p.ProductID = mfg.ProductID

LEFT JOIN (
    SELECT ProductID, SUM(Quantity) AS CurrentStock
    FROM ProductInventory GROUP BY ProductID
) inv ON p.ProductID = inv.ProductID

LEFT JOIN (
    SELECT ProductID,
        COUNT(DISTINCT SalesOrderID) AS OrderCount,
        SUM(OrderQty) AS TotalUnitsSold,
        SUM(LineTotal) AS TotalRevenue,
        AVG(UnitPrice * (1 - UnitPriceDiscount)) AS AvgSellingPrice
    FROM SalesOrderDetail GROUP BY ProductID
) sales ON p.ProductID = sales.ProductID

WHERE p.SellEndDate IS NULL
ORDER BY EstimatedGrossProfit DESC;
```

---

## Q10: "Monthly Business Trend — Sales Revenue, Procurement Spend, Manufacturing Output, and New Customers Over Time"

*Use case: Board meeting — long-term business trend analysis*

*8 joins*

```sql
WITH Months AS (
    SELECT DISTINCT strftime('%Y-%m', OrderDate) AS Month FROM SalesOrderHeader
),
MonthlySales AS (
    SELECT
        strftime('%Y-%m', soh.OrderDate) AS Month,
        COUNT(DISTINCT soh.SalesOrderID) AS SalesOrders,
        ROUND(SUM(soh.TotalDue), 2) AS SalesRevenue,
        COUNT(DISTINCT soh.CustomerID) AS ActiveCustomers,
        ROUND(SUM(soh.Freight), 2) AS TotalFreight
    FROM SalesOrderHeader soh
    GROUP BY strftime('%Y-%m', soh.OrderDate)
),
MonthlyProcurement AS (
    SELECT
        strftime('%Y-%m', poh.OrderDate) AS Month,
        COUNT(DISTINCT poh.PurchaseOrderID) AS PurchaseOrders,
        ROUND(SUM(poh.TotalDue), 2) AS ProcurementSpend
    FROM PurchaseOrderHeader poh
    GROUP BY strftime('%Y-%m', poh.OrderDate)
),
MonthlyManufacturing AS (
    SELECT
        strftime('%Y-%m', wo.StartDate) AS Month,
        COUNT(*) AS WorkOrders,
        SUM(wo.StockedQty) AS UnitsProduced,
        SUM(wo.ScrappedQty) AS UnitsScrapped,
        ROUND(SUM(wo.ScrappedQty) * 100.0 / NULLIF(SUM(wo.OrderQty), 0), 2) AS ScrapRatePct
    FROM WorkOrder wo
    GROUP BY strftime('%Y-%m', wo.StartDate)
),
MonthlyNewCustomers AS (
    SELECT
        strftime('%Y-%m', MIN(soh.OrderDate)) AS Month,
        COUNT(*) AS NewCustomers
    FROM SalesOrderHeader soh
    GROUP BY soh.CustomerID
)
SELECT
    m.Month,
    COALESCE(s.SalesOrders, 0) AS SalesOrders,
    COALESCE(s.SalesRevenue, 0) AS SalesRevenue,
    COALESCE(s.ActiveCustomers, 0) AS ActiveCustomers,
    COALESCE(nc.NewCustomers, 0) AS NewCustomers,
    COALESCE(p.PurchaseOrders, 0) AS PurchaseOrders,
    COALESCE(p.ProcurementSpend, 0) AS ProcurementSpend,
    COALESCE(ROUND(s.SalesRevenue - p.ProcurementSpend, 2), 0) AS NetSalesVsProcurement,
    COALESCE(mfg.WorkOrders, 0) AS WorkOrders,
    COALESCE(mfg.UnitsProduced, 0) AS UnitsManufactured,
    COALESCE(mfg.ScrapRatePct, 0) AS MfgScrapRatePct,
    COALESCE(s.TotalFreight, 0) AS FreightCost
FROM Months m
LEFT JOIN MonthlySales s ON m.Month = s.Month
LEFT JOIN MonthlyProcurement p ON m.Month = p.Month
LEFT JOIN MonthlyManufacturing mfg ON m.Month = mfg.Month
LEFT JOIN (
    SELECT Month, SUM(NewCustomers) AS NewCustomers
    FROM MonthlyNewCustomers GROUP BY Month
) nc ON m.Month = nc.Month
ORDER BY m.Month;
```

---

## Summary

| # | Query | Domains Covered | Use Case |
|---|-------|----------------|----------|
| Q1 | Executive Dashboard KPIs | Sales + Procurement + Manufacturing | CEO/COO morning briefing |
| Q2 | Revenue by Territory/Category/Channel | Sales + Product | VP Sales quarterly review |
| Q3 | Salesperson Scorecard | Sales + HR | Sales manager weekly review |
| Q4 | Product Profitability | Purchasing + Manufacturing + Sales + Product | Finance P&L analysis |
| Q5 | Inventory Health Check | Product + Inventory + Sales | Warehouse daily review |
| Q6 | Vendor Scorecard | Purchasing + Vendor + Geography | Procurement quarterly review |
| Q7 | Customer Lifetime Value | Sales + Customer + Geography | Marketing CRM targeting |
| Q8 | HR Workforce Overview | HR + Employee + Department | HR monthly report |
| Q9 | End-to-End Value Chain | ALL domains (Purchase → Manufacture → Inventory → Sell) | COO supply chain visibility |
| Q10 | Monthly Business Trend | Sales + Procurement + Manufacturing | Board meeting trend analysis |

---
