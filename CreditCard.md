# CreditCard

---

## 📋 Short Description

### Style 1: Conceptual Summary
This table stores credit card records — one row per card (19,118 cards). It captures the card type (CardType — e.g., Visa, MasterCard), the card number (CardNumber — unique), and expiration details (ExpMonth, ExpYear). Credit cards are linked to people via the PersonCreditCard junction table and to sales orders via SalesOrderHeader.CreditCardID. This is the payment instrument table — it tells you how customers pay for orders.

### Style 2: Query Possibilities & Business Story
This is the payment card table — every credit card used by any person in the system is stored here. A person can have multiple cards, and a card is linked to sales orders when used as the payment method. Use this table to answer questions like:

- "How many credit cards are in the system by card type (Visa, MasterCard, etc.)?"
- "Which card type is used most frequently for orders?" (with SalesOrderHeader)
- "How many cards are expired?"
- "What's the average order value by card type?" (with SalesOrderHeader)
- "How many people have multiple credit cards on file?" (with PersonCreditCard)
- "What percentage of sales revenue comes from each card type?"
- "Which card type generates the highest total revenue?"
- "Are there cards on file that have never been used for an order?"
- "What's the distribution of card expiration years — how many cards expire soon?"
- "How many orders were placed with expired cards?"
- "Which salesperson's orders use which card types most?" (with SalesOrderHeader, SalesPerson)
- "What's the revenue by card type and territory?" (with SalesOrderHeader, SalesTerritory)

Each card links to people via PersonCreditCard (many-to-many — a person can have multiple cards and theoretically a card could be shared) and to sales orders via SalesOrderHeader.CreditCardID (nullable — not all orders use a credit card).

### Style 3: Grouped & Complete (Column Reference)
This table stores one row per credit card (19,118 rows), containing 6 columns organized as:

- **Identifiers:** CreditCardID (PK, auto-increment), CardNumber (unique — the full/masked card number)
- **Card Details:** CardType (e.g., Vista, SuperiorCard, ColonialVoice, Distinguish — AdventureWorks fictional types)
- **Expiration:** ExpMonth (1–12), ExpYear (4-digit year)
- **Audit:** ModifiedDate

---

## 📖 Extensive Description

### Purpose & Business Context

CreditCard stores the 19,118 payment cards registered in the system. In AdventureWorks, credit cards are the primary payment method for sales orders. The table is intentionally simple — it stores card metadata (type, number, expiration) without sensitive data like CVV or cardholder name (the cardholder identity comes from the Person table via PersonCreditCard).

The card types in AdventureWorks are fictional: Vista, SuperiorCard, ColonialVoice, Distinguish (analogous to real-world Visa, MasterCard, American Express, Discover). Analyzing order patterns by card type can reveal customer demographics and payment preferences.

Cards connect to the system in two ways:
1. **PersonCreditCard** — links cards to people (ownership)
2. **SalesOrderHeader.CreditCardID** — links cards to specific orders (usage)

Not all orders have a credit card (CreditCardID is nullable on SalesOrderHeader) — some orders may use other payment methods or be B2B/store orders on account.

### Key Business Logic

- **CardNumber is unique** — each physical card appears only once
- **CardType** values are fictional: 'Vista', 'SuperiorCard', 'ColonialVoice', 'Distinguish'
- **Card is expired** when ExpYear < current year, or ExpYear = current year AND ExpMonth < current month
- **PersonCreditCard is many-to-many** — one person can have multiple cards; in theory one card could link to multiple people
- **SalesOrderHeader.CreditCardID = NULL** → order didn't use a credit card
- **19,118 cards ≈ 19,118 PersonCreditCard links ≈ 19,972 people** — almost 1:1, most people have exactly one card
- No financial amounts stored here — dollar values come from SalesOrderHeader/SalesOrderDetail

### Relationships

| Direction | Table | Join Key | Notes |
|-----------|-------|----------|-------|
| ← Junction | PersonCreditCard → Person | CreditCardID | Who owns this card |
| ← Referenced by | SalesOrderHeader (31,465) | CreditCardID | Orders paid with this card (nullable) |
| ← Via SalesOrderHeader | Customer → Person / Store | CustomerID | Customer who used this card |
| ← Via SalesOrderHeader | SalesPerson → Employee → Person | SalesPersonID | Rep on the order |
| ← Via SalesOrderHeader | SalesTerritory | TerritoryID | Territory of the order |
| ← Via SalesOrderHeader | SalesOrderDetail → Product | SalesOrderID | Products purchased with this card |
| ← Via PersonCreditCard → Person | EmailAddress | BusinessEntityID | Cardholder's email |
| ← Via PersonCreditCard → Person | BusinessEntityAddress → Address | BusinessEntityID | Cardholder's address |

