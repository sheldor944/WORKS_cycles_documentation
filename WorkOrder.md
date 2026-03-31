# WorkOrder

---

## 📋 Short Description

### Style 1: Conceptual Summary
This table stores manufacturing work orders — one row per work order (72,591 work orders). It captures what product is being built (ProductID), how much (OrderQty), the production outcome (StockedQty vs. ScrappedQty), why items were scrapped (ScrapReasonID → ScrapReason), and the production timeline (StartDate, EndDate, DueDate). This is the central manufacturing table — it sits between procurement (what we bought) and sales (what we sold), tracking what gets built on the shop floor.

### Style 2: Query Possibilities & Business Story
This is the core manufacturing/production table — every time the factory builds a product, a work order is created here. The critical story this table tells is the **ordered → stocked → scrapped** production pipeline — did we produce what we planned, and if not, how much was lost and why? Use this table to answer questions like:

- "How many work orders were created this month?"
- "What's our overall manufacturing scrap rate?"
- "Which products have the highest scrap rate?"
- "What are the most common scrap reasons?"
- "How many work orders are currently in progress (started but not ended)?"
- "What's the average production time (StartDate to EndDate) by product?"
- "Which work orders are past due (DueDate passed but EndDate is NULL)?"
- "How much production output are we actually stocking vs. scrapping?"
- "What's the total manufacturing volume trend over time?"
- "Which products take longest to manufacture?" (with Product.DaysToManufacture)
- "What's the total manufacturing cost for each work order?" (with WorkOrderRouting)
- "How does scrap rate correlate with the vendor who supplied raw materials?" (with PurchaseOrderDetail, Vendor)
- "What products are we building vs. buying?" (with Product.MakeFlag)

Each work order links to the Product being manufactured, an optional ScrapReason, and is broken into detailed operations via WorkOrderRouting (locations, costs, hours). It completes the value chain: Purchase → Manufacture (WorkOrder) → Inventory → Sell.

### Style 3: Grouped & Complete (Column Reference)
This table stores one row per manufacturing work order (72,591 rows), containing 10 columns organized as:

