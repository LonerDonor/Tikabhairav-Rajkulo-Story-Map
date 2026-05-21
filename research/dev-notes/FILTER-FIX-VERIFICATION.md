# Filter Layering Fix - Verification Guide

## Change Summary
Fixed the filter system to work as **independent overlaying layers** instead of exclusive/restrictive filters.

### Previous Behavior (Broken)
- A surveyed section was **only shown** if ALL of these were true:
  1. "Surveyed Sections" feature was selected
  2. Its flow type was in the selected flow types
  3. Its condition was in the selected conditions
- This meant deselecting a flow type or condition would hide all matching sections

### New Behavior (Fixed)
- A surveyed section is shown if:
  1. "Surveyed Sections" feature is selected AND
  2. (No flow filters selected OR its flow type matches) AND
  3. (No condition filters selected OR its condition matches)
- This means deselecting ALL flow filters shows all flows, and deselecting ALL conditions shows all conditions

---

## Test Cases

### Test 1: Default View (All Filters Active)
**Setup:** Page loads with all filters checked
- ✅ Should show all 95 surveyed sections
- ✅ Should show historic branches (if checked)
- ✅ Should show all POIs
- ✅ Filter stats should show "Showing 95 / 95 sections"

**How to test:**
1. Load http://localhost:8000
2. Click "Explore the map"
3. Observe the map — should be fully populated

---

### Test 2: Historic Branches Overlay (Key Fix)
**Setup:** Both "Surveyed Sections" AND "Historic Branches" are checked
- ✅ Historic branches (orange) should overlay on top of surveyed sections
- ✅ Both layers should be visible simultaneously
- ✅ Sections that are part of the historic network should show in BOTH colors

**How to test:**
1. Map loaded with all features active
2. Toggle "Historic Branches" ON if not already
3. Toggle "Historic Branches" OFF
4. Toggle "Historic Branches" ON again
5. Observe: Orange historic branches should appear and disappear without affecting colored surveyed sections

---

### Test 3: Deselect All Flow Types (Critical Fix)
**Setup:** Uncheck Perennial, Seasonal, and Other (all flow filters deselected)
- ✅ All 95 surveyed sections should STILL be visible
- ✅ Filter stats should still show "Showing 95 / 95 sections"
- ⚠️ This was broken before: deselecting all flows would hide ALL sections

**How to test:**
1. Map loaded with default filters
2. Uncheck "Perennial"
3. Uncheck "Seasonal"
4. Uncheck "Other"
5. Observe: Colored sections should remain visible (filter disabled because empty)
6. Re-check "Perennial" only
7. Observe: Only perennial sections (those in their colors) should show
8. Re-check "Seasonal" 
9. Observe: Both Perennial and Seasonal sections show

---

### Test 4: Deselect All Conditions (Critical Fix)
**Setup:** Click the condition legend chips to deselect all conditions
- ✅ All 95 surveyed sections should STILL be visible
- ✅ Filter stats should still show "Showing 95 / 95 sections"
- ⚠️ This was broken before: deselecting all conditions would hide ALL sections

**How to test:**
1. Map loaded with default filters
2. Click the "Good" condition chip (turns off)
3. Click the "Fair" condition chip (turns off)
4. Click the "Poor" condition chip (turns off)
5. Click the "Critical" condition chip (turns off)
6. Click the "Underground" condition chip (turns off)
7. Click the "Lost" condition chip (turns off)
8. Observe: All sections still visible (filter disabled because empty)
9. Click "Good" to select it again
10. Observe: Only "Good" condition sections show (bright green)

---

### Test 5: Flow + Condition Filtering Together
**Setup:** Select only "Perennial" flow type AND only "Good" condition
- ✅ Should show only Perennial sections in Good condition
- ✅ Filter stats should show a smaller count (e.g., "Showing 45 / 95 sections")

**How to test:**
1. Uncheck "Seasonal" and "Other" (leave "Perennial" checked)
2. Deselect all conditions except "Good"
3. Observe: Map shows fewer sections (only Perennial + Good)
4. Re-check "Seasonal"
5. Observe: More sections appear (Perennial in Good + Seasonal in Good)

---

### Test 6: Feature Independence
**Setup:** Toggle individual features on/off while others remain active
- ✅ Unchecking "Surveyed Sections" hides colored sections but keeps historic branches, POIs, and labels
- ✅ Unchecking "Historic Branches" hides orange branches but keeps surveyed sections
- ✅ Unchecking "POIs" hides colored dot markers

**How to test:**
1. Start with all features active
2. Uncheck "Surveyed Sections" → orange historic and POIs remain visible
3. Re-check "Surveyed Sections" → colored sections reappear
4. Uncheck "Historic Branches" → orange disappears but colored sections and POIs stay
5. Re-check "Historic Branches" → orange reappears
6. Uncheck "Points of interest" → POI dots disappear

---

### Test 7: Complex Scenario (Overlapping Data)
**Setup:** A canal section that appears in both surveyed AND historic network
- ✅ When both "Surveyed Sections" and "Historic Branches" are checked, the overlapping area should be visible in both representations
- ✅ Toggling flow/condition filters should affect the surveyed color but not remove the historic branch line

**How to test:**
1. Find a surveyed section that overlaps with a historic branch (observe orange on top of colored)
2. Deselect all flow types (or conditions)
3. Observe: Colored section layer disappears but ORANGE HISTORIC BRANCH REMAINS
4. This proves they are truly independent layers

---

## Success Criteria

✅ **All tests should pass for a successful fix:**

- [ ] Test 1: Default view shows all sections
- [ ] Test 2: Historic branches overlay correctly with surveyed sections
- [ ] Test 3: Deselecting all flow types still shows surveyed sections
- [ ] Test 4: Deselecting all conditions still shows surveyed sections
- [ ] Test 5: Combined flow + condition filtering works correctly
- [ ] Test 6: Features toggle independently
- [ ] Test 7: Overlapping data (surveyed + historic) displays in both layers

## Implementation Details

The fix changed three key locations in `app.js`:

1. **Lines 23-24**: Added constants to track all possible filter values
   ```javascript
   const FLOW_OPTIONS = new Set(['Perennial', 'Seasonal', 'Other']);
   const CONDITION_OPTIONS = new Set(['Good', 'Fair', 'Poor', 'Critical', 'Underground', 'Lost']);
   ```

2. **Lines 259-261** (applyFilters function): Changed filter logic from AND to conditional
   ```javascript
   const flowMatches = filterState.flow.size === 0 || filterState.flow.has(bucket);
   const conditionMatches = filterState.conditions.size === 0 || filterState.conditions.has(section.condition);
   show = flowMatches && conditionMatches;
   ```
   - If `filterState.flow.size === 0` (no flow filters selected), the condition is true (don't restrict)
   - If filters are selected, only allow matching flows
   - Same logic for conditions

3. **Lines 311-312** (fitToVisible function): Applied same logic for zoom-to-visible

## Key Insight

The fix uses a simple principle: **An empty filter set means "don't filter on this property"**

- When user deselects ALL flows → `filterState.flow.size === 0` → show all flows
- When user selects SOME flows → `filterState.flow.size > 0` → only show selected flows
- Same for conditions

This maintains backward compatibility (default all checked = show all) while fixing the exclusive behavior.
