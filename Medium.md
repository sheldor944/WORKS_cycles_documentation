# 🟡 10 Medium Complexity Business Queries

---

**Q1: "What is the month-over-month sales revenue growth rate?"**

```sql
WITH MonthlySales AS (
    SELECT
        strftime('%Y-%m', OrderDate) AS Month,
        ROUND(SUM(TotalDue), 2) AS Revenue
    FROM SalesOrderHeader
    GROUP BY strftime('%Y-%m', OrderDate)
)
SELECT
    Month,
    Revenue,
    LAG(Revenue) OVER (ORDER BY Month) AS PrevMonthRevenue,
    ROUND(Revenue - LAG(Revenue) OVER (ORDER BY Month), 2) AS RevenueChange,
    ROUND((Revenue - LAG(Revenue) OVER (ORDER BY Month)) * 100.0
        / NULLIF(LAG(Revenue) OVER (ORDER BY Month), 0), 2) AS GrowthPct
FROM MonthlySales
ORDER BY Month;
```

---

**Q2: "Which products are frequently bought together on the same order?"**

```sql
SELECT
    p1.Name AS Product1,
    p2.Name AS Product2,
    COUNT(DISTINCT sod1.SalesOrderID) AS TimesBoughtTogether
FROM SalesOrderDetail sod1
JOIN SalesOrderDetail sod2
    ON sod1.SalesOrderID = sod2.SalesOrderID
    AND sod1.ProductID < sod2.ProductID
JOIN Product p1 ON sod1.ProductID = p1.ProductID
JOIN Product p2 ON sod2.ProductID = p2.ProductID
GROUP BY p1.Name, p2.Name
HAVING COUNT(DISTINCT sod1.SalesOrderID) > 50
ORDER BY TimesBoughtTogether DESC
LIMIT 20;
```

---

**Q3: "For each salesperson, what percentage of their total revenue comes from online vs. sales-rep orders?"**

```sql
SELECT
    p.FirstName || ' ' || p.LastName AS SalesPersonName,
    COUNT(DISTINCT soh.SalesOrderID) AS TotalOrders,
    ROUND(SUM(soh.TotalDue), 2) AS TotalRevenue,
    ROUND(SUM(CASE WHEN soh.OnlineOrderFlag = 1 THEN soh.TotalDue ELSE 0 END) * 100.0
        / NULLIF(SUM(soh.TotalDue), 0), 2) AS OnlineRevenuePct,
    ROUND(SUM(CASE WHEN soh.OnlineOrderFlag = 0 THEN soh.TotalDue ELSE 0 END) * 100.0
        / NULLIF(SUM(soh.TotalDue), 0), 2) AS RepRevenuePct
FROM SalesOrderHeader soh
JOIN SalesPerson sp ON soh.SalesPersonID = sp.BusinessEntityID
JOIN Person p ON sp.BusinessEntityID = p.BusinessEntityID
GROUP BY p.FirstName, p.LastName
ORDER BY TotalRevenue DESC;
```

---

**Q4: "Which vendors have the longest average lead time, and how does it correlate with their rejection rate?"**

```sql
SELECT
    v.Name AS VendorName,
    v.CreditRating,
    ROUND(AVG(pv.AverageLeadTime), 0) AS AvgLeadTimeDays,
    COUNT(DISTINCT poh.PurchaseOrderID) AS TotalPOs,
    SUM(pod.ReceivedQty) AS TotalReceived,
    SUM(pod.RejectedQty) AS TotalRejected,
    ROUND(SUM(pod.RejectedQty) * 100.0 / NULLIF(SUM(pod.ReceivedQty), 0), 2) AS RejectionRatePct,
    CASE
        WHEN AVG(pv.AverageLeadTime) > 30 AND SUM(pod.RejectedQty) * 100.0 / NULLIF(SUM(pod.ReceivedQty), 0) > 3
        THEN 'Slow + Poor Quality'
        WHEN AVG(pv.AverageLeadTime) > 30
        THEN 'Slow but Good Quality'
        WHEN SUM(pod.RejectedQty) * 100.0 / NULLIF(SUM(pod.ReceivedQty), 0) > 3
        THEN 'Fast but Poor Quality'
        ELSE 'Good'
    END AS VendorAssessment
FROM Vendor v
JOIN ProductVendor pv ON v.BusinessEntityID = pv.BusinessEntityID
JOIN PurchaseOrderHeader poh ON v.BusinessEntityID = poh.VendorID
JOIN PurchaseOrderDetail pod ON poh.PurchaseOrderID = pod.PurchaseOrderID
GROUP BY v.Name, v.CreditRating
ORDER BY AvgLeadTimeDays DESC;
```

---

**Q5: "Rank the product subcategories by revenue and show each one's percentage of its parent category's total."**

