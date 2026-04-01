

# 🟢 10 Basic Everyday Business Queries

---

**Q1: "How many sales orders were placed this year?"**

```sql
SELECT
    COUNT(*) AS TotalOrders,
    ROUND(SUM(TotalDue), 2) AS TotalRevenue
FROM SalesOrderHeader
WHERE strftime('%Y', OrderDate) = strftime('%Y', 'now');
```

---

**Q2: "What are the top 10 most expensive products in our catalog?"**

```sql
SELECT
    Name,
    ProductNumber,
    Color,
    ListPrice,
    StandardCost
FROM Product
WHERE ListPrice > 0
ORDER BY ListPrice DESC
LIMIT 10;
```

---

**Q3: "How many employees do we have in each department?"**

```sql
SELECT
    d.Name AS Department,
    COUNT(*) AS EmployeeCount
FROM Employee e
JOIN EmployeeDepartmentHistory edh ON e.BusinessEntityID = edh.BusinessEntityID
    AND edh.EndDate IS NULL
JOIN Department d ON edh.DepartmentID = d.DepartmentID
WHERE e.CurrentFlag = 1
GROUP BY d.Name
ORDER BY EmployeeCount DESC;
```

---

**Q4: "What are the 5 best-selling products by total quantity sold?"**

```sql
SELECT
    p.Name AS ProductName,
    SUM(sod.OrderQty) AS TotalQtySold,
    ROUND(SUM(sod.LineTotal), 2) AS TotalRevenue
FROM SalesOrderDetail sod
JOIN Product p ON sod.ProductID = p.ProductID
GROUP BY p.ProductID, p.Name
ORDER BY TotalQtySold DESC
LIMIT 5;
```

---

**Q5: "How many vendors do we have, and how many are currently active?"**

```sql
SELECT
    COUNT(*) AS TotalVendors,
    SUM(CASE WHEN ActiveFlag = 1 THEN 1 ELSE 0 END) AS ActiveVendors,
    SUM(CASE WHEN ActiveFlag = 0 THEN 1 ELSE 0 END) AS InactiveVendors
FROM Vendor;
```

---

**Q6: "What is the total revenue by sales territory?"**

```sql
SELECT
    st.Name AS Territory,
    st."Group" AS Region,
    COUNT(*) AS Orders,
    ROUND(SUM(soh.TotalDue), 2) AS TotalRevenue
FROM SalesOrderHeader soh
JOIN SalesTerritory st ON soh.TerritoryID = st.TerritoryID
GROUP BY st.Name, st."Group"
ORDER BY TotalRevenue DESC;
```

---

**Q7: "How many products do we have in each category?"**

```sql
SELECT
    pcat.Name AS Category,
    COUNT(*) AS ProductCount
FROM Product p
JOIN ProductSubcategory psub ON p.ProductSubcategoryID = psub.ProductSubcategoryID
JOIN ProductCategory pcat ON psub.ProductCategoryID = pcat.ProductCategoryID
GROUP BY pcat.Name
ORDER BY ProductCount DESC;
```

---

**Q8: "What are the 10 most recent purchase orders and who are they from?"**

```sql
SELECT
    poh.PurchaseOrderID,
    poh.OrderDate,
    v.Name AS VendorName,
    poh.Status,
    ROUND(poh.TotalDue, 2) AS TotalDue
FROM PurchaseOrderHeader poh
JOIN Vendor v ON poh.VendorID = v.BusinessEntityID
ORDER BY poh.OrderDate DESC
LIMIT 10;
```

---

**Q9: "How many work orders had scrap, and what was the most common scrap reason?"**

```sql
SELECT
    sr.Name AS ScrapReason,
    COUNT(*) AS WorkOrderCount,
    SUM(wo.ScrappedQty) AS TotalScrapped
FROM WorkOrder wo
JOIN ScrapReason sr ON wo.ScrapReasonID = sr.ScrapReasonID
WHERE wo.ScrappedQty > 0
GROUP BY sr.Name
ORDER BY TotalScrapped DESC;
```

---

**Q10: "How many online orders vs. sales-rep orders do we have, and what's the revenue for each?"**

```sql
SELECT
    CASE WHEN OnlineOrderFlag = 1 THEN 'Online' ELSE 'Sales Rep' END AS Channel,
    COUNT(*) AS OrderCount,
    ROUND(SUM(TotalDue), 2) AS TotalRevenue,
    ROUND(AVG(TotalDue), 2) AS AvgOrderValue
FROM SalesOrderHeader
GROUP BY OnlineOrderFlag
ORDER BY TotalRevenue DESC;
```

---


---

**Q1: "Which credit card type is used most for purchases?"**

```sql
SELECT
    cc.CardType,
    COUNT(*) AS OrderCount,
    ROUND(SUM(soh.TotalDue), 2) AS TotalRevenue
FROM SalesOrderHeader soh
JOIN CreditCard cc ON soh.CreditCardID = cc.CreditCardID
GROUP BY cc.CardType
ORDER BY OrderCount DESC;
```