---

## 🔗 10 NL → SQL Examples

### Join-Heavy Queries (5)

---

**Q1: "For each credit card, show the card type, masked card number, the cardholder's name and email, their address city/state/country, and whether the card is expired."**

*8 joins: CreditCard → PersonCreditCard → Person → EmailAddress → BusinessEntityAddress → Address → StateProvince → CountryRegion*

```sql
SELECT
    cc.CreditCardID,
    cc.CardType,
    '****' || SUBSTR(cc.CardNumber, -4) AS MaskedCardNumber,
    cc.ExpMonth || '/' || cc.ExpYear AS Expiration,
    CASE
        WHEN cc.ExpYear < CAST(strftime('%Y', 'now') AS INTEGER)
            OR (cc.ExpYear = CAST(strftime('%Y', 'now') AS INTEGER)
                AND cc.ExpMonth < CAST(strftime('%m', 'now') AS INTEGER))
        THEN 'EXPIRED'
        ELSE 'ACTIVE'
    END AS CardStatus,
    per.FirstName || ' ' || per.LastName AS CardholderName,
    ea.EmailAddress,
    a.City,
    sp.Name AS State,
    cr.Name AS Country
FROM CreditCard cc
JOIN PersonCreditCard pcc ON cc.CreditCardID = pcc.CreditCardID
JOIN Person per ON pcc.BusinessEntityID = per.BusinessEntityID
LEFT JOIN EmailAddress ea ON per.BusinessEntityID = ea.BusinessEntityID
LEFT JOIN BusinessEntityAddress bea ON per.BusinessEntityID = bea.BusinessEntityID
LEFT JOIN Address a ON bea.AddressID = a.AddressID
LEFT JOIN StateProvince sp ON a.StateProvinceID = sp.StateProvinceID
LEFT JOIN CountryRegion cr ON sp.CountryRegionCode = cr.CountryRegionCode
ORDER BY cc.CardType, per.LastName;
```

---

**Q2: "Show each credit card's usage: card type, cardholder name, total orders placed with it, total revenue, the salesperson on those orders, and the territories where it was used."**

*8 joins: CreditCard → SalesOrderHeader → Customer → Person(customer) → SalesPerson → Employee → Person(rep) → SalesTerritory*

```sql
SELECT
    cc.CardType,
    '****' || SUBSTR(cc.CardNumber, -4) AS MaskedCard,
    cust.FirstName || ' ' || cust.LastName AS CustomerName,
    rep.FirstName || ' ' || rep.LastName AS SalesPersonName,
    st.Name AS Territory,
    COUNT(DISTINCT soh.SalesOrderID) AS OrderCount,
    ROUND(SUM(soh.TotalDue), 2) AS TotalRevenue,
    ROUND(AVG(soh.TotalDue), 2) AS AvgOrderValue
FROM CreditCard cc
JOIN SalesOrderHeader soh ON cc.CreditCardID = soh.CreditCardID
JOIN Customer c ON soh.CustomerID = c.CustomerID
LEFT JOIN Person cust ON c.PersonID = cust.BusinessEntityID
LEFT JOIN SalesPerson sp ON soh.SalesPersonID = sp.BusinessEntityID
LEFT JOIN Employee e ON sp.BusinessEntityID = e.BusinessEntityID
LEFT JOIN Person rep ON e.BusinessEntityID = rep.BusinessEntityID
JOIN SalesTerritory st ON soh.TerritoryID = st.TerritoryID
GROUP BY cc.CreditCardID, cc.CardType, cc.CardNumber, cust.FirstName,
         cust.LastName, rep.FirstName, rep.LastName, st.Name
ORDER BY TotalRevenue DESC;
```

---

**Q3: "For each card type, show the top-selling product categories purchased with that card type, including total units sold, revenue, and the average discount applied."**

*8 joins: CreditCard → SalesOrderHeader → SalesOrderDetail → SpecialOfferProduct → SpecialOffer → Product → ProductSubcategory → ProductCategory*