```sql
SELECT
    pcat.Name AS Category,
    psub.Name AS Subcategory,
    SUM(sod.OrderQty) AS UnitsSold,
    ROUND(SUM(sod.LineTotal), 2) AS Revenue,
    ROUND(SUM(sod.LineTotal) * 100.0 /
        SUM(SUM(sod.LineTotal)) OVER (PARTITION BY pcat.Name), 2) AS PctOfCategory,
    RANK() OVER (PARTITION BY pcat.Name ORDER BY SUM(sod.LineTotal) DESC) AS RankInCategory
FROM SalesOrderDetail sod
JOIN Product p ON sod.ProductID = p.ProductID
JOIN ProductSubcategory psub ON p.ProductSubcategoryID = psub.ProductSubcategoryID
JOIN ProductCategory pcat ON psub.ProductCategoryID = pcat.ProductCategoryID
GROUP BY pcat.Name, psub.Name
ORDER BY pcat.Name, Revenue DESC;
```

---

**Q6: "Which employees have received the most pay raises, and what was their total pay increase over time?"**

```sql
SELECT
    p.FirstName || ' ' || p.LastName AS EmployeeName,
    e.JobTitle,
    COUNT(*) AS PayChanges,
    ROUND(MIN(eph.Rate), 2) AS StartingRate,
    ROUND(MAX(eph.Rate), 2) AS CurrentRate,
    ROUND(MAX(eph.Rate) - MIN(eph.Rate), 2) AS TotalRateIncrease,
    ROUND((MAX(eph.Rate) - MIN(eph.Rate)) * 100.0 / NULLIF(MIN(eph.Rate), 0), 2) AS TotalIncreasePct,
    MIN(eph.RateChangeDate) AS FirstPayDate,
    MAX(eph.RateChangeDate) AS LastPayDate
FROM EmployeePayHistory eph
JOIN Employee e ON eph.BusinessEntityID = e.BusinessEntityID
JOIN Person p ON e.BusinessEntityID = p.BusinessEntityID
WHERE e.CurrentFlag = 1
GROUP BY p.FirstName, p.LastName, e.JobTitle
HAVING COUNT(*) > 1
ORDER BY TotalRateIncrease DESC
LIMIT 15;
```

---

**Q7: "What's the average time to ship an order by territory, and which territories are slowest?"**

```sql
SELECT
    st.Name AS Territory,
    st."Group" AS Region,
    COUNT(*) AS ShippedOrders,
    ROUND(AVG(JULIANDAY(soh.ShipDate) - JULIANDAY(soh.OrderDate)), 1) AS AvgDaysToShip,
    MIN(CAST(JULIANDAY(soh.ShipDate) - JULIANDAY(soh.OrderDate) AS INTEGER)) AS FastestDays,
    MAX(CAST(JULIANDAY(soh.ShipDate) - JULIANDAY(soh.OrderDate) AS INTEGER)) AS SlowestDays,
    SUM(CASE
        WHEN JULIANDAY(soh.ShipDate) - JULIANDAY(soh.OrderDate) > 7 THEN 1 ELSE 0
    END) AS OrdersOver7Days,
    ROUND(SUM(soh.Freight), 2) AS TotalFreight
FROM SalesOrderHeader soh
JOIN SalesTerritory st ON soh.TerritoryID = st.TerritoryID
WHERE soh.ShipDate IS NOT NULL
GROUP BY st.Name, st."Group"
ORDER BY AvgDaysToShip DESC;
```

---

**Q8: "For each product category, compare total procurement spend vs. total sales revenue — where are we making or losing money?"**

```sql
SELECT
    pcat.Name AS Category,
    COALESCE(ROUND(purch.TotalPurchaseCost, 2), 0) AS TotalPurchaseCost,
    COALESCE(ROUND(sales.TotalSalesRevenue, 2), 0) AS TotalSalesRevenue,
    ROUND(COALESCE(sales.TotalSalesRevenue, 0) - COALESCE(purch.TotalPurchaseCost, 0), 2) AS NetMargin,
    CASE
        WHEN COALESCE(sales.TotalSalesRevenue, 0) > COALESCE(purch.TotalPurchaseCost, 0) THEN 'Profitable'
        ELSE 'Unprofitable'
    END AS Status
FROM ProductCategory pcat
LEFT JOIN ProductSubcategory psub ON pcat.ProductCategoryID = psub.ProductCategoryID
LEFT JOIN Product p ON psub.ProductSubcategoryID = p.ProductSubcategoryID
LEFT JOIN (
    SELECT pod.ProductID, SUM(pod.LineTotal) AS TotalPurchaseCost
    FROM PurchaseOrderDetail pod
    GROUP BY pod.ProductID
) purch ON p.ProductID = purch.ProductID
LEFT JOIN (
    SELECT sod.ProductID, SUM(sod.LineTotal) AS TotalSalesRevenue
    FROM SalesOrderDetail sod
    GROUP BY sod.ProductID
) sales ON p.ProductID = sales.ProductID
GROUP BY pcat.Name
ORDER BY NetMargin DESC;
```

---

**Q9: "Which customers have been placing orders of declining value — potential churn risk?"**

