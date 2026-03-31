# CurrencyRate

---

## 📋 Short Description

### Style 1: Conceptual Summary
This table stores daily currency exchange rates — one row per currency pair per date (13,532 rate records). It captures which currencies are being exchanged (FromCurrencyCode, ToCurrencyCode → Currency), the date of the rate (CurrencyRateDate), and two rate snapshots (AverageRate — the day's average, EndOfDayRate — the closing rate). This table powers international sales order pricing and is referenced directly by SalesOrderHeader for orders involving non-base currency transactions.

### Style 2: Query Possibilities & Business Story
This is the foreign exchange rate table — every day, exchange rates between currency pairs are recorded here so the company can properly price and account for international sales orders. When a sales order involves a currency other than the base currency (USD), SalesOrderHeader references a CurrencyRateID from this table to capture the applicable exchange rate. Use this table to answer questions like:

- "What's today's exchange rate between USD and EUR?"
- "How has the USD/GBP exchange rate trended over the last year?"
- "Which currency pairs have the most rate records?"
- "What's the biggest single-day exchange rate swing for any currency pair?"
- "How many international orders used a specific currency rate?" (with SalesOrderHeader)
- "What's the difference between average rate and end-of-day rate — how volatile is a currency?"
- "Which currencies have appreciated or depreciated the most over time?"
- "What's the total sales revenue in foreign currencies converted to base currency?" (with SalesOrderHeader)
- "How many unique currency pairs are tracked?"
- "What date range do we have rate data for?"
- "Which sales territories use which currencies?" (with SalesTerritory, CountryRegion, CountryRegionCurrency)
- "How does exchange rate fluctuation impact our international revenue when converted?" (with SalesOrderHeader)

Each rate links to two Currency records (from and to) and is referenced by SalesOrderHeader. The geographic chain CountryRegion → CountryRegionCurrency → Currency connects rates to sales territories and customer locations.

### Style 3: Grouped & Complete (Column Reference)
This table stores one row per currency pair per date (13,532 rows), containing 7 columns organized as:

- **Identifiers:** CurrencyRateID (PK, auto-increment)
- **Date:** CurrencyRateDate (the date this rate applies to)
- **Currency Pair:** FromCurrencyCode (FK → Currency — base/source currency), ToCurrencyCode (FK → Currency — target currency)
- **Rates:** AverageRate (day's average exchange rate), EndOfDayRate (closing rate)
- **Audit:** ModifiedDate
- **Uniqueness:** Composite unique on (CurrencyRateDate, FromCurrencyCode, ToCurrencyCode)

---

## 📖 Extensive Description

### Purpose & Business Context

CurrencyRate is the foreign exchange reference table — 13,532 daily rate records that support international commerce. AdventureWorks operates globally (sales territories span North America, Europe, Pacific, etc.), and when orders are placed in non-base currencies, the applicable exchange rate must be captured at the time of the transaction for proper revenue recognition and financial reporting.

SalesOrderHeader references this table via CurrencyRateID — when NULL, the order is in the base currency (presumably USD) and no conversion is needed. When populated, the rate tells the system how to convert between the order's currency and the base currency.

The table stores two rate values per day per pair:
- **AverageRate** — the mean rate across the trading day (useful for financial reporting)
- **EndOfDayRate** — the closing rate (useful for balance sheet valuations)

### Key Business Logic

- **FromCurrencyCode** is typically the base currency (e.g., 'USD'); **ToCurrencyCode** is the foreign currency
- **AverageRate** = day-average rate; **EndOfDayRate** = closing/settlement rate
- **One record per currency pair per day** — enforced by the composite unique constraint
- **SalesOrderHeader.CurrencyRateID = NULL** → order is in base currency, no conversion needed
- **SalesOrderHeader.CurrencyRateID IS NOT NULL** → international order, this rate was applied
- Rate values represent "1 unit of FromCurrency = X units of ToCurrency"
- To convert TotalDue from foreign to base: `TotalDue / AverageRate` (or vice versa depending on direction)
- Rates should exist for every trading day — gaps may indicate holidays or data issues
- Historical rates are valuable for restating historical financials at current rates (mark-to-market)

### Relationships

| Direction | Table | Join Key | Notes |
|-----------|-------|----------|-------|
| → Parent | Currency (From) | FromCurrencyCode | Base/source currency |
| → Parent | Currency (To) | ToCurrencyCode | Target/foreign currency |
| ← Referenced by | SalesOrderHeader (31,465) | CurrencyRateID | Orders using this exchange rate |
| ← Via Currency | CountryRegionCurrency | CurrencyCode | Which countries use this currency |
| ← Via CountryRegionCurrency | CountryRegion | CountryRegionCode | Country-level geography |
| ← Via SalesOrderHeader | Customer, SalesPerson, SalesTerritory | — | Full sales context for FX orders |

---

## 🔗 10 NL → SQL Examples

### Join-Heavy Queries (5)

---

**Q1: "For each international sales order, show the order number, customer name, territory, the from/to currency names, the exchange rate applied, and the order total — both in foreign and estimated base currency."**

*9 joins: CurrencyRate → Currency(from) → Currency(to) → SalesOrderHeader → Customer → Person → SalesTerritory → SalesPerson → Person(rep)*

```sql
SELECT
    soh.SalesOrderNumber,
    soh.OrderDate,
    cust.FirstName || ' ' || cust.LastName AS CustomerName,
    st.Name AS Territory,
    cf.Name AS FromCurrency,
    ct.Name AS ToCurrency,
    cr.AverageRate,
    cr.EndOfDayRate,
    ROUND(soh.TotalDue, 2) AS OrderTotal,
    ROUND(soh.TotalDue / cr.AverageRate, 2) AS EstimatedBaseCurrencyTotal,
    rep.FirstName || ' ' || rep.LastName AS SalesPersonName
FROM CurrencyRate cr
JOIN Currency cf ON cr.FromCurrencyCode = cf.CurrencyCode
JOIN Currency ct ON cr.ToCurrencyCode = ct.CurrencyCode
JOIN SalesOrderHeader soh ON cr.CurrencyRateID = soh.CurrencyRateID
JOIN Customer c ON soh.CustomerID = c.CustomerID
LEFT JOIN Person cust ON c.PersonID = cust.BusinessEntityID
JOIN SalesTerritory st ON soh.TerritoryID = st.TerritoryID
LEFT JOIN SalesPerson sp ON soh.SalesPersonID = sp.BusinessEntityID
LEFT JOIN Person rep ON sp.BusinessEntityID = rep.BusinessEntityID
ORDER BY soh.OrderDate DESC;
```

---

**Q2: "Show each currency rate alongside the countries that use the target currency, their sales territories, and the total revenue from orders placed using that rate."**

*8 joins: CurrencyRate → Currency(from) → Currency(to) → CountryRegionCurrency → CountryRegion → SalesTerritory → SalesOrderHeader*

```sql
SELECT
    cr.CurrencyRateDate,
    cf.Name AS FromCurrency,
    ct.Name AS ToCurrency,
    cr.AverageRate,
    crg.Name AS CountryUsingToCurrency,
    st.Name AS SalesTerritory,
    COUNT(DISTINCT soh.SalesOrderID) AS OrdersUsingRate,
    ROUND(SUM(soh.TotalDue), 2) AS TotalRevenue
FROM CurrencyRate cr
JOIN Currency cf ON cr.FromCurrencyCode = cf.CurrencyCode
JOIN Currency ct ON cr.ToCurrencyCode = ct.CurrencyCode
LEFT JOIN CountryRegionCurrency crc ON ct.CurrencyCode = crc.CurrencyCode
LEFT JOIN CountryRegion crg ON crc.CountryRegionCode = crg.CountryRegionCode
LEFT JOIN StateProvince spr ON crg.CountryRegionCode = spr.CountryRegionCode
LEFT JOIN SalesTerritory st ON spr.TerritoryID = st.TerritoryID
LEFT JOIN SalesOrderHeader soh ON cr.CurrencyRateID = soh.CurrencyRateID
GROUP BY cr.CurrencyRateDate, cf.Name, ct.Name, cr.AverageRate, crg.Name, st.Name
ORDER BY cr.CurrencyRateDate DESC;
```

---

**Q3: "For international orders, show the line-item detail: product name, category, quantity sold, line total, the exchange rate used, and convert the line total to base currency."**

*9 joins: CurrencyRate → Currency(from) → Currency(to) → SalesOrderHeader → SalesOrderDetail → Product → ProductSubcategory → ProductCategory → SalesTerritory*

```sql
SELECT
    soh.SalesOrderNumber,
    st.Name AS Territory,
    cf.Name AS FromCurrency,
    ct.Name AS ToCurrency,
    cr.AverageRate,
    p.Name AS ProductName,
    pcat.Name AS Category,
    sod.OrderQty,
    ROUND(sod.LineTotal, 2) AS LineTotal_ForeignCurrency,
    ROUND(sod.LineTotal / cr.AverageRate, 2) AS LineTotal_BaseCurrency
FROM CurrencyRate cr
JOIN Currency cf ON cr.FromCurrencyCode = cf.CurrencyCode
JOIN Currency ct ON cr.ToCurrencyCode = ct.CurrencyCode
JOIN SalesOrderHeader soh ON cr.CurrencyRateID = soh.CurrencyRateID
JOIN SalesOrderDetail sod ON soh.SalesOrderID = sod.SalesOrderID
JOIN Product p ON sod.ProductID = p.ProductID
LEFT JOIN ProductSubcategory psub ON p.ProductSubcategoryID = psub.ProductSubcategoryID
LEFT JOIN ProductCategory pcat ON psub.ProductCategoryID = pcat.ProductCategoryID
JOIN SalesTerritory st ON soh.TerritoryID = st.TerritoryID
ORDER BY soh.OrderDate DESC, soh.SalesOrderNumber;
```

---

**Q4: "Show the exchange rate used for each international order alongside the shipping address country, billing address state, credit card type, and ship method — the full international order context."**

*11 joins: CurrencyRate → Currency(from) → Currency(to) → SalesOrderHeader → Address(ship) → StateProvince(ship) → CountryRegion(ship) → Address(bill) → StateProvince(bill) → CreditCard → ShipMethod*

```sql
SELECT
    soh.SalesOrderNumber,
    soh.OrderDate,
    cf.Name AS FromCurrency,
    ct.Name AS ToCurrency,
    cr.AverageRate,
    ship_cr.Name AS ShipCountry,
    ship_sp.Name AS ShipState,
    bill_sp.Name AS BillState,
    cc.CardType,
    sm.Name AS ShipMethod,
    ROUND(soh.TotalDue, 2) AS OrderTotal
FROM CurrencyRate cr
JOIN Currency cf ON cr.FromCurrencyCode = cf.CurrencyCode
JOIN Currency ct ON cr.ToCurrencyCode = ct.CurrencyCode
JOIN SalesOrderHeader soh ON cr.CurrencyRateID = soh.CurrencyRateID
JOIN Address ship_a ON soh.ShipToAddressID = ship_a.AddressID
JOIN StateProvince ship_sp ON ship_a.StateProvinceID = ship_sp.StateProvinceID
JOIN CountryRegion ship_cr ON ship_sp.CountryRegionCode = ship_cr.CountryRegionCode
JOIN Address bill_a ON soh.BillToAddressID = bill_a.AddressID
JOIN StateProvince bill_sp ON bill_a.StateProvinceID = bill_sp.StateProvinceID
LEFT JOIN CreditCard cc ON soh.CreditCardID = cc.CreditCardID
JOIN ShipMethod sm ON soh.ShipMethodID = sm.ShipMethodID
ORDER BY soh.OrderDate DESC;
```

---

**Q5: "For each salesperson handling international orders, show their name, department, territory, the currencies they deal with, total international revenue, and the average exchange rate they operated under."**

*10 joins: CurrencyRate → Currency(from) → Currency(to) → SalesOrderHeader → SalesPerson → Employee → Person → EmployeeDepartmentHistory → Department → SalesTerritory*

```sql
SELECT
    per.FirstName || ' ' || per.LastName AS SalesPersonName,
    d.Name AS Department,
    st.Name AS Territory,
    cf.Name AS FromCurrency,
    ct.Name AS ToCurrency,
    COUNT(DISTINCT soh.SalesOrderID) AS InternationalOrders,
    ROUND(SUM(soh.TotalDue), 2) AS TotalFXRevenue,
    ROUND(AVG(cr.AverageRate), 4) AS AvgExchangeRate,
    ROUND(SUM(soh.TotalDue / cr.AverageRate), 2) AS EstimatedBaseRevenue
FROM CurrencyRate cr
JOIN Currency cf ON cr.FromCurrencyCode = cf.CurrencyCode
JOIN Currency ct ON cr.ToCurrencyCode = ct.CurrencyCode
JOIN SalesOrderHeader soh ON cr.CurrencyRateID = soh.CurrencyRateID
JOIN SalesPerson sp ON soh.SalesPersonID = sp.BusinessEntityID
JOIN Employee e ON sp.BusinessEntityID = e.BusinessEntityID
JOIN Person per ON e.BusinessEntityID = per.BusinessEntityID
JOIN EmployeeDepartmentHistory edh ON e.BusinessEntityID = edh.BusinessEntityID
    AND edh.EndDate IS NULL
JOIN Department d ON edh.DepartmentID = d.DepartmentID
JOIN SalesTerritory st ON soh.TerritoryID = st.TerritoryID
GROUP BY per.FirstName, per.LastName, d.Name, st.Name, cf.Name, ct.Name
ORDER BY TotalFXRevenue DESC;
```

---

### Practical Business Use-Case Queries (5)

---

**Q6: "Which currency pairs are tracked, and how many daily rate records exist for each?"**

*Use case: Data inventory — FX coverage*

```sql
SELECT
    FromCurrencyCode,
    ToCurrencyCode,
    COUNT(*) AS RateDays,
    MIN(CurrencyRateDate) AS FirstRateDate,
    MAX(CurrencyRateDate) AS LastRateDate,
    ROUND(AVG(AverageRate), 4) AS OverallAvgRate,
    ROUND(MIN(AverageRate), 4) AS LowestRate,
    ROUND(MAX(AverageRate), 4) AS HighestRate,
    ROUND(MAX(AverageRate) - MIN(AverageRate), 4) AS RateSpread
FROM CurrencyRate
GROUP BY FromCurrencyCode, ToCurrencyCode
ORDER BY RateDays DESC;
```

---

**Q7: "How has each currency pair's exchange rate trended month over month?"**

*Use case: Finance — FX trend monitoring*

```sql
SELECT
    strftime('%Y-%m', CurrencyRateDate) AS RateMonth,
    FromCurrencyCode,
    ToCurrencyCode,
    ROUND(AVG(AverageRate), 4) AS MonthlyAvgRate,
    ROUND(AVG(EndOfDayRate), 4) AS MonthlyAvgEODRate,
    ROUND(MAX(AverageRate) - MIN(AverageRate), 4) AS IntraMonthVolatility,
    COUNT(*) AS TradingDays
FROM CurrencyRate
GROUP BY strftime('%Y-%m', CurrencyRateDate), FromCurrencyCode, ToCurrencyCode
ORDER BY FromCurrencyCode, ToCurrencyCode, RateMonth;
```

---

**Q8: "What's the biggest single-day rate change for each currency pair — high volatility days?"**

*Use case: Risk management — FX volatility detection*

```sql
WITH DailyChange AS (
    SELECT
        CurrencyRateID,
        CurrencyRateDate,
        FromCurrencyCode,
        ToCurrencyCode,
        AverageRate,
        LAG(AverageRate) OVER (
            PARTITION BY FromCurrencyCode, ToCurrencyCode
            ORDER BY CurrencyRateDate
        ) AS PrevDayRate,
        AverageRate - LAG(AverageRate) OVER (
            PARTITION BY FromCurrencyCode, ToCurrencyCode
            ORDER BY CurrencyRateDate
        ) AS DailyChange
    FROM CurrencyRate
)
SELECT
    CurrencyRateDate,
    FromCurrencyCode,
    ToCurrencyCode,
    PrevDayRate,
    AverageRate AS CurrentRate,
    ROUND(DailyChange, 4) AS RateChange,
    ROUND(ABS(DailyChange) * 100.0 / NULLIF(PrevDayRate, 0), 2) AS PctChange
FROM DailyChange
WHERE DailyChange IS NOT NULL
ORDER BY ABS(DailyChange) DESC
LIMIT 20;
```

---

**Q9: "How much spread exists between the AverageRate and EndOfDayRate on each day — are they significantly different?"**

*Use case: Finance — intraday rate volatility assessment*

```sql
SELECT
    FromCurrencyCode,
    ToCurrencyCode,
    COUNT(*) AS TotalDays,
    ROUND(AVG(ABS(EndOfDayRate - AverageRate)), 6) AS AvgDailySpread,
    ROUND(MAX(ABS(EndOfDayRate - AverageRate)), 6) AS MaxDailySpread,
    ROUND(AVG(ABS(EndOfDayRate - AverageRate) * 100.0 / NULLIF(AverageRate, 0)), 4) AS AvgSpreadPct,
    SUM(CASE
        WHEN ABS(EndOfDayRate - AverageRate) * 100.0 / NULLIF(AverageRate, 0) > 1.0
        THEN 1 ELSE 0
    END) AS DaysWithOver1PctSpread
FROM CurrencyRate
GROUP BY FromCurrencyCode, ToCurrencyCode
ORDER BY AvgSpreadPct DESC;
```

---

**Q10: "How many sales orders used a currency conversion vs. base currency, and what's the revenue split?"**

*Use case: International business mix analysis*

```sql
SELECT
    CASE
        WHEN CurrencyRateID IS NOT NULL THEN 'International (FX Conversion)'
        ELSE 'Domestic (Base Currency)'
    END AS OrderType,
    COUNT(*) AS OrderCount,
    ROUND(SUM(TotalDue), 2) AS TotalRevenue,
    ROUND(AVG(TotalDue), 2) AS AvgOrderValue,
    ROUND(SUM(Freight), 2) AS TotalFreight,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM SalesOrderHeader), 2) AS PctOfOrders,
    ROUND(SUM(TotalDue) * 100.0 / (SELECT SUM(TotalDue) FROM SalesOrderHeader), 2) AS PctOfRevenue
FROM SalesOrderHeader
GROUP BY CASE WHEN CurrencyRateID IS NOT NULL THEN 'International (FX Conversion)' ELSE 'Domestic (Base Currency)' END;
```

---