```sql
SELECT
    cc.CardType,
    pcat.Name AS ProductCategory,
    SUM(sod.OrderQty) AS TotalUnitsSold,
    ROUND(SUM(sod.LineTotal), 2) AS TotalRevenue,
    ROUND(AVG(sod.UnitPriceDiscount) * 100, 2) AS AvgDiscountPct,
    COUNT(DISTINCT soh.SalesOrderID) AS OrderCount,
    so.Description AS MostCommonPromotion
FROM CreditCard cc
JOIN SalesOrderHeader soh ON cc.CreditCardID = soh.CreditCardID
JOIN SalesOrderDetail sod ON soh.SalesOrderID = sod.SalesOrderID
JOIN Product p ON sod.ProductID = p.ProductID
LEFT JOIN ProductSubcategory psub ON p.ProductSubcategoryID = psub.ProductSubcategoryID
LEFT JOIN ProductCategory pcat ON psub.ProductCategoryID = pcat.ProductCategoryID
JOIN SpecialOfferProduct sop ON sod.SpecialOfferID = sop.SpecialOfferID
    AND sod.ProductID = sop.ProductID
JOIN SpecialOffer so ON sop.SpecialOfferID = so.SpecialOfferID
GROUP BY cc.CardType, pcat.Name, so.Description
ORDER BY cc.CardType, TotalRevenue DESC;
```

---

**Q4: "Show credit cards used for international orders (with currency conversion): card type, cardholder, the currency pair, exchange rate, ship country, and total order value."**

*10 joins: CreditCard → SalesOrderHeader → CurrencyRate → Currency(from) → Currency(to) → Customer → Person → Address(ship) → StateProvince → CountryRegion*

```sql
SELECT
    cc.CardType,
    '****' || SUBSTR(cc.CardNumber, -4) AS MaskedCard,
    per.FirstName || ' ' || per.LastName AS CustomerName,
    cf.Name AS FromCurrency,
    ct.Name AS ToCurrency,
    cr.AverageRate,
    ship_cr.Name AS ShipCountry,
    ROUND(soh.TotalDue, 2) AS OrderTotal,
    ROUND(soh.TotalDue / cr.AverageRate, 2) AS EstBaseCurrencyTotal
FROM CreditCard cc
JOIN SalesOrderHeader soh ON cc.CreditCardID = soh.CreditCardID
JOIN CurrencyRate cr ON soh.CurrencyRateID = cr.CurrencyRateID
JOIN Currency cf ON cr.FromCurrencyCode = cf.CurrencyCode
JOIN Currency ct ON cr.ToCurrencyCode = ct.CurrencyCode
JOIN Customer c ON soh.CustomerID = c.CustomerID
LEFT JOIN Person per ON c.PersonID = per.BusinessEntityID
JOIN Address ship_a ON soh.ShipToAddressID = ship_a.AddressID
JOIN StateProvince ship_sp ON ship_a.StateProvinceID = ship_sp.StateProvinceID
JOIN CountryRegion ship_cr ON ship_sp.CountryRegionCode = ship_cr.CountryRegionCode
ORDER BY soh.OrderDate DESC;
```

---

**Q5: "For cardholders who are also employees, show their name, job title, department, card type, and the total amount they've spent as customers — linking their employee identity to their customer spending."**

*10 joins: CreditCard → PersonCreditCard → Person → Employee → EmployeeDepartmentHistory → Department → Customer → SalesOrderHeader → SalesTerritory*

```sql
SELECT
    per.FirstName || ' ' || per.LastName AS EmployeeName,
    e.JobTitle,
    d.Name AS Department,
    cc.CardType,
    cc.ExpMonth || '/' || cc.ExpYear AS Expiration,
    COUNT(DISTINCT soh.SalesOrderID) AS OrdersAsCustomer,
    ROUND(SUM(soh.TotalDue), 2) AS TotalSpentAsCustomer,
    st.Name AS OrderTerritory
FROM CreditCard cc
JOIN PersonCreditCard pcc ON cc.CreditCardID = pcc.CreditCardID
JOIN Person per ON pcc.BusinessEntityID = per.BusinessEntityID
JOIN Employee e ON per.BusinessEntityID = e.BusinessEntityID
JOIN EmployeeDepartmentHistory edh ON e.BusinessEntityID = edh.BusinessEntityID
    AND edh.EndDate IS NULL
JOIN Department d ON edh.DepartmentID = d.DepartmentID
LEFT JOIN Customer c ON per.BusinessEntityID = c.PersonID
LEFT JOIN SalesOrderHeader soh ON c.CustomerID = soh.CustomerID
    AND soh.CreditCardID = cc.CreditCardID
LEFT JOIN SalesTerritory st ON soh.TerritoryID = st.TerritoryID
GROUP BY per.FirstName, per.LastName, e.JobTitle, d.Name, cc.CardType,
         cc.ExpMonth, cc.ExpYear, st.Name
ORDER BY TotalSpentAsCustomer DESC;
```