```sql
WITH CustomerYearly AS (
    SELECT
        soh.CustomerID,
        strftime('%Y', soh.OrderDate) AS OrderYear,
        COUNT(*) AS Orders,
        ROUND(AVG(soh.TotalDue), 2) AS AvgOrderValue,
        ROUND(SUM(soh.TotalDue), 2) AS TotalRevenue
    FROM SalesOrderHeader soh
    GROUP BY soh.CustomerID, strftime('%Y', soh.OrderDate)
)
SELECT
    cur.CustomerID,
    COALESCE(p.FirstName || ' ' || p.LastName, s.Name) AS CustomerName,
    prev.OrderYear AS PreviousYear,
    prev.AvgOrderValue AS PrevYearAOV,
    cur.OrderYear AS CurrentYear,
    cur.AvgOrderValue AS CurrYearAOV,
    ROUND(cur.AvgOrderValue - prev.AvgOrderValue, 2) AS AOVChange,
    ROUND((cur.AvgOrderValue - prev.AvgOrderValue) * 100.0
        / NULLIF(prev.AvgOrderValue, 0), 2) AS AOVChangePct
FROM CustomerYearly cur
JOIN CustomerYearly prev
    ON cur.CustomerID = prev.CustomerID
    AND CAST(cur.OrderYear AS INTEGER) = CAST(prev.OrderYear AS INTEGER) + 1
JOIN Customer c ON cur.CustomerID = c.CustomerID
LEFT JOIN Person p ON c.PersonID = p.BusinessEntityID
LEFT JOIN Store s ON c.StoreID = s.BusinessEntityID
WHERE cur.AvgOrderValue < prev.AvgOrderValue
ORDER BY AOVChangePct ASC
LIMIT 20;
```

---

**Q10: "What's the manufacturing scrap cost impact — how much money are we losing to scrap by product and reason?"**

```sql
SELECT
    p.Name AS ProductName,
    pcat.Name AS Category,
    sr.Name AS ScrapReason,
    COUNT(*) AS AffectedWorkOrders,
    SUM(wo.ScrappedQty) AS TotalUnitsScrapped,
    ROUND(SUM(wo.ScrappedQty * p.StandardCost), 2) AS EstimatedScrapCost,
    ROUND(SUM(wo.ScrappedQty) * 100.0 / NULLIF(SUM(wo.OrderQty), 0), 2) AS ScrapRatePct,
    RANK() OVER (ORDER BY SUM(wo.ScrappedQty * p.StandardCost) DESC) AS CostImpactRank
FROM WorkOrder wo
JOIN Product p ON wo.ProductID = p.ProductID
LEFT JOIN ProductSubcategory psub ON p.ProductSubcategoryID = psub.ProductSubcategoryID
LEFT JOIN ProductCategory pcat ON psub.ProductCategoryID = pcat.ProductCategoryID
JOIN ScrapReason sr ON wo.ScrapReasonID = sr.ScrapReasonID
WHERE wo.ScrappedQty > 0
GROUP BY p.Name, pcat.Name, sr.Name
ORDER BY EstimatedScrapCost DESC
LIMIT 20;
```


---



**Q11: "What is each territory's contribution to total company revenue — with running cumulative percentage?"**

```sql
WITH TerritoryRevenue AS (
    SELECT
        st.Name AS Territory,
        st."Group" AS Region,
        ROUND(SUM(soh.TotalDue), 2) AS Revenue
    FROM SalesOrderHeader soh
    JOIN SalesTerritory st ON soh.TerritoryID = st.TerritoryID
    GROUP BY st.Name, st."Group"
)
SELECT
    Territory,
    Region,
    Revenue,
    ROUND(Revenue * 100.0 / SUM(Revenue) OVER (), 2) AS PctOfTotal,
    ROUND(SUM(Revenue) OVER (ORDER BY Revenue DESC) * 100.0
        / SUM(Revenue) OVER (), 2) AS CumulativePct
FROM TerritoryRevenue
ORDER BY Revenue DESC;
```

---

**Q12: "Which products have had the biggest price increase from their original list price to now?"**

```sql
WITH PriceHistory AS (
    SELECT
        ProductID,
        MIN(StartDate) AS FirstDate,
        ListPrice AS Price,
        ROW_NUMBER() OVER (PARTITION BY ProductID ORDER BY StartDate ASC) AS FirstRow,
        ROW_NUMBER() OVER (PARTITION BY ProductID ORDER BY StartDate DESC) AS LastRow
    FROM ProductListPriceHistory
)
SELECT
    p.Name AS ProductName,
    first_price.Price AS OriginalPrice,
    last_price.Price AS CurrentPrice,
    ROUND(last_price.Price - first_price.Price, 2) AS PriceIncrease,
    ROUND((last_price.Price - first_price.Price) * 100.0
        / NULLIF(first_price.Price, 0), 2) AS PriceIncreasePct
FROM Product p
JOIN PriceHistory first_price ON p.ProductID = first_price.ProductID AND first_price.FirstRow = 1
JOIN PriceHistory last_price ON p.ProductID = last_price.ProductID AND last_price.LastRow = 1
WHERE last_price.Price > first_price.Price
ORDER BY PriceIncreasePct DESC
LIMIT 15;
```

---

**Q13: "How many employees have changed departments, and who has moved the most?"**

