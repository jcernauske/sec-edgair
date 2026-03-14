## Data Profile: raw.xbrl_company_facts
**Source:** Iceberg table at data/raw/iceberg_warehouse
**Date:** 2026-03-14
**Agent:** @data-profiler
**Record Count:** 104,810
**Field Count:** 19

### Row Counts by CIK
| CIK | Rows |
|-----|------|
| 19617 | 48,657 |
| 789019 | 31,574 |
| 320193 | 24,579 |

### Field Profiles

#### cik
- **Distinct:** 3
- **Null Rate:** 0.0% (0/104,810)
- **Min:** 19617.0
- **Max:** 789019.0
- **Mean:** 321,887.3583
- **Top Values:** `19617` (48,657), `789019` (31,574), `320193` (24,579)

#### entity_name
- **Distinct:** 3
- **Null Rate:** 0.0% (0/104,810)
- **Length:** 10-21 (avg 17.5)
- **Top Values:** `JPMorgan Chase & Co` (48,657), `MICROSOFT CORPORATION` (31,574), `Apple Inc.` (24,579)

#### taxonomy
- **Distinct:** 4
- **Null Rate:** 0.0% (0/104,810)
- **Length:** 3-7 (avg 7.0)
- **Top Values:** `us-gaap` (104,406), `dei` (316), `invest` (70), `srt` (18)

#### concept
- **Distinct:** 1,409
- **Null Rate:** 0.0% (0/104,810)
- **Length:** 4-167 (avg 44.4)
- **Top Values:** `CommonStockDividendsPerShareDeclared` (942), `EarningsPerShareBasic` (893), `EarningsPerShareDiluted` (893), `NetIncomeLoss` (893), `IncomeTaxExpenseBenefit` (681)

#### label
- **Distinct:** 1,371
- **Null Rate:** 0.9% (998/104,810)
- **Length:** 4-193 (avg 53.9)
- **Top Values:** `Common Stock, Dividends, Per Share, Declared` (942), `Earnings Per Share, Basic` (893), `Earnings Per Share, Diluted` (893), `Net Income (Loss) Attributable to Parent` (893), `Income Tax Expense (Benefit)` (681)

#### description
- **Distinct:** 1,361
- **Null Rate:** 0.9% (998/104,810)
- **Length:** 32-1668 (avg 214.7)
- **Top Values:** `Aggregate dividends declared during the period for` (942), `The amount of net income (loss) for the period per` (893), `The amount of net income (loss) for the period ava` (893), `The portion of profit or loss for the period, net ` (893), `Amount of current income tax expense (benefit) and` (681)

#### unit
- **Distinct:** 17
- **Null Rate:** 0.0% (0/104,810)
- **Length:** 3-15 (avg 3.4)
- **Top Values:** `USD` (94,437), `shares` (4,615), `USD/shares` (3,647), `pure` (1,999), `segment` (47)

#### start_date
- **Distinct:** 140
- **Null Rate:** 40.5% (42,486/104,810)
- **Min:** 2006-10-01
- **Max:** 2025-10-01
- **Top Values:** `2011-01-01` (1,776), `2010-01-01` (1,718), `2012-01-01` (1,608), `2023-01-01` (1,602), `2022-01-01` (1,501)

#### end_date
- **Distinct:** 352
- **Null Rate:** 0.0% (0/104,810)
- **Min:** 2006-09-30
- **Max:** 2026-01-31
- **Top Values:** `2010-12-31` (2,028), `2022-12-31` (1,898), `2016-12-31` (1,878), `2012-06-30` (1,810), `2011-06-30` (1,797)

#### val
- **Distinct:** 26,716
- **Null Rate:** 0.0% (0/104,810)
- **Min:** -2952048000000.0
- **Max:** 80832000000000.0
- **Mean:** 131,619,834,833.5653
- **Top Values:** `0.0` (2,176), `1.0` (313), `1000000.0` (222), `200000000.0` (183), `1500000000.0` (165)

#### accession_number
- **Distinct:** 210
- **Null Rate:** 0.0% (0/104,810)
- **Length:** 20-20 (avg 20.0)
- **Top Values:** `0001628280-26-008131` (1,009), `0000019617-25-000270` (946), `0000019617-24-000225` (942), `0000019617-22-000272` (919), `0000019617-23-000231` (916)

#### fiscal_year
- **Distinct:** 18
- **Null Rate:** 1.7% (1,742/104,810)
- **Min:** 2009.0
- **Max:** 2026.0
- **Mean:** 2,017.4108
- **Top Values:** `2011` (6,968), `2012` (6,835), `2013` (6,648), `2015` (6,378), `2020` (6,367)

#### fiscal_period
- **Distinct:** 4
- **Null Rate:** 1.7% (1,742/104,810)
- **Length:** 2-2 (avg 2.0)
- **Top Values:** `FY` (34,902), `Q2` (25,079), `Q3` (24,617), `Q1` (18,470)

#### form
- **Distinct:** 5
- **Null Rate:** 0.0% (0/104,810)
- **Length:** 3-6 (avg 4.0)
- **Top Values:** `10-Q` (66,127), `10-K` (32,727), `8-K` (4,839), `10-Q/A` (907), `10-K/A` (210)

#### filed_date
- **Distinct:** 193
- **Null Rate:** 0.0% (0/104,810)
- **Min:** 2009-07-22
- **Max:** 2026-02-13
- **Top Values:** `2011-11-04` (2,588), `2017-08-02` (1,693), `2024-10-30` (1,140), `2012-08-09` (1,088), `2024-08-02` (1,066)

#### frame
- **Distinct:** 170
- **Null Rate:** 59.2% (62,095/104,810)
- **Length:** 6-9 (avg 8.2)
- **Top Values:** `CY2010` (532), `CY2011` (512), `CY2012` (460), `CY2013` (460), `CY2009` (447)

#### ingested_at
- **Distinct:** 3
- **Null Rate:** 0.0% (0/104,810)
- **Min:** 2026-03-14 01:21:10.942987-05:00
- **Max:** 2026-03-14 01:21:11.151064-05:00
- **Top Values:** `2026-03-14 01:21:11.033193-05:00` (48,657), `2026-03-14 01:21:11.151064-05:00` (31,574), `2026-03-14 01:21:10.942987-05:00` (24,579)

#### source_url
- **Distinct:** 3
- **Null Rate:** 0.0% (0/104,810)
- **Length:** 61-61 (avg 61.0)
- **Top Values:** `https://data.sec.gov/api/xbrl/companyfacts/CIK0000` (48,657), `https://data.sec.gov/api/xbrl/companyfacts/CIK0000` (31,574), `https://data.sec.gov/api/xbrl/companyfacts/CIK0000` (24,579)

#### source_method
- **Distinct:** 1
- **Null Rate:** 0.0% (0/104,810)
- **Length:** 3-3 (avg 3.0)
- **Top Values:** `api` (104,810)
