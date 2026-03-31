# WorkOrderRouting

---

## 📋 Short Description

### Style 1: Conceptual Summary
This table stores manufacturing routing steps — one row per operation within a work order (67,131 routing steps). It captures which work order and product the step belongs to (WorkOrderID, ProductID), the sequence of the operation (OperationSequence), where it happens (LocationID → Location), scheduling info (ScheduledStartDate, ScheduledEndDate vs. ActualStartDate, ActualEndDate), resource consumption (ActualResourceHrs), and cost tracking (PlannedCost vs. ActualCost). This is the most granular manufacturing table — it breaks each work order into individual shop-floor steps.

### Style 2: Query Possibilities & Business Story
This is the manufacturing operations detail table — every step a product goes through on the shop floor during production is recorded here. A single work order can have multiple routing steps (e.g., Step 1: Cut metal at Location A → Step 2: Weld at Location B → Step 3: Paint at Location C). Use this table to answer questions like:

- "How many operations does a typical work order go through?"
- "Which manufacturing locations are used the most?"
- "What's the average actual cost vs. planned cost per operation — are we over or under budget?"
- "Which operations are taking longer than scheduled?"
- "What's the total resource hours consumed per product?"
- "Which locations have the highest cost overruns?"
- "How does actual vs. scheduled timeline compare per work order?"
- "Which products require the most manufacturing steps?"
- "What's the total manufacturing cost per product across all routing steps?" (with WorkOrder, Product)
- "Which locations are bottlenecks — longest actual duration per operation?"
- "How do manufacturing costs break down by product category?" (with Product, ProductSubcategory, ProductCategory)
- "What's the relationship between scrap rate and routing complexity?" (with WorkOrder, ScrapReason)

Each routing step links to a work order (for order-level info like quantities and scrap), a product, and a manufacturing location. The planned vs. actual pattern across dates, hours, and costs enables deep schedule adherence and cost variance analysis.

### Style 3: Grouped & Complete (Column Reference)
This table stores one row per manufacturing routing step (67,131 rows), containing 12 columns organized as:

- **Identifiers (Composite PK):** WorkOrderID (FK → WorkOrder), ProductID, OperationSequence (step number)
- **Location:** LocationID (FK → Location — the shop floor area where this step happens)
- **Scheduled Timeline:** ScheduledStartDate, ScheduledEndDate
- **Actual Timeline:** ActualStartDate (nullable), ActualEndDate (nullable)
- **Resource Consumption:** ActualResourceHrs (nullable — hours of labor/machine time consumed)
- **Cost:** PlannedCost (budgeted), ActualCost (nullable — actual spend)
- **Audit:** ModifiedDate

---

## 📖 Extensive Description

### Purpose & Business Context

WorkOrderRouting is the most granular table in the manufacturing domain — 67,131 rows representing individual operations on the shop floor. While WorkOrder (72,591 rows) captures what needs to be built and how much, WorkOrderRouting captures how it gets built — the step-by-step sequence of operations, which factory locations are used, how long each step takes, and what it costs.

This is essential for manufacturing efficiency analysis: schedule adherence (planned vs. actual dates), cost variance (planned vs. actual cost), resource utilization (actual hours by location), and process complexity (number of steps per product). Combined with WorkOrder's scrap data and Product's catalog info, it enables full production analytics from raw material to finished good.

### Key Business Logic

- **OperationSequence** defines the step order within a work order (1, 2, 3...) — operations must typically complete in sequence
- **ActualStartDate/ActualEndDate/ActualResourceHrs/ActualCost = NULL** → the step hasn't started or completed yet
- **PlannedCost vs. ActualCost** → cost variance; ActualCost > PlannedCost = budget overrun
- **ScheduledEndDate vs. ActualEndDate** → schedule variance; ActualEndDate > ScheduledEndDate = delay
- **ActualResourceHrs** captures labor and/or machine time — key input for utilization and throughput analysis
- **LocationID** represents manufacturing areas (e.g., Frame Welding, Paint Shop, Subassembly, Final Assembly) — 14 locations
- A work order may have 0 routing steps (simple/non-routed) or many (complex multi-step manufacturing)
- **ProductID** in routing should match the ProductID in the parent WorkOrder

### Relationships

| Direction | Table | Join Key | Notes |
|-----------|-------|----------|-------|
| → Parent | WorkOrder | WorkOrderID | Parent work order (qty, scrap, dates) |
| → Parent | Location | LocationID | Manufacturing location (cost rate, availability) |
| → Related | Product | ProductID | Product being manufactured |
| ← Via WorkOrder | ScrapReason | ScrapReasonID | Why units were scrapped |
| ← Via Product | ProductSubcategory → ProductCategory | ProductSubcategoryID | Product classification |
| ← Via Product | BillOfMaterials | ProductAssemblyID/ComponentID | Component structure |
| ← Via Product | ProductInventory → Location | ProductID, LocationID | Inventory at same locations |
| Comparison | PurchaseOrderDetail | ProductID | Buy cost vs. make cost |