```sql
SELECT
    p.FirstName || ' ' || p.LastName AS EmployeeName,
    e.JobTitle,
    COUNT(*) AS DepartmentChanges,
    GROUP_CONCAT(d.Name, ' → ') AS DepartmentPath,
    MIN(edh.StartDate) AS FirstDeptDate,
    MAX(edh.StartDate) AS LatestDeptDate
FROM EmployeeDepartmentHistory edh
JOIN Employee e ON edh.BusinessEntityID = e.BusinessEntityID
JOIN Person p ON e.BusinessEntityID = p.BusinessEntityID
JOIN Department d ON edh.DepartmentID = d.DepartmentID
WHERE e.CurrentFlag = 1
GROUP BY p.FirstName, p.LastName, e.JobTitle
HAVING COUNT(*) > 1
ORDER BY DepartmentChanges DESC;
```

---

**Q14: "What's the seasonal sales pattern — which months consistently perform best across all years?"**

```sql
SELECT
    CAST(strftime('%m', OrderDate) AS INTEGER) AS MonthNum,
    CASE CAST(strftime('%m', OrderDate) AS INTEGER)
        WHEN 1 THEN 'January' WHEN 2 THEN 'February' WHEN 3 THEN 'March'
        WHEN 4 THEN 'April' WHEN 5 THEN 'May' WHEN 6 THEN 'June'
        WHEN 7 THEN 'July' WHEN 8 THEN 'August' WHEN 9 THEN 'September'
        WHEN 10 THEN 'October' WHEN 11 THEN 'November' WHEN 12 THEN 'December'
    END AS MonthName,
    COUNT(DISTINCT strftime('%Y', OrderDate)) AS YearsOfData,
    COUNT(*) AS TotalOrders,
    ROUND(SUM(TotalDue), 2) AS TotalRevenue,
    ROUND(AVG(TotalDue), 2) AS AvgOrderValue,
    ROUND(SUM(TotalDue) / COUNT(DISTINCT strftime('%Y', OrderDate)), 2) AS AvgRevenuePerYear
FROM SalesOrderHeader
GROUP BY MonthNum
ORDER BY AvgRevenuePerYear DESC;
```

---

**Q15: "For each product, how many days of inventory do we have left based on last 90 days sales velocity?"**

```sql
SELECT
    p.Name AS ProductName,
    pcat.Name AS Category,
    COALESCE(inv.TotalStock, 0) AS CurrentStock,
    COALESCE(sales.Last90DaysQty, 0) AS SoldLast90Days,
    CASE
        WHEN COALESCE(sales.Last90DaysQty, 0) = 0 THEN 'No Recent Sales'
        ELSE CAST(ROUND(COALESCE(inv.TotalStock, 0) * 90.0
            / sales.Last90DaysQty, 0) AS TEXT) || ' days'
    END AS EstDaysOfInventory,
    CASE
        WHEN COALESCE(inv.TotalStock, 0) = 0 THEN 'OUT OF STOCK'
        WHEN COALESCE(sales.Last90DaysQty, 0) = 0 THEN 'NO SALES — DEAD STOCK?'
        WHEN COALESCE(inv.TotalStock, 0) * 90.0 / sales.Last90DaysQty < 30 THEN 'CRITICAL (<30 days)'
        WHEN COALESCE(inv.TotalStock, 0) * 90.0 / sales.Last90DaysQty < 60 THEN 'LOW (30-60 days)'
        ELSE 'OK'
    END AS InventoryAlert
FROM Product p
LEFT JOIN ProductSubcategory psub ON p.ProductSubcategoryID = psub.ProductSubcategoryID
LEFT JOIN ProductCategory pcat ON psub.ProductCategoryID = pcat.ProductCategoryID
LEFT JOIN (
    SELECT ProductID, SUM(Quantity) AS TotalStock
    FROM ProductInventory GROUP BY ProductID
) inv ON p.ProductID = inv.ProductID
LEFT JOIN (
    SELECT sod.ProductID, SUM(sod.OrderQty) AS Last90DaysQty
    FROM SalesOrderDetail sod
    JOIN SalesOrderHeader soh ON sod.SalesOrderID = soh.SalesOrderID
    WHERE soh.OrderDate >= DATE('now', '-90 days')
    GROUP BY sod.ProductID
) sales ON p.ProductID = sales.ProductID
WHERE p.FinishedGoodsFlag = 1 AND p.SellEndDate IS NULL
ORDER BY
    CASE
        WHEN COALESCE(inv.TotalStock, 0) = 0 THEN 0
        WHEN COALESCE(sales.Last90DaysQty, 0) = 0 THEN 9999
        ELSE COALESCE(inv.TotalStock, 0) * 90.0 / sales.Last90DaysQty
    END ASC;
```

---

**Q16: "What percentage of revenue comes from repeat customers vs. one-time buyers?"**

