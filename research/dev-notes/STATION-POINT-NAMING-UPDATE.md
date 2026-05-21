# Station Point Naming Update — Summary

## Overview
Replaced vague "index point" terminology with **"Station Point"** — a standard hydraulic engineering term that is both meaningful on maps and in documentation.

---

## What Changed

### 1. **Excel Sheet Update** ✅
**File:** `C:\Users\olenepal\Downloads\Rajkulo All Documents\Rajkulo All Documents\RajkuloSurvey\CANAL_Survey.xlsx`

- **New Column:** Column AH labeled "Station Point"
- **Format:** Standard survey chainage notation: `{km}+{m:03d} m`
- **Examples:**
  - `0+014 m` (Intake)
  - `0+450 m` (Chapagaon section)
  - `5+200 m` (Thecho section)
  - `13+000 m` (Terminal sections)

Each Station Point automatically includes the location name in parentheses when available:
- `0+014 m (Intake)`
- `3+450 m (Chapagaon)`

---

### 2. **Website Detail View Update** ✅
**File:** `Story map Tikabhairav/app.js` (lines 383-425)

#### What users now see when they click a section:

**Before:**
```
Section 1 · Intake
Mergin fid #4

Chainage: 14.2649 m
Section length: 14.26 m
...
```

**After:**
```
Section 1 · Intake
Station Point 0+014 m · Mergin fid #4

┌─────────────────────────────────────────┐
│ Station Point │ 0+014 m                 │
│ Chainage      │ 14.2649 m               │
│ Section length│ 14.26 m                 │
│ Elevation (Z) │ 1477.16 m ASL           │
│ Water quality │ River Quality           │
│ ... (other properties)                  │
└─────────────────────────────────────────┘
```

#### Key improvements:
1. ✅ **Header displays Station Point** — immediately visible when opening a section
2. ✅ **Dedicated grid cell** for "Station Point" — users understand what it is
3. ✅ **Chainage notation** `0+450 m` — follows standard survey conventions
4. ✅ **Meaningful on maps** — directly indicates location along 13 km canal

---

## Naming Options Evaluated

| Option | Definition | Use Case | Pros | Cons |
|--------|-----------|----------|------|------|
| **Station Point** ⭐ | Surveyed location on canal at specific chainage | Field surveys, technical docs | Standard term, precise, on maps | Less casual |
| Chainage | Distance along canal from intake | Engineering calculations | Exact, quantifiable | Not a "point" |
| Section Chainage | Same as chainage but section-specific | Clarity in multi-section docs | Clear | Redundant with data |
| Survey Station | Specific field survey location | Academic/technical | Formal | Generic term |
| Map Location | Location on the map | General audiences | User-friendly | Vague |

**Recommendation:** "Station Point" balances **precision** (engineers understand it), **accessibility** (users can see it on the map), and **formality** (appropriate for heritage documentation).

---

## Technical Details

### Station Point Calculation
```javascript
// From chainage value (e.g., 14.2649)
const km = Math.floor(14.2649 / 1000);  // 0
const m = Math.round(14.2649 % 1000);   // 14
const stationPoint = `${km}+${String(m).padStart(3, '0')} m`;  // "0+014 m"
```

### Chainage Notation Explained
- **0+450 m** = Station 0, 450 meters = 450m from intake
- **5+200 m** = Station 5, 200 meters = 5,200m from intake
- Standard in:
  - Road and railway surveying
  - Canal and pipeline engineering
  - Hydraulic infrastructure projects

---

## Impact on Other Views

| View | Change | Status |
|------|--------|--------|
| **Detail Panel** (click section) | Shows "Station Point 0+450 m" in header and data grid | ✅ Updated |
| **Index/List Panel** | Still shows Section #, Chainage, Condition | No change needed |
| **Search Results** | Still searchable by Section #, Tole, fid | No change |
| **Tooltips on Map** | Shows "Section #1 · Intake" | No change needed |
| **Excel Source Data** | New column AH with Station Point values | ✅ Added |
| **URL Deep Links** | Still use pdf_n (Section #) for stability | No change |

---

## Next Steps (Optional)

If you want to further enhance the documentation:

1. **Add to HTML metadata** — Include Station Point in page descriptions for SEO
2. **Update Index labels** — Show Station Point in the index list alongside Chainage
3. **Build a station directory** — Create a printable PDF listing all stations by chainage
4. **Mobile app notation** — Consider abbreviating to "Stn 0+450 m" on smaller screens

---

## Sources & References

[Understanding Survey Distances - AiWorldwide](https://support.aiworldwide.com/products/cn1/content/feat_indirectsurvey/sm_fields.htm)  
[Chain Surveying - Definition and Procedure](https://civiltoday.com/surveying/242-chain-surveying)  
[River Modelling Technical Standards - UK Government](https://www.gov.uk/government/publications/river-modelling-technical-standards-and-assessment/represent-river-channels-floodplains-and-pipe-networks-pathway)

---

## Testing

To verify the changes:

1. **Open http://localhost:8000**
2. **Click any surveyed section on the map**
3. **Verify in the Detail panel:**
   - Header shows "Station Point 0+XXX m"
   - Data grid has dedicated "Station Point" row
   - Value format is correct: `{km}+{m:03d} m`

**Example expected outputs:**
- Section 1 (Intake) → Station Point: **0+014 m**
- Section 45 → Station Point: **3+450 m**  
- Section 88 → Station Point: **8+800 m**