---

## 🔗 10 NL → SQL Examples

### Join-Heavy Queries (5)

---

**Q1: "For each routing step, show the work order ID, product name, product category, operation sequence, location name, location cost rate, planned vs. actual cost, and the scrap reason if any units were scrapped."**

*7 joins: WorkOrderRouting → WorkOrder → ScrapReason → Product → ProductSubcategory → ProductCategory → Location*

```sql
SELECT
    wor.WorkOrderID,
    wor.OperationSequence,
    p.Name AS ProductName,
    pcat.Name AS Category,
    loc.Name AS LocationName,
    loc.CostRate AS LocationCostRate,
    ROUND(wor.PlannedCost, 2) AS PlannedCost,
    ROUND(wor.ActualCost, 2) AS ActualCost,
    ROUND(COALESCE(wor.ActualCost, 0) - wor.PlannedCost, 2) AS CostVariance,
    wo.ScrappedQty,
    sr.Name AS ScrapReason
FROM WorkOrderRouting wor
JOIN WorkOrder wo ON wor.WorkOrderID = wo.WorkOrderID
LEFT JOIN ScrapReason sr ON wo.ScrapReasonID = sr.ScrapReasonID
JOIN Product p ON wor.ProductID = p.ProductID
LEFT JOIN ProductSubcategory psub ON p.ProductSubcategoryID = psub.ProductSubcategoryID
LEFT JOIN ProductCategory pcat ON psub.ProductCategoryID = pcat.ProductCategoryID
JOIN Location loc ON wor.LocationID = loc.LocationID
ORDER BY wor.WorkOrderID, wor.OperationSequence;
```

---

**Q2: "Show each routing step with the product name, the product's vendor (who supplied the raw material), vendor credit rating, the manufacturing location, and compare actual manufacturing cost to the vendor's purchase price."**

*9 joins: WorkOrderRouting → Product → ProductVendor → Vendor → Location → WorkOrder → PurchaseOrderDetail → PurchaseOrderHeader*

```sql
SELECT
    p.Name AS ProductName,
    v.Name AS Vendor,
    v.CreditRating,
    pv.StandardPrice AS VendorPrice,
    loc.Name AS MfgLocation,
    wor.OperationSequence,
    ROUND(wor.ActualCost, 2) AS MfgStepCost,
    wo.OrderQty,
    ROUND(SUM(pod.LineTotal), 2) AS TotalPurchaseCost
FROM WorkOrderRouting wor
JOIN WorkOrder wo ON wor.WorkOrderID = wo.WorkOrderID
JOIN Product p ON wor.ProductID = p.ProductID
LEFT JOIN ProductVendor pv ON p.ProductID = pv.ProductID
LEFT JOIN Vendor v ON pv.BusinessEntityID = v.BusinessEntityID
JOIN Location loc ON wor.LocationID = loc.LocationID
LEFT JOIN PurchaseOrderDetail pod ON p.ProductID = pod.ProductID
LEFT JOIN PurchaseOrderHeader poh ON pod.PurchaseOrderID = poh.PurchaseOrderID
GROUP BY p.Name, v.Name, v.CreditRating, pv.StandardPrice, loc.Name,
         wor.OperationSequence, wor.ActualCost, wo.OrderQty
ORDER BY p.Name, wor.OperationSequence;
```

---

**Q3: "For each product routed through manufacturing, show the product name, category, total routing steps, total planned and actual costs across all steps, total resource hours, and compare to the product's list price and standard cost."**

*5 joins: WorkOrderRouting → Product → ProductSubcategory → ProductCategory → Location → WorkOrder*

```sql
SELECT
    p.Name AS ProductName,
    pcat.Name AS Category,
    p.StandardCost AS CatalogStdCost,
    p.ListPrice,
    COUNT(DISTINCT wor.WorkOrderID) AS WorkOrderCount,
    COUNT(*) AS TotalRoutingSteps,
    ROUND(SUM(wor.PlannedCost), 2) AS TotalPlannedCost,
    ROUND(SUM(wor.ActualCost), 2) AS TotalActualCost,
    ROUND(SUM(wor.ActualCost) - SUM(wor.PlannedCost), 2) AS TotalCostVariance,
    ROUND(SUM(wor.ActualResourceHrs), 1) AS TotalResourceHrs,
    COUNT(DISTINCT wor.LocationID) AS LocationsUsed
FROM WorkOrderRouting wor
JOIN WorkOrder wo ON wor.WorkOrderID = wo.WorkOrderID
JOIN Product p ON wor.ProductID = p.ProductID
LEFT JOIN ProductSubcategory psub ON p.ProductSubcategoryID = psub.ProductSubcategoryID
LEFT JOIN ProductCategory pcat ON psub.ProductCategoryID = pcat.ProductCategoryID
GROUP BY p.ProductID, p.Name, pcat.Name, p.StandardCost, p.ListPrice
ORDER BY TotalActualCost DESC;
```