```sql
WITH CustomerOrders AS (
    SELECT
        CustomerID,
        COUNT(*) AS OrderCount,
        ROUND(SUM(TotalDue), 2) AS TotalSpent
    FROM SalesOrderHeader
    GROUP BY CustomerID
)
SELECT
    CASE
        WHEN OrderCount = 1 THEN 'One-Time Buyer'
        WHEN OrderCount BETWEEN 2 AND 5 THEN 'Repeat (2-5 orders)'
        WHEN OrderCount BETWEEN 6 AND 10 THEN 'Loyal (6-10 orders)'
        ELSE 'VIP (10+ orders)'
    END AS CustomerSegment,
    COUNT(*) AS CustomerCount,
    ROUND(SUM(TotalSpent), 2) AS SegmentRevenue,
    ROUND(SUM(TotalSpent) * 100.0 / (SELECT SUM(TotalDue) FROM SalesOrderHeader), 2) AS PctOfTotalRevenue,
    ROUND(AVG(TotalSpent), 2) AS AvgCustomerValue
FROM CustomerOrders
GROUP BY CustomerSegment
ORDER BY SegmentRevenue DESC;
```

---

**Q17: "Which manufacturing locations are being used the most, and which have the highest cost per hour?"**

```sql
SELECT
    loc.Name AS LocationName,
    loc.CostRate,
    loc.Availability,
    COUNT(*) AS OperationsRun,
    COUNT(DISTINCT wor.WorkOrderID) AS UniqueWorkOrders,
    ROUND(SUM(wor.ActualResourceHrs), 1) AS TotalHoursUsed,
    ROUND(SUM(wor.ActualCost), 2) AS TotalCost,
    ROUND(SUM(wor.ActualCost) / NULLIF(SUM(wor.ActualResourceHrs), 0), 2) AS CostPerHour,
    ROUND(SUM(wor.ActualCost) - SUM(wor.PlannedCost), 2) AS CostVariance,
    CASE
        WHEN SUM(wor.ActualCost) > SUM(wor.PlannedCost) THEN 'Over Budget'
        ELSE 'On/Under Budget'
    END AS BudgetStatus
FROM WorkOrderRouting wor
JOIN Location loc ON wor.LocationID = loc.LocationID
WHERE wor.ActualCost IS NOT NULL
GROUP BY loc.LocationID, loc.Name, loc.CostRate, loc.Availability
ORDER BY TotalHoursUsed DESC;
```

---

**Q18: "What's the discount effectiveness — do higher discounts actually lead to higher order quantities?"**

```sql
SELECT
    CASE
        WHEN UnitPriceDiscount = 0 THEN 'No Discount'
        WHEN UnitPriceDiscount <= 0.05 THEN '1-5%'
        WHEN UnitPriceDiscount <= 0.10 THEN '6-10%'
        WHEN UnitPriceDiscount <= 0.20 THEN '11-20%'
        ELSE '20%+'
    END AS DiscountBand,
    COUNT(*) AS LineItems,
    COUNT(DISTINCT SalesOrderID) AS Orders,
    ROUND(AVG(OrderQty), 1) AS AvgQtyPerLine,
    ROUND(AVG(UnitPrice), 2) AS AvgUnitPrice,
    ROUND(SUM(LineTotal), 2) AS TotalRevenue,
    ROUND(SUM(UnitPrice * OrderQty) - SUM(LineTotal), 2) AS TotalDiscountGiven,
    ROUND(AVG(LineTotal), 2) AS AvgLineValue
FROM SalesOrderDetail
GROUP BY DiscountBand
ORDER BY MIN(UnitPriceDiscount);
```

---

**Q19: "Which stores haven't placed an order in the last 6 months — are they going dormant?"**

```sql
SELECT
    s.Name AS StoreName,
    sp_person.FirstName || ' ' || sp_person.LastName AS AssignedSalesPerson,
    MAX(soh.OrderDate) AS LastOrderDate,
    CAST(JULIANDAY('now') - JULIANDAY(MAX(soh.OrderDate)) AS INTEGER) AS DaysSinceLastOrder,
    COUNT(DISTINCT soh.SalesOrderID) AS LifetimeOrders,
    ROUND(SUM(soh.TotalDue), 2) AS LifetimeRevenue,
    CASE
        WHEN MAX(soh.OrderDate) IS NULL THEN 'NEVER ORDERED'
        WHEN JULIANDAY('now') - JULIANDAY(MAX(soh.OrderDate)) > 365 THEN 'LAPSED (>1 year)'
        WHEN JULIANDAY('now') - JULIANDAY(MAX(soh.OrderDate)) > 180 THEN 'DORMANT (6-12 months)'
        ELSE 'ACTIVE'
    END AS StoreStatus
FROM Store s
LEFT JOIN SalesPerson salp ON s.SalesPersonID = salp.BusinessEntityID
LEFT JOIN Person sp_person ON salp.BusinessEntityID = sp_person.BusinessEntityID
LEFT JOIN Customer c ON s.BusinessEntityID = c.StoreID
LEFT JOIN SalesOrderHeader soh ON c.CustomerID = soh.CustomerID
GROUP BY s.Name, sp_person.FirstName, sp_person.LastName
HAVING StoreStatus IN ('DORMANT (6-12 months)', 'LAPSED (>1 year)', 'NEVER ORDERED')
ORDER BY DaysSinceLastOrder DESC;
```

---

**Q20: "What's the bill of materials depth — how many levels deep is each product's component tree, and how many total components does it need?"**