---

### Practical Business Use-Case Queries (5)

---

**Q6: "What's the breakdown of credit cards by card type — total cards, percentage of total, and how many are expired?"**

*Use case: Payment operations — card portfolio overview*

```sql
SELECT
    CardType,
    COUNT(*) AS TotalCards,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM CreditCard), 2) AS PctOfTotal,
    SUM(CASE
        WHEN ExpYear < CAST(strftime('%Y', 'now') AS INTEGER)
            OR (ExpYear = CAST(strftime('%Y', 'now') AS INTEGER)
                AND ExpMonth < CAST(strftime('%m', 'now') AS INTEGER))
        THEN 1 ELSE 0
    END) AS ExpiredCards,
    SUM(CASE
        WHEN ExpYear = CAST(strftime('%Y', 'now') AS INTEGER)
            AND ExpMonth >= CAST(strftime('%m', 'now') AS INTEGER)
        THEN 1 ELSE 0
    END) AS ExpiringThisYear,
    MIN(ExpYear) AS OldestExpYear,
    MAX(ExpYear) AS NewestExpYear
FROM CreditCard
GROUP BY CardType
ORDER BY TotalCards DESC;
```

---

**Q7: "What's the revenue and order volume by card type — which card type drives the most business?"**

*Use case: Finance — payment method revenue analysis*

```sql
SELECT
    cc.CardType,
    COUNT(DISTINCT soh.SalesOrderID) AS OrderCount,
    COUNT(DISTINCT soh.CustomerID) AS UniqueCustomers,
    ROUND(SUM(soh.TotalDue), 2) AS TotalRevenue,
    ROUND(AVG(soh.TotalDue), 2) AS AvgOrderValue,
    ROUND(SUM(soh.TotalDue) * 100.0 / (
        SELECT SUM(TotalDue) FROM SalesOrderHeader WHERE CreditCardID IS NOT NULL
    ), 2) AS RevenueSharePct
FROM CreditCard cc
JOIN SalesOrderHeader soh ON cc.CreditCardID = soh.CreditCardID
GROUP BY cc.CardType
ORDER BY TotalRevenue DESC;
```

---

**Q8: "How many cards on file have never been used for a sales order?"**

*Use case: Data cleanup — identifying dormant cards*

```sql
SELECT
    cc.CardType,
    COUNT(*) AS UnusedCards,
    cc.ExpMonth || '/' || cc.ExpYear AS SampleExpiration,
    CASE
        WHEN cc.ExpYear < CAST(strftime('%Y', 'now') AS INTEGER)
        THEN 'EXPIRED & UNUSED'
        ELSE 'ACTIVE & UNUSED'
    END AS Status
FROM CreditCard cc
LEFT JOIN SalesOrderHeader soh ON cc.CreditCardID = soh.CreditCardID
WHERE soh.SalesOrderID IS NULL
GROUP BY cc.CardType, Status
ORDER BY UnusedCards DESC;
```

---

**Q9: "What's the expiration year distribution — how many cards expire each year, and what revenue is at risk from expiring cards?"**

*Use case: Customer retention — proactive card renewal outreach*

```sql
SELECT
    cc.ExpYear,
    COUNT(DISTINCT cc.CreditCardID) AS CardsExpiring,
    COUNT(DISTINCT soh.SalesOrderID) AS OrdersOnTheseCards,
    ROUND(SUM(soh.TotalDue), 2) AS RevenueOnTheseCards,
    ROUND(AVG(soh.TotalDue), 2) AS AvgOrderValue
FROM CreditCard cc
LEFT JOIN SalesOrderHeader soh ON cc.CreditCardID = soh.CreditCardID
GROUP BY cc.ExpYear
ORDER BY cc.ExpYear;
```

---