---

**Q4: "Show the full manufacturing journey for each work order: product name, each routing step with location, the employee who approved the purchase order for that product's raw materials, and the vendor who supplied them."**

*10 joins: WorkOrderRouting → WorkOrder → Product → Location → PurchaseOrderDetail → PurchaseOrderHeader → Employee → Person → Vendor → ShipMethod*

```sql
SELECT
    wo.WorkOrderID,
    p.Name AS ProductName,
    wor.OperationSequence AS Step,
    loc.Name AS MfgLocation,
    wor.ActualResourceHrs,
    ROUND(wor.ActualCost, 2) AS StepCost,
    v.Name AS RawMaterialVendor,
    per.FirstName || ' ' || per.LastName AS POApprover,
    sm.Name AS VendorShipMethod,
    poh.OrderDate AS PODate
FROM WorkOrderRouting wor
JOIN WorkOrder wo ON wor.WorkOrderID = wo.WorkOrderID
JOIN Product p ON wor.ProductID = p.ProductID
JOIN Location loc ON wor.LocationID = loc.LocationID
LEFT JOIN PurchaseOrderDetail pod ON p.ProductID = pod.ProductID
LEFT JOIN PurchaseOrderHeader poh ON pod.PurchaseOrderID = poh.PurchaseOrderID
LEFT JOIN Employee e ON poh.EmployeeID = e.BusinessEntityID
LEFT JOIN Person per ON e.BusinessEntityID = per.BusinessEntityID
LEFT JOIN Vendor v ON poh.VendorID = v.BusinessEntityID
LEFT JOIN ShipMethod sm ON poh.ShipMethodID = sm.ShipMethodID
ORDER BY wo.WorkOrderID, wor.OperationSequence;
```

---

**Q5: "For products that are both manufactured and sold, show the product name, category, total manufacturing cost (all routing steps), total sales revenue, and the gross margin — broken down by sales territory."**

*9 joins: WorkOrderRouting → WorkOrder → Product → ProductSubcategory → ProductCategory → SalesOrderDetail → SalesOrderHeader → SalesTerritory*

```sql
SELECT
    p.Name AS ProductName,
    pcat.Name AS Category,
    st.Name AS SalesTerritory,
    ROUND(mfg.TotalMfgCost, 2) AS TotalMfgCost,
    SUM(sod.OrderQty) AS TotalQtySold,
    ROUND(SUM(sod.LineTotal), 2) AS TotalSalesRevenue,
    ROUND(SUM(sod.LineTotal) - mfg.TotalMfgCost, 2) AS GrossMargin
FROM Product p
LEFT JOIN ProductSubcategory psub ON p.ProductSubcategoryID = psub.ProductSubcategoryID
LEFT JOIN ProductCategory pcat ON psub.ProductCategoryID = pcat.ProductCategoryID
JOIN SalesOrderDetail sod ON p.ProductID = sod.ProductID
JOIN SalesOrderHeader soh ON sod.SalesOrderID = soh.SalesOrderID
JOIN SalesTerritory st ON soh.TerritoryID = st.TerritoryID
JOIN (
    SELECT
        wor.ProductID,
        ROUND(SUM(wor.ActualCost), 2) AS TotalMfgCost
    FROM WorkOrderRouting wor
    GROUP BY wor.ProductID
) mfg ON p.ProductID = mfg.ProductID
GROUP BY p.Name, pcat.Name, st.Name, mfg.TotalMfgCost
ORDER BY GrossMargin DESC;
```

---

### Practical Business Use-Case Queries (5)

---

**Q6: "What's the overall cost variance across all routing steps — are we over or under budget in manufacturing?"**

*Use case: Manufacturing finance — budget adherence*