```sql
WITH RECURSIVE BOMTree AS (
    -- Anchor: top-level assemblies
    SELECT
        bom.ProductAssemblyID AS TopProductID,
        bom.ComponentID,
        bom.PerAssemblyQty,
        bom.BOMLevel,
        1 AS Depth
    FROM BillOfMaterials bom
    WHERE bom.ProductAssemblyID IS NOT NULL
        AND bom.EndDate IS NULL

    UNION ALL

    -- Recursive: dig into sub-components
    SELECT
        bt.TopProductID,
        bom.ComponentID,
        bom.PerAssemblyQty * bt.PerAssemblyQty,
        bom.BOMLevel,
        bt.Depth + 1
    FROM BOMTree bt
    JOIN BillOfMaterials bom ON bt.ComponentID = bom.ProductAssemblyID
        AND bom.EndDate IS NULL
    WHERE bt.Depth < 10
)
SELECT
    p.Name AS AssemblyProduct,
    COUNT(DISTINCT bt.ComponentID) AS UniqueComponents,
    MAX(bt.Depth) AS MaxDepth,
    ROUND(SUM(bt.PerAssemblyQty), 2) AS TotalComponentQtyNeeded,
    p.ListPrice,
    p.StandardCost
FROM BOMTree bt
JOIN Product p ON bt.TopProductID = p.ProductID
GROUP BY bt.TopProductID, p.Name, p.ListPrice, p.StandardCost
ORDER BY UniqueComponents DESC
LIMIT 15;
```

---

**Q21: "What is the average markup (ListPrice vs. StandardCost) by product category, and which categories have the thinnest margins?"**

```sql
SELECT
    pcat.Name AS Category,
    COUNT(*) AS ProductCount,
    ROUND(AVG(p.StandardCost), 2) AS AvgCost,
    ROUND(AVG(p.ListPrice), 2) AS AvgListPrice,
    ROUND(AVG(p.ListPrice - p.StandardCost), 2) AS AvgMarkup,
    ROUND(AVG((p.ListPrice - p.StandardCost) * 100.0
        / NULLIF(p.ListPrice, 0)), 2) AS AvgMarkupPct,
    ROUND(MIN((p.ListPrice - p.StandardCost) * 100.0
        / NULLIF(p.ListPrice, 0)), 2) AS ThinnestMarginPct,
    RANK() OVER (ORDER BY AVG((p.ListPrice - p.StandardCost) * 100.0
        / NULLIF(p.ListPrice, 0)) ASC) AS MarginRank
FROM Product p
JOIN ProductSubcategory psub ON p.ProductSubcategoryID = psub.ProductSubcategoryID
JOIN ProductCategory pcat ON psub.ProductCategoryID = pcat.ProductCategoryID
WHERE p.ListPrice > 0
GROUP BY pcat.Name
ORDER BY AvgMarkupPct ASC;
```

---

**Q22: "How does each salesperson's current year performance compare to last year — who's improving and who's declining?"**

```sql
WITH SalesPersonYearly AS (
    SELECT
        soh.SalesPersonID,
        strftime('%Y', soh.OrderDate) AS SalesYear,
        COUNT(DISTINCT soh.SalesOrderID) AS Orders,
        ROUND(SUM(soh.TotalDue), 2) AS Revenue
    FROM SalesOrderHeader soh
    WHERE soh.SalesPersonID IS NOT NULL
    GROUP BY soh.SalesPersonID, strftime('%Y', soh.OrderDate)
)
SELECT
    p.FirstName || ' ' || p.LastName AS SalesPersonName,
    cur.SalesYear AS CurrentYear,
    cur.Orders AS CurrYearOrders,
    cur.Revenue AS CurrYearRevenue,
    prev.Orders AS PrevYearOrders,
    prev.Revenue AS PrevYearRevenue,
    ROUND(cur.Revenue - prev.Revenue, 2) AS RevenueChange,
    ROUND((cur.Revenue - prev.Revenue) * 100.0
        / NULLIF(prev.Revenue, 0), 2) AS RevenueChangePct,
    CASE
        WHEN cur.Revenue > prev.Revenue THEN '📈 Improving'
        WHEN cur.Revenue < prev.Revenue THEN '📉 Declining'
        ELSE '➡️ Flat'
    END AS Trend
FROM SalesPersonYearly cur
JOIN SalesPersonYearly prev
    ON cur.SalesPersonID = prev.SalesPersonID
    AND CAST(cur.SalesYear AS INTEGER) = CAST(prev.SalesYear AS INTEGER) + 1
JOIN Person p ON cur.SalesPersonID = p.BusinessEntityID
ORDER BY RevenueChangePct DESC;
```

---

**Q23: "Which products have never been sold — dead catalog items?"**