---

**Q2: "What are the top 5 cities we ship the most orders to?"**

```sql
SELECT
    a.City,
    sp.Name AS State,
    COUNT(*) AS OrdersShipped,
    ROUND(SUM(soh.TotalDue), 2) AS TotalRevenue
FROM SalesOrderHeader soh
JOIN Address a ON soh.ShipToAddressID = a.AddressID
JOIN StateProvince sp ON a.StateProvinceID = sp.StateProvinceID
GROUP BY a.City, sp.Name
ORDER BY OrdersShipped DESC
LIMIT 5;
```

---

**Q3: "How many products are currently out of stock?"**

```sql
SELECT
    p.Name AS ProductName,
    p.ProductNumber,
    p.ReorderPoint,
    COALESCE(SUM(pi.Quantity), 0) AS CurrentStock
FROM Product p
LEFT JOIN ProductInventory pi ON p.ProductID = pi.ProductID
WHERE p.SellEndDate IS NULL
    AND p.FinishedGoodsFlag = 1
GROUP BY p.ProductID, p.Name, p.ProductNumber, p.ReorderPoint
HAVING COALESCE(SUM(pi.Quantity), 0) = 0
ORDER BY p.Name;
```

---

**Q4: "Which shipping method is used most often?"**

```sql
SELECT
    sm.Name AS ShipMethod,
    COUNT(*) AS TimesUsed,
    ROUND(AVG(soh.Freight), 2) AS AvgFreightCost
FROM SalesOrderHeader soh
JOIN ShipMethod sm ON soh.ShipMethodID = sm.ShipMethodID
GROUP BY sm.Name
ORDER BY TimesUsed DESC;
```

---

**Q5: "What are the newest 10 employees hired?"**

```sql
SELECT
    p.FirstName || ' ' || p.LastName AS EmployeeName,
    e.JobTitle,
    e.HireDate,
    e.Gender,
    CASE WHEN e.SalariedFlag = 1 THEN 'Salaried' ELSE 'Hourly' END AS PayType
FROM Employee e
JOIN Person p ON e.BusinessEntityID = p.BusinessEntityID
WHERE e.CurrentFlag = 1
ORDER BY e.HireDate DESC
LIMIT 10;
```

---

**Q6: "What is the average order value by year?"**

```sql
SELECT
    strftime('%Y', OrderDate) AS OrderYear,
    COUNT(*) AS TotalOrders,
    ROUND(SUM(TotalDue), 2) AS TotalRevenue,
    ROUND(AVG(TotalDue), 2) AS AvgOrderValue
FROM SalesOrderHeader
GROUP BY strftime('%Y', OrderDate)
ORDER BY OrderYear;
```

---

**Q7: "Which vendor do we spend the most money with?"**

```sql
SELECT
    v.Name AS VendorName,
    v.CreditRating,
    COUNT(*) AS TotalPOs,
    ROUND(SUM(poh.TotalDue), 2) AS TotalSpend
FROM PurchaseOrderHeader poh
JOIN Vendor v ON poh.VendorID = v.BusinessEntityID
GROUP BY v.Name, v.CreditRating
ORDER BY TotalSpend DESC
LIMIT 10;
```

---

**Q8: "How many orders are still unshipped?"**

```sql
SELECT
    Status,
    COUNT(*) AS UnshippedOrders,
    ROUND(SUM(TotalDue), 2) AS TotalValuePending,
    MIN(OrderDate) AS OldestOrderDate
FROM SalesOrderHeader
WHERE ShipDate IS NULL
GROUP BY Status
ORDER BY UnshippedOrders DESC;
```

---

**Q9: "What are the available product colors and how many products come in each color?"**

```sql
SELECT
    COALESCE(Color, 'No Color') AS Color,
    COUNT(*) AS ProductCount,
    ROUND(AVG(ListPrice), 2) AS AvgListPrice
FROM Product
GROUP BY Color
ORDER BY ProductCount DESC;
```

---

**Q10: "What are the top 5 stores by total sales revenue?"**

```sql
SELECT
    s.Name AS StoreName,
    COUNT(DISTINCT soh.SalesOrderID) AS TotalOrders,
    ROUND(SUM(soh.TotalDue), 2) AS TotalRevenue
FROM Store s
JOIN Customer c ON s.BusinessEntityID = c.StoreID
JOIN SalesOrderHeader soh ON c.CustomerID = soh.CustomerID
GROUP BY s.Name
ORDER BY TotalRevenue DESC
LIMIT 5;
```

---





---

**Q1: "What is the total tax and freight collected across all sales orders?"**

```sql
SELECT
    COUNT(*) AS TotalOrders,
    ROUND(SUM(SubTotal), 2) AS TotalSubTotal,
    ROUND(SUM(TaxAmt), 2) AS TotalTax,
    ROUND(SUM(Freight), 2) AS TotalFreight,
    ROUND(SUM(TotalDue), 2) AS GrandTotal
FROM SalesOrderHeader;
```