```sql
SELECT
    COUNT(*) AS TotalRoutingSteps,
    ROUND(SUM(PlannedCost), 2) AS TotalPlannedCost,
    ROUND(SUM(ActualCost), 2) AS TotalActualCost,
    ROUND(SUM(ActualCost) - SUM(PlannedCost), 2) AS OverallVariance,
    ROUND((SUM(ActualCost) - SUM(PlannedCost)) * 100.0 / NULLIF(SUM(PlannedCost), 0), 2) AS VariancePct,
    CASE
        WHEN SUM(ActualCost) > SUM(PlannedCost) THEN 'OVER BUDGET'
        ELSE 'UNDER/ON BUDGET'
    END AS BudgetStatus
FROM WorkOrderRouting
WHERE ActualCost IS NOT NULL;
```

---

**Q7: "Which manufacturing locations have the highest utilization (total resource hours) and highest cost? Rank them."**

*Use case: Capacity planning / location efficiency*

```sql
SELECT
    LocationID,
    COUNT(*) AS OperationsPerformed,
    COUNT(DISTINCT WorkOrderID) AS UniqueWorkOrders,
    ROUND(SUM(ActualResourceHrs), 1) AS TotalResourceHrs,
    ROUND(AVG(ActualResourceHrs), 2) AS AvgHrsPerOperation,
    ROUND(SUM(ActualCost), 2) AS TotalActualCost,
    ROUND(SUM(ActualCost) - SUM(PlannedCost), 2) AS CostVariance,
    RANK() OVER (ORDER BY SUM(ActualResourceHrs) DESC) AS UtilizationRank
FROM WorkOrderRouting
WHERE ActualResourceHrs IS NOT NULL
GROUP BY LocationID
ORDER BY TotalResourceHrs DESC;
```

---

**Q8: "Which routing steps are running behind schedule — where actual end date exceeded scheduled end date — and by how many days on average?"**

*Use case: Production scheduling — delay identification*

```sql
SELECT
    LocationID,
    COUNT(*) AS DelayedOperations,
    ROUND(AVG(JULIANDAY(ActualEndDate) - JULIANDAY(ScheduledEndDate)), 1) AS AvgDaysLate,
    MAX(CAST(JULIANDAY(ActualEndDate) - JULIANDAY(ScheduledEndDate) AS INTEGER)) AS WorstDelayDays,
    ROUND(SUM(ActualCost), 2) AS CostOfDelayedOps,
    ROUND(SUM(ActualResourceHrs), 1) AS HrsOnDelayedOps
FROM WorkOrderRouting
WHERE ActualEndDate IS NOT NULL
    AND ActualEndDate > ScheduledEndDate
GROUP BY LocationID
ORDER BY AvgDaysLate DESC;
```

---

**Q9: "What's the average number of routing steps per work order, and which work orders have the most complex routing (most steps)?"**

*Use case: Process complexity analysis*

```sql
WITH WOComplexity AS (
    SELECT
        WorkOrderID,
        ProductID,
        COUNT(*) AS RoutingSteps,
        ROUND(SUM(ActualResourceHrs), 1) AS TotalHrs,
        ROUND(SUM(ActualCost), 2) AS TotalCost
    FROM WorkOrderRouting
    GROUP BY WorkOrderID, ProductID
)
SELECT
    ROUND(AVG(RoutingSteps), 1) AS AvgStepsPerWO,
    MIN(RoutingSteps) AS MinSteps,
    MAX(RoutingSteps) AS MaxSteps,
    ROUND(AVG(TotalHrs), 1) AS AvgHrsPerWO,
    ROUND(AVG(TotalCost), 2) AS AvgCostPerWO
FROM WOComplexity

UNION ALL

SELECT
    RoutingSteps,
    WorkOrderID,
    ProductID,
    TotalHrs,
    TotalCost
FROM WOComplexity
ORDER BY RoutingSteps DESC
LIMIT 10;
```

---

**Q10: "Show the monthly trend of total manufacturing hours and costs — are we spending more time and money over time?"**

*Use case: Manufacturing operations — trend monitoring*

```sql
SELECT
    strftime('%Y-%m', ScheduledStartDate) AS MfgMonth,
    COUNT(*) AS OperationCount,
    COUNT(DISTINCT WorkOrderID) AS UniqueWorkOrders,
    ROUND(SUM(ActualResourceHrs), 1) AS TotalResourceHrs,
    ROUND(SUM(PlannedCost), 2) AS TotalPlannedCost,
    ROUND(SUM(ActualCost), 2) AS TotalActualCost,
    ROUND(SUM(ActualCost) - SUM(PlannedCost), 2) AS MonthlyVariance,
    ROUND(AVG(ActualResourceHrs), 2) AS AvgHrsPerOp
FROM WorkOrderRouting
WHERE ActualCost IS NOT NULL
GROUP BY strftime('%Y-%m', ScheduledStartDate)
ORDER BY MfgMonth;
```

---