```sql
SELECT
    p.Name AS ProductName,
    p.ProductNumber,
    pcat.Name AS Category,
    p.ListPrice,
    p.StandardCost,
    p.SellStartDate,
    p.SellEndDate,
    CASE WHEN p.DiscontinuedDate IS NOT NULL THEN 'Discontinued' 
         WHEN p.SellEndDate IS NOT NULL THEN 'Retired'
         ELSE 'Active'
    END AS ProductStatus,
    COALESCE(inv.TotalStock, 0) AS CurrentInventory,
    CASE WHEN p.MakeFlag = 1 THEN 'Manufactured' ELSE 'Purchased' END AS SourceType
FROM Product p
LEFT JOIN ProductSubcategory psub ON p.ProductSubcategoryID = psub.ProductSubcategoryID
LEFT JOIN ProductCategory pcat ON psub.ProductCategoryID = pcat.ProductCategoryID
LEFT JOIN SalesOrderDetail sod ON p.ProductID = sod.ProductID
LEFT JOIN (
    SELECT ProductID, SUM(Quantity) AS TotalStock
    FROM ProductInventory GROUP BY ProductID
) inv ON p.ProductID = inv.ProductID
WHERE sod.ProductID IS NULL
ORDER BY p.ListPrice DESC;
```

---

**Q24: "What's the ratio of salaried to hourly employees at each organization level, and what's the average pay?"**

```sql
SELECT
    e.OrganizationLevel,
    COUNT(*) AS TotalEmployees,
    SUM(CASE WHEN e.SalariedFlag = 1 THEN 1 ELSE 0 END) AS Salaried,
    SUM(CASE WHEN e.SalariedFlag = 0 THEN 1 ELSE 0 END) AS Hourly,
    ROUND(SUM(CASE WHEN e.SalariedFlag = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS SalariedPct,
    ROUND(AVG(CASE WHEN e.SalariedFlag = 1 THEN eph.Rate END), 2) AS AvgSalariedRate,
    ROUND(AVG(CASE WHEN e.SalariedFlag = 0 THEN eph.Rate END), 2) AS AvgHourlyRate,
    ROUND(AVG(e.VacationHours), 1) AS AvgVacationHrs
FROM Employee e
JOIN EmployeePayHistory eph ON e.BusinessEntityID = eph.BusinessEntityID
    AND eph.RateChangeDate = (
        SELECT MAX(eph2.RateChangeDate)
        FROM EmployeePayHistory eph2
        WHERE eph2.BusinessEntityID = e.BusinessEntityID
    )
WHERE e.CurrentFlag = 1
GROUP BY e.OrganizationLevel
ORDER BY e.OrganizationLevel;
```

---

**Q25: "For each ship method, what's the average order value, freight cost, and freight as a percentage of the order?"**

```sql
SELECT
    sm.Name AS ShipMethod,
    sm.ShipBase,
    sm.ShipRate,
    COUNT(*) AS OrderCount,
    ROUND(AVG(soh.SubTotal), 2) AS AvgSubTotal,
    ROUND(AVG(soh.Freight), 2) AS AvgFreight,
    ROUND(AVG(soh.Freight * 100.0 / NULLIF(soh.SubTotal, 0)), 2) AS AvgFreightPctOfOrder,
    ROUND(SUM(soh.Freight), 2) AS TotalFreightCollected,
    ROUND(SUM(soh.TotalDue), 2) AS TotalRevenue
FROM SalesOrderHeader soh
JOIN ShipMethod sm ON soh.ShipMethodID = sm.ShipMethodID
GROUP BY sm.Name, sm.ShipBase, sm.ShipRate
ORDER BY TotalRevenue DESC;
```

---

**Q26: "Which purchase orders had the most rejected items, and which vendors were responsible?"**

```sql
SELECT
    poh.PurchaseOrderID,
    poh.OrderDate,
    v.Name AS VendorName,
    v.CreditRating,
    p.Name AS ProductName,
    pod.OrderQty,
    pod.ReceivedQty,
    pod.RejectedQty,
    pod.StockedQty,
    ROUND(pod.RejectedQty * 100.0 / NULLIF(pod.ReceivedQty, 0), 2) AS RejectionPct,
    ROUND(pod.RejectedQty * pod.UnitPrice, 2) AS EstCostOfRejections
FROM PurchaseOrderDetail pod
JOIN PurchaseOrderHeader poh ON pod.PurchaseOrderID = poh.PurchaseOrderID
JOIN Vendor v ON poh.VendorID = v.BusinessEntityID
JOIN Product p ON pod.ProductID = p.ProductID
WHERE pod.RejectedQty > 0
ORDER BY pod.RejectedQty DESC
LIMIT 20;
```

---

**Q27: "What's the year-over-year order count and revenue growth by product category?"**

```sql
WITH CategoryYearly AS (
    SELECT
        pcat.Name AS Category,
        strftime('%Y', soh.OrderDate) AS SalesYear,
        COUNT(DISTINCT soh.SalesOrderID) AS Orders,
        ROUND(SUM(sod.LineTotal), 2) AS Revenue
    FROM SalesOrderDetail sod
    JOIN SalesOrderHeader soh ON sod.SalesOrderID = soh.SalesOrderID
    JOIN Product p ON sod.ProductID = p.ProductID
    JOIN ProductSubcategory psub ON p.ProductSubcategoryID = psub.ProductSubcategoryID
    JOIN ProductCategory pcat ON psub.ProductCategoryID = pcat.ProductCategoryID
    GROUP BY pcat.Name, strftime('%Y', soh.OrderDate)
)
SELECT
    cur.Category,
    cur.SalesYear,
    cur.Orders AS CurrentOrders,
    cur.Revenue AS CurrentRevenue,
    prev.Orders AS PrevYearOrders,
    prev.Revenue AS PrevYearRevenue,
    ROUND(cur.Revenue - prev.Revenue, 2) AS RevenueGrowth,
    ROUND((cur.Revenue - prev.Revenue) * 100.0
        / NULLIF(prev.Revenue, 0), 2) AS GrowthPct
FROM CategoryYearly cur
JOIN CategoryYearly prev
    ON cur.Category = prev.Category
    AND CAST(cur.SalesYear AS INTEGER) = CAST(prev.SalesYear AS INTEGER) + 1
ORDER BY cur.Category, cur.SalesYear;
```