---

**Q2: "How many products do we manufacture in-house vs. purchase from vendors?"**

```sql
SELECT
    CASE WHEN MakeFlag = 1 THEN 'Manufactured In-House' ELSE 'Purchased from Vendor' END AS SourceType,
    COUNT(*) AS ProductCount,
    ROUND(AVG(ListPrice), 2) AS AvgListPrice,
    ROUND(AVG(StandardCost), 2) AS AvgCost
FROM Product
GROUP BY MakeFlag;
```

---

**Q3: "What are the 10 customers who placed the most orders?"**

```sql
SELECT
    c.CustomerID,
    COALESCE(p.FirstName || ' ' || p.LastName, s.Name) AS CustomerName,
    COUNT(*) AS OrderCount,
    ROUND(SUM(soh.TotalDue), 2) AS TotalSpent
FROM SalesOrderHeader soh
JOIN Customer c ON soh.CustomerID = c.CustomerID
LEFT JOIN Person p ON c.PersonID = p.BusinessEntityID
LEFT JOIN Store s ON c.StoreID = s.BusinessEntityID
GROUP BY c.CustomerID, CustomerName
ORDER BY OrderCount DESC
LIMIT 10;
```

---

**Q4: "How many special offers/promotions are currently active?"**

```sql
SELECT
    SpecialOfferID,
    Description,
    Type,
    Category,
    DiscountPct,
    StartDate,
    EndDate,
    CASE
        WHEN DATE('now') BETWEEN DATE(StartDate) AND DATE(EndDate) THEN 'Active'
        WHEN DATE('now') < DATE(StartDate) THEN 'Upcoming'
        ELSE 'Expired'
    END AS Status
FROM SpecialOffer
ORDER BY Status, EndDate;
```

---

**Q5: "What are the different departments and how many are in each group?"**

```sql
SELECT
    GroupName,
    COUNT(*) AS DepartmentCount,
    GROUP_CONCAT(Name, ', ') AS Departments
FROM Department
GROUP BY GroupName
ORDER BY DepartmentCount DESC;
```

---

**Q6: "Which products have customer reviews, and what's the average rating?"**

```sql
SELECT
    p.Name AS ProductName,
    COUNT(*) AS ReviewCount,
    ROUND(AVG(pr.Rating), 1) AS AvgRating,
    MIN(pr.Rating) AS LowestRating,
    MAX(pr.Rating) AS HighestRating
FROM ProductReview pr
JOIN Product p ON pr.ProductID = p.ProductID
GROUP BY p.Name
ORDER BY AvgRating DESC;
```

---

**Q7: "How many work orders are currently in progress on the shop floor?"**

```sql
SELECT
    COUNT(*) AS InProgressWorkOrders,
    SUM(OrderQty) AS TotalUnitsInProduction,
    MIN(StartDate) AS OldestStartDate,
    MIN(DueDate) AS EarliestDueDate,
    SUM(CASE WHEN DueDate < DATE('now') THEN 1 ELSE 0 END) AS OverdueWorkOrders
FROM WorkOrder
WHERE EndDate IS NULL
    AND StartDate IS NOT NULL;
```

---

**Q8: "What are the top 10 most stocked products across all warehouse locations?"**

```sql
SELECT
    p.Name AS ProductName,
    p.ProductNumber,
    SUM(pi.Quantity) AS TotalStock,
    COUNT(DISTINCT pi.LocationID) AS LocationCount
FROM ProductInventory pi
JOIN Product p ON pi.ProductID = p.ProductID
GROUP BY p.ProductID, p.Name, p.ProductNumber
ORDER BY TotalStock DESC
LIMIT 10;
```

---

**Q9: "How many countries do we operate in, and how many states/provinces does each have?"**

```sql
SELECT
    cr.Name AS Country,
    cr.CountryRegionCode,
    COUNT(*) AS StateProvinceCount
FROM CountryRegion cr
JOIN StateProvince sp ON cr.CountryRegionCode = sp.CountryRegionCode
GROUP BY cr.Name, cr.CountryRegionCode
ORDER BY StateProvinceCount DESC;
```

---

**Q10: "What is the breakdown of person types in the system — employees, customers, contacts?"**

```sql
SELECT
    PersonType,
    CASE PersonType
        WHEN 'EM' THEN 'Employee'
        WHEN 'SP' THEN 'Sales Person'
        WHEN 'IN' THEN 'Individual Customer'
        WHEN 'SC' THEN 'Store Contact'
        WHEN 'VC' THEN 'Vendor Contact'
        WHEN 'GC' THEN 'General Contact'
    END AS TypeLabel,
    COUNT(*) AS PersonCount,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM Person), 2) AS PctOfTotal
FROM Person
GROUP BY PersonType
ORDER BY PersonCount DESC;
```

---