- **Identifiers:** WorkOrderID (PK, auto-increment)
- **Product:** ProductID (FK → Product — what's being manufactured)
- **Quantities:** OrderQty (planned production), StockedQty (successfully produced and stocked), ScrappedQty (lost/defective units)
- **Quality:** ScrapReasonID (FK → ScrapReason, nullable — why units were scrapped; NULL if no scrap)
- **Timeline:** StartDate (production began), EndDate (nullable — production completed; NULL = still in progress), DueDate (expected completion)
- **Audit:** ModifiedDate

---

## 📖 Extensive Description

### Purpose & Business Context

WorkOrder is the central manufacturing table — 72,591 work orders representing the production floor's activity. It's the critical middle step in the value chain: the company procures raw materials (PurchaseOrder), manufactures products (WorkOrder), stocks them (ProductInventory), and sells them (SalesOrder). This table answers the fundamental manufacturing question: "Did we build what we planned, on time, and without waste?"

The **OrderQty → StockedQty + ScrappedQty** relationship is the core data story — it reveals production yield, scrap rates, and quality issues. Combined with ScrapReason, it enables root cause analysis of manufacturing defects. Combined with WorkOrderRouting, it provides cost, location, and timing details for each production step.

With 72,591 work orders (vs. 31,465 sales orders), manufacturing volume significantly exceeds sales volume — reflecting that multiple components/subassemblies may be manufactured to produce a single sellable finished good.

### Key Business Logic

- **StockedQty = OrderQty - ScrappedQty** — what successfully made it to inventory
- **ScrappedQty > 0** → quality issue; check ScrapReasonID for the cause
- **ScrapReasonID IS NULL** → no scrap occurred (ScrappedQty should be 0)
- **EndDate IS NULL** → work order still in progress or not yet started
- **EndDate > DueDate** → production ran late
- **OrderQty** is the planned/target quantity; actual output is StockedQty
- **Yield Rate** = StockedQty / OrderQty — measures production efficiency
- Products with MakeFlag = 1 in the Product table are the ones appearing here
- A single work order may have many routing steps (WorkOrderRouting) across different locations
- Multiple work orders can exist for the same product (different batches/runs)

### Relationships

| Direction | Table | Join Key | Notes |
|-----------|-------|----------|-------|
| → Parent | Product | ProductID | Product being manufactured |
| → Parent | ScrapReason | ScrapReasonID | Why units were scrapped (nullable) |
| ↓ Child | WorkOrderRouting (67,131) | WorkOrderID | Step-by-step operations, locations, costs, hours |
| ← Via Product | ProductSubcategory → ProductCategory | ProductSubcategoryID | Product classification |
| ← Via Product | BillOfMaterials | ProductAssemblyID | Components needed to build this product |
| ← Via Product | ProductInventory → Location | ProductID | Where finished goods are stocked |
| ← Via Product | PurchaseOrderDetail | ProductID | Raw materials purchased for this product |
| ← Via Product | SalesOrderDetail → SalesOrderHeader | ProductID | Sales of the manufactured product |
| ← Via WorkOrderRouting | Location | LocationID | Manufacturing floor locations |
| Related | TransactionHistory | ReferenceOrderID | Audit trail (TransactionType = 'W') |

---

## 🔗 10 NL → SQL Examples

### Join-Heavy Queries (5)

---

**Q1: "For each work order, show the product name, product category, order and stocked quantities, scrap reason (if any), total manufacturing cost from routing, and the number of routing steps."**

*6 joins: WorkOrder → Product → ProductSubcategory → ProductCategory → ScrapReason → WorkOrderRouting*

```sql
SELECT
    wo.WorkOrderID,
    p.Name AS ProductName,
    pcat.Name AS Category,
    wo.OrderQty,
    wo.StockedQty,
    wo.ScrappedQty,
    sr.Name AS ScrapReason,
    COALESCE(routing.TotalSteps, 0) AS RoutingSteps,
    COALESCE(ROUND(routing.TotalActualCost, 2), 0) AS TotalMfgCost,
    COALESCE(ROUND(routing.TotalResourceHrs, 1), 0) AS TotalResourceHrs
FROM WorkOrder wo
JOIN Product p ON wo.ProductID = p.ProductID
LEFT JOIN ProductSubcategory psub ON p.ProductSubcategoryID = psub.ProductSubcategoryID
LEFT JOIN ProductCategory pcat ON psub.ProductCategoryID = pcat.ProductCategoryID
LEFT JOIN ScrapReason sr ON wo.ScrapReasonID = sr.ScrapReasonID
LEFT JOIN (
    SELECT
        WorkOrderID,
        COUNT(*) AS TotalSteps,
        SUM(ActualCost) AS TotalActualCost,
        SUM(ActualResourceHrs) AS TotalResourceHrs
    FROM WorkOrderRouting
    GROUP BY WorkOrderID
) routing ON wo.WorkOrderID = routing.WorkOrderID
ORDER BY wo.WorkOrderID;
```

---

**Q2: "For products being manufactured, show the work order details alongside the vendor who supplies the raw materials, the purchase price, and the vendor's credit rating — to compare procurement cost to manufacturing output."**

*8 joins: WorkOrder → Product → ProductSubcategory → ProductCategory → ProductVendor → Vendor → PurchaseOrderDetail → PurchaseOrderHeader*

```sql
SELECT
    wo.WorkOrderID,
    p.Name AS ProductName,
    pcat.Name AS Category,
    wo.OrderQty AS MfgOrderQty,
    wo.StockedQty,
    wo.ScrappedQty,
    v.Name AS RawMaterialVendor,
    v.CreditRating,
    pv.StandardPrice AS VendorCatalogPrice,
    ROUND(AVG(pod.UnitPrice), 2) AS AvgActualPurchasePrice,
    SUM(pod.RejectedQty) AS VendorRejections
FROM WorkOrder wo
JOIN Product p ON wo.ProductID = p.ProductID
LEFT JOIN ProductSubcategory psub ON p.ProductSubcategoryID = psub.ProductSubcategoryID
LEFT JOIN ProductCategory pcat ON psub.ProductCategoryID = pcat.ProductCategoryID
LEFT JOIN ProductVendor pv ON p.ProductID = pv.ProductID
LEFT JOIN Vendor v ON pv.BusinessEntityID = v.BusinessEntityID
LEFT JOIN PurchaseOrderDetail pod ON p.ProductID = pod.ProductID
LEFT JOIN PurchaseOrderHeader poh ON pod.PurchaseOrderID = poh.PurchaseOrderID
    AND poh.VendorID = v.BusinessEntityID
GROUP BY wo.WorkOrderID, p.Name, pcat.Name, wo.OrderQty, wo.StockedQty,
         wo.ScrappedQty, v.Name, v.CreditRating, pv.StandardPrice
ORDER BY wo.ScrappedQty DESC;
```

---

**Q3: "Show the full product lifecycle: product name, category, what we paid to buy it, what it cost to manufacture (from routing), and what we sold it for — with sales territory breakdown."**

*10 joins: WorkOrder → WorkOrderRouting → Product → ProductSubcategory → ProductCategory → PurchaseOrderDetail → SalesOrderDetail → SalesOrderHeader → SalesTerritory*

```sql
SELECT
    p.Name AS ProductName,
    pcat.Name AS Category,
    st.Name AS SalesTerritory,
    ROUND(COALESCE(purchase.AvgPurchasePrice, 0), 2) AS AvgPurchaseCost,
    ROUND(COALESCE(mfg.MfgCostPerUnit, 0), 2) AS AvgMfgCostPerUnit,
    ROUND(AVG(sod.UnitPrice), 2) AS AvgSellingPrice,
    SUM(sod.OrderQty) AS TotalQtySold,
    ROUND(SUM(sod.LineTotal), 2) AS TotalSalesRevenue
FROM WorkOrder wo
JOIN Product p ON wo.ProductID = p.ProductID
LEFT JOIN ProductSubcategory psub ON p.ProductSubcategoryID = psub.ProductSubcategoryID
LEFT JOIN ProductCategory pcat ON psub.ProductCategoryID = pcat.ProductCategoryID
LEFT JOIN (
    SELECT ProductID, ROUND(AVG(UnitPrice), 2) AS AvgPurchasePrice
    FROM PurchaseOrderDetail GROUP BY ProductID
) purchase ON p.ProductID = purchase.ProductID
LEFT JOIN (
    SELECT wo2.ProductID,
        ROUND(SUM(wor.ActualCost) / NULLIF(SUM(wo2.OrderQty), 0), 2) AS MfgCostPerUnit
    FROM WorkOrder wo2
    JOIN WorkOrderRouting wor ON wo2.WorkOrderID = wor.WorkOrderID
    GROUP BY wo2.ProductID
) mfg ON p.ProductID = mfg.ProductID
LEFT JOIN SalesOrderDetail sod ON p.ProductID = sod.ProductID
LEFT JOIN SalesOrderHeader soh ON sod.SalesOrderID = soh.SalesOrderID
LEFT JOIN SalesTerritory st ON soh.TerritoryID = st.TerritoryID
GROUP BY p.Name, pcat.Name, st.Name, purchase.AvgPurchasePrice, mfg.MfgCostPerUnit
ORDER BY TotalSalesRevenue DESC;
```

---

**Q4: "Show each work order with the product's bill of materials — what components are needed, the component names, and whether those components are currently in stock at which locations."**

*7 joins: WorkOrder → Product → BillOfMaterials → Product(component) → UnitMeasure → ProductInventory → Location*

```sql
SELECT
    wo.WorkOrderID,
    p.Name AS AssemblyProduct,
    wo.OrderQty AS MfgQty,
    comp.Name AS ComponentName,
    bom.PerAssemblyQty AS QtyPerAssembly,
    bom.PerAssemblyQty * wo.OrderQty AS TotalComponentNeeded,
    um.Name AS UnitOfMeasure,
    loc.Name AS InventoryLocation,
    COALESCE(pi.Quantity, 0) AS ComponentStockOnHand
FROM WorkOrder wo
JOIN Product p ON wo.ProductID = p.ProductID
LEFT JOIN BillOfMaterials bom ON p.ProductID = bom.ProductAssemblyID
    AND bom.EndDate IS NULL
LEFT JOIN Product comp ON bom.ComponentID = comp.ProductID
LEFT JOIN UnitMeasure um ON bom.UnitMeasureCode = um.UnitMeasureCode
LEFT JOIN ProductInventory pi ON comp.ProductID = pi.ProductID
LEFT JOIN Location loc ON pi.LocationID = loc.LocationID
WHERE wo.EndDate IS NULL
ORDER BY wo.WorkOrderID, bom.BOMLevel;
```

---

**Q5: "For work orders with scrap, show the product name, category, scrap reason, the manufacturing locations involved, the employee who approved the purchase of raw materials, and the vendor who supplied them."**

*11 joins: WorkOrder → Product → ProductSubcategory → ProductCategory → ScrapReason → WorkOrderRouting → Location → PurchaseOrderDetail → PurchaseOrderHeader → Employee → Person → Vendor*

```sql
SELECT
    wo.WorkOrderID,
    p.Name AS ProductName,
    pcat.Name AS Category,
    wo.OrderQty,
    wo.ScrappedQty,
    ROUND(wo.ScrappedQty * 100.0 / NULLIF(wo.OrderQty, 0), 2) AS ScrapRatePct,
    sr.Name AS ScrapReason,
    loc.Name AS MfgLocation,
    v.Name AS RawMaterialVendor,
    per.FirstName || ' ' || per.LastName AS POApprover
FROM WorkOrder wo
JOIN Product p ON wo.ProductID = p.ProductID
LEFT JOIN ProductSubcategory psub ON p.ProductSubcategoryID = psub.ProductSubcategoryID
LEFT JOIN ProductCategory pcat ON psub.ProductCategoryID = pcat.ProductCategoryID
JOIN ScrapReason sr ON wo.ScrapReasonID = sr.ScrapReasonID
LEFT JOIN WorkOrderRouting wor ON wo.WorkOrderID = wor.WorkOrderID
LEFT JOIN Location loc ON wor.LocationID = loc.LocationID
LEFT JOIN PurchaseOrderDetail pod ON p.ProductID = pod.ProductID
LEFT JOIN PurchaseOrderHeader poh ON pod.PurchaseOrderID = poh.PurchaseOrderID
LEFT JOIN Employee e ON poh.EmployeeID = e.BusinessEntityID
LEFT JOIN Person per ON e.BusinessEntityID = per.BusinessEntityID
LEFT JOIN Vendor v ON poh.VendorID = v.BusinessEntityID
WHERE wo.ScrappedQty > 0
ORDER BY ScrapRatePct DESC;
```

---

### Practical Business Use-Case Queries (5)

---

**Q6: "What's the overall manufacturing yield rate and scrap rate across all work orders?"**

*Use case: Manufacturing KPI — production efficiency*

```sql
SELECT
    COUNT(*) AS TotalWorkOrders,
    SUM(OrderQty) AS TotalPlanned,
    SUM(StockedQty) AS TotalStocked,
    SUM(ScrappedQty) AS TotalScrapped,
    ROUND(SUM(StockedQty) * 100.0 / NULLIF(SUM(OrderQty), 0), 2) AS YieldRatePct,
    ROUND(SUM(ScrappedQty) * 100.0 / NULLIF(SUM(OrderQty), 0), 2) AS ScrapRatePct,
    SUM(CASE WHEN ScrappedQty > 0 THEN 1 ELSE 0 END) AS WorkOrdersWithScrap,
    ROUND(SUM(CASE WHEN ScrappedQty > 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS PctWOsWithScrap
FROM WorkOrder;
```

---

**Q7: "What are the top scrap reasons by frequency and total scrapped units?"**

*Use case: Quality management — root cause prioritization*

```sql
SELECT
    sr.ScrapReasonID,
    sr.Name AS ScrapReason,
    COUNT(*) AS AffectedWorkOrders,
    SUM(wo.ScrappedQty) AS TotalUnitsScrapped,
    ROUND(AVG(wo.ScrappedQty), 1) AS AvgScrapPerWO,
    ROUND(SUM(wo.ScrappedQty) * 100.0 / (SELECT SUM(ScrappedQty) FROM WorkOrder WHERE ScrappedQty > 0), 2) AS PctOfAllScrap
FROM WorkOrder wo
JOIN ScrapReason sr ON wo.ScrapReasonID = sr.ScrapReasonID
WHERE wo.ScrappedQty > 0
GROUP BY sr.ScrapReasonID, sr.Name
ORDER BY TotalUnitsScrapped DESC;
```

---

**Q8: "Which work orders are overdue — past their DueDate but not yet completed?"**

*Use case: Production scheduling — overdue order tracking*

```sql
SELECT
    WorkOrderID,
    ProductID,
    OrderQty,
    StartDate,
    DueDate,
    CAST(JULIANDAY('now') - JULIANDAY(DueDate) AS INTEGER) AS DaysOverdue,
    StockedQty,
    ScrappedQty,
    CASE
        WHEN JULIANDAY('now') - JULIANDAY(DueDate) > 30 THEN 'CRITICAL (>30 days)'
        WHEN JULIANDAY('now') - JULIANDAY(DueDate) > 7 THEN 'WARNING (>7 days)'
        ELSE 'MINOR'
    END AS UrgencyLevel
FROM WorkOrder
WHERE EndDate IS NULL
    AND DueDate < DATE('now')
ORDER BY DaysOverdue DESC;
```

---

**Q9: "What's the average production cycle time (StartDate to EndDate) by product, and which products consistently take longest?"**

*Use case: Production planning — cycle time optimization*

```sql
SELECT
    ProductID,
    COUNT(*) AS CompletedWorkOrders,
    ROUND(AVG(JULIANDAY(EndDate) - JULIANDAY(StartDate)), 1) AS AvgCycleTimeDays,
    MIN(CAST(JULIANDAY(EndDate) - JULIANDAY(StartDate) AS INTEGER)) AS FastestDays,
    MAX(CAST(JULIANDAY(EndDate) - JULIANDAY(StartDate) AS INTEGER)) AS SlowestDays,
    SUM(OrderQty) AS TotalQtyProduced,
    ROUND(SUM(StockedQty) * 100.0 / NULLIF(SUM(OrderQty), 0), 2) AS YieldRatePct,
    SUM(CASE WHEN EndDate > DueDate THEN 1 ELSE 0 END) AS LateCompletions
FROM WorkOrder
WHERE EndDate IS NOT NULL
GROUP BY ProductID
ORDER BY AvgCycleTimeDays DESC
LIMIT 20;
```

---

**Q10: "Show the monthly manufacturing trend — total work orders, total output, scrap rate, and average cycle time."**

*Use case: Manufacturing operations — trend monitoring*

```sql
SELECT
    strftime('%Y-%m', StartDate) AS MfgMonth,
    COUNT(*) AS WorkOrders,
    SUM(OrderQty) AS TotalPlanned,
    SUM(StockedQty) AS TotalStocked,
    SUM(ScrappedQty) AS TotalScrapped,
    ROUND(SUM(ScrappedQty) * 100.0 / NULLIF(SUM(OrderQty), 0), 2) AS ScrapRatePct,
    ROUND(SUM(StockedQty) * 100.0 / NULLIF(SUM(OrderQty), 0), 2) AS YieldRatePct,
    SUM(CASE WHEN EndDate IS NULL THEN 1 ELSE 0 END) AS StillInProgress,
    ROUND(AVG(
        CASE WHEN EndDate IS NOT NULL
        THEN JULIANDAY(EndDate) - JULIANDAY(StartDate)
        END
    ), 1) AS AvgCycleTimeDays
FROM WorkOrder
GROUP BY strftime('%Y-%m', StartDate)
ORDER BY MfgMonth;
```

---