---

**Q28: "How does procurement spending break down by quarter — is there a seasonal purchasing pattern?"**

```sql
SELECT
    strftime('%Y', poh.OrderDate) AS Year,
    CASE
        WHEN CAST(strftime('%m', poh.OrderDate) AS INTEGER) BETWEEN 1 AND 3 THEN 'Q1'
        WHEN CAST(strftime('%m', poh.OrderDate) AS INTEGER) BETWEEN 4 AND 6 THEN 'Q2'
        WHEN CAST(strftime('%m', poh.OrderDate) AS INTEGER) BETWEEN 7 AND 9 THEN 'Q3'
        ELSE 'Q4'
    END AS Quarter,
    COUNT(DISTINCT poh.PurchaseOrderID) AS POCount,
    COUNT(DISTINCT poh.VendorID) AS ActiveVendors,
    ROUND(SUM(poh.TotalDue), 2) AS TotalSpend,
    ROUND(AVG(poh.TotalDue), 2) AS AvgPOValue,
    SUM(pod.OrderQty) AS TotalUnitsOrdered,
    SUM(pod.RejectedQty) AS TotalRejected
FROM PurchaseOrderHeader poh
JOIN PurchaseOrderDetail pod ON poh.PurchaseOrderID = pod.PurchaseOrderID
GROUP BY Year, Quarter
ORDER BY Year, Quarter;
```

---

**Q29: "Which customers order from the most product categories — who are our cross-category buyers?"**

```sql
SELECT
    c.CustomerID,
    COALESCE(p.FirstName || ' ' || p.LastName, s.Name) AS CustomerName,
    CASE WHEN c.StoreID IS NOT NULL THEN 'Store' ELSE 'Individual' END AS CustomerType,
    COUNT(DISTINCT pcat.ProductCategoryID) AS CategoriesBought,
    GROUP_CONCAT(DISTINCT pcat.Name) AS Categories,
    COUNT(DISTINCT soh.SalesOrderID) AS TotalOrders,
    ROUND(SUM(sod.LineTotal), 2) AS TotalRevenue
FROM Customer c
LEFT JOIN Person p ON c.PersonID = p.BusinessEntityID
LEFT JOIN Store s ON c.StoreID = s.BusinessEntityID
JOIN SalesOrderHeader soh ON c.CustomerID = soh.CustomerID
JOIN SalesOrderDetail sod ON soh.SalesOrderID = sod.SalesOrderID
JOIN Product prod ON sod.ProductID = prod.ProductID
LEFT JOIN ProductSubcategory psub ON prod.ProductSubcategoryID = psub.ProductSubcategoryID
LEFT JOIN ProductCategory pcat ON psub.ProductCategoryID = pcat.ProductCategoryID
GROUP BY c.CustomerID, CustomerName, CustomerType
HAVING COUNT(DISTINCT pcat.ProductCategoryID) > 1
ORDER BY CategoriesBought DESC, TotalRevenue DESC
LIMIT 20;
```

---

**Q30: "What's the average manufacturing cycle time by product category, and which categories have the most overdue work orders?"**

```sql
SELECT
    pcat.Name AS Category,
    COUNT(*) AS TotalWorkOrders,
    SUM(CASE WHEN wo.EndDate IS NOT NULL THEN 1 ELSE 0 END) AS Completed,
    SUM(CASE WHEN wo.EndDate IS NULL THEN 1 ELSE 0 END) AS InProgress,
    SUM(CASE WHEN wo.EndDate IS NULL AND wo.DueDate < DATE('now') THEN 1 ELSE 0 END) AS Overdue,
    ROUND(AVG(
        CASE WHEN wo.EndDate IS NOT NULL
        THEN JULIANDAY(wo.EndDate) - JULIANDAY(wo.StartDate)
        END
    ), 1) AS AvgCycleTimeDays,
    ROUND(SUM(wo.ScrappedQty) * 100.0 / NULLIF(SUM(wo.OrderQty), 0), 2) AS ScrapRatePct,
    SUM(wo.StockedQty) AS TotalUnitsProduced,
    ROUND(AVG(p.DaysToManufacture), 1) AS CatalogAvgDaysToMfg
FROM WorkOrder wo
JOIN Product p ON wo.ProductID = p.ProductID
LEFT JOIN ProductSubcategory psub ON p.ProductSubcategoryID = psub.ProductSubcategoryID
LEFT JOIN ProductCategory pcat ON psub.ProductCategoryID = pcat.ProductCategoryID
GROUP BY pcat.Name
ORDER BY Overdue DESC, AvgCycleTimeDays DESC;
```

---
