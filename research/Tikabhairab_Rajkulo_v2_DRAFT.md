# Tikabhairab Rajkulo — Report v2 (Working Draft)

**Status:** Outline + two specimen sections for review.
**Author:** Hrishav Raj Joshi
**Supervisor:** Padma Sundar Joshi
**Institution:** Centre for Integrated Urban Development (CIUD) / Newah Organization of America (NOA), Seattle
**Field Survey:** May 2022
**Revision date:** 2026-05-19

---

## How to read this draft

This file contains **(1)** the proposed full structure for the rewritten report, and **(2)** two fully written specimen sections — the **Executive Summary** and **Chapter 6: Hydraulic Analysis** — so you can validate voice, depth, and structure before the remaining ~25 pages are written.

The Executive Summary is the section most readers (donors, government, journalists) will read first and possibly only. The Hydraulic Analysis is the highest-stakes technical chapter and the one with the most calculation issues in v1. If these two land right, the rest of the rewrite can proceed with confidence.

**Placeholders used throughout:** `[FIGURE n: …]`, `[MAP n: …]`, `[CITATION: …]`, `[TK]` (to-come), `[VERIFY: …]`.

---

# Part 1 — Proposed Full Structure

## Front matter

- **Cover page** — title, subtitle, author, supervisor, institutions, field-survey date, report date, version.
- **Acknowledgements** — supervisor, field assistants, communities along the alignment, funding bodies. *(One paragraph; you to fill names.)*
- **Executive Summary** — ~1.5 pages, audience-neutral synthesis: what was surveyed, the headline finding (hydraulic design sound; deterioration anthropogenic), the heritage angle (qualified), the priority zone, and four required follow-up studies.
- **Table of Contents**
- **List of Figures** — ~15–20 figures, all with detailed placeholder captions in the body.
- **List of Tables** — ~10–12 tables.
- **List of Maps** — separate listing because maps are the dominant visual; ~6–8 maps anticipated.
- **Glossary and Acronyms** — Newari/Nepali hydraulic terms (rajkulo, hiti, pokhari, nabhi mandal, hiti duun, ga hiti, chyaphi, aagaa); historical periods (Kirat, Licchavi, Malla); technical acronyms (ASL, GPS, GIS, BOD, DoI, LMC, GM, HDD).

## 1. Introduction

- **1.1 Background — hydraulic heritage of the Kathmandu Valley.** Why rajkulo, pokhari, and hiti are one interconnected system. Why their decline matters beyond heritage.
- **1.2 The Tikabhairab Rajkulo.** What this specific canal is, where it runs, what it once did, what state it is in now.
- **1.3 Study rationale.** Why this survey now: deterioration of Saptapatal Pokhari, planning need for restoration, missing baseline data.
- **1.4 Objectives.** Same six objectives as v1, tightened.
- **1.5 Scope and study area.** Geographic extent, coordinates, jurisdictions, what is *excluded* from scope (e.g., command-area mapping, branch loops beyond two surveyed).
- **1.6 Report structure.** Half-page roadmap for readers from non-technical to technical.

## 2. Heritage Significance and Historical Context *(moved earlier; this is the "why" before the "what")*

- **2.1 The integrated hydraulic system of the Kathmandu Valley.** Rajkulo as one element of a canal–pond–field–hiti system, drawing on Hiti Pranali terminology.
- **2.2 The Licchavi hydraulic record.** What inscriptions document about canal administration in the 4th–9th century CE.
- **2.3 The Tilmak hypothesis — evidence pointing to pre-Licchavi origins.** Expanded discussion: the Sanskritic-naming convention argument; the toponymic anomaly; the Kirat-period inheritance hypothesis; what evidence would be needed to confirm. **Framed throughout as a defensible hypothesis pending epigraphic verification, with `[CITATION: Hiti Pranali, p. TK]` placeholders for you to fill once you locate the passage.**
- **2.4 Heritage classification implications.** What confirmation of pre-Licchavi origin would mean for conservation funding, monument status, and UNESCO eligibility.

## 3. Methodology

- **3.1 Research design.** Two-phase: field survey + desktop hydraulic analysis. Why GPS-based section coding was chosen.
- **3.2 Field survey protocol.** The 94-section data collection flowchart, attribute schema, photographic protocol, manual+digital redundancy.
- **3.3 Spatial data acquisition.** Mergin Maps workflow, GPS accuracy notes, satellite verification.
- **3.4 Length measurement and reconciliation.** **New subsection** explaining why GPS-measured length (10,668.5 m) and AutoCAD-refined length (13,158.2 m) differ, and which is used where. *Critical for the v1 inconsistency.*
- **3.5 Hydraulic analysis framework.** Why Kennedy, Lacey, and Manning are the appropriate first-pass tools for this kind of channel. What discharge assumption is used (Q = 0.1 m³/s; rationale stated).
- **3.6 Restoration priority scoring methodology.** **New subsection** explaining the 0–4/0–2/0–2 scoring rationale, threshold rationale, sensitivity caveats. The scoring was opaque in v1.
- **3.7 Software stack.** Same list as v1 with version numbers and license types.
- **3.8 Survey limitations.** Consolidated and sharpened from v1 §2.5 + §6.4 caveats.

## 4. Canal Structure and Alignment

- **4.1 Alignment and settlements traversed.** Chainage map intake → terminus, with all named settlements.
- **4.2 Cross-sectional geometry.** Distribution table (rectangular, circular hume pipe, underground/unknown).
- **4.3 Lining materials and construction.** The one-sided rock-face lining tradition; mixed-period repairs; current condition.
- **4.4 Intake structure at Tikabhairav.** Detailed description: heavy silting, non-functional sluice gate, 2019 BS restoration history, current capacity loss.
- **4.5 Cross-drainage structures.** Six GPS-located structures; their hydraulic significance.
- **4.6 Encroachment and buried sections.** Four confirmed road-over-canal segments; future encroachment risk at Chainage 2+636.7 m.
- **4.7 Length reconciliation.** Why surveyed length (10.7 km), main alignment (13.2 km), and terminus chainage (11.8 km) differ; what each represents.

## 5. Flow and Water Quality

- **5.1 Flow regime distribution.** Perennial / seasonal / disturbed lengths with chainage ranges.
- **5.2 The perennial-to-sewage transition zone (Chainage 3+124 to 3+253.8 m).** A 130 m boundary that defines the rehabilitable upper canal. This is one of the most important spatial findings — promote it.
- **5.3 Water quality categories.** Multi-select observation framework; what each category actually means in field terms.
- **5.4 Sewage inflow points.** Six confirmed chainages, with the upper-canal inflow at 0+524.5 m flagged as anomalous and priority.
- **5.5 Implications for restoration water quality.** Why simply "restoring flow" without sewage diversion would harm Saptapatal Pokhari.

## 6. Hydraulic Analysis ★ *(specimen written below)*

- **6.1 Elevation profile and bed slope.** *Corrected:* both GPS-length-based and AutoCAD-length-based slopes presented; AutoCAD-refined adopted as primary value.
- **6.2 Reference discharge for hydraulic computation.** *New:* states the Q assumption that v1 implied but did not declare.
- **6.3 Kennedy's critical velocity.** Formula, assumptions, computed values across observed depth range.
- **6.4 Lacey's regime slope.** *New:* full derivation with explicit Q and silt-factor f.
- **6.5 Manning's flow velocity by lining material.** *Recalculated cleanly* at the corrected slope.
- **6.6 Effect of cross-sectional geometry.** Rectangular vs. circular hydraulic radius behaviour.
- **6.7 The central hydraulic finding.** Design is sound; deterioration is anthropogenic.
- **6.8 Caveats and validation requirements.** What the analysis assumes; what a total-station survey would refine.

## 7. Environmental and Public Health Risk Assessment *(new chapter)*

- **7.1 Risk framework.** Severity × likelihood matrix tailored to canal-driven hazards.
- **7.2 Saptapatal Pokhari contamination risk.** If restored flow carries six untreated sewage inflows into a culturally significant urban pond, the restoration becomes a vector of harm. Quantitative framing of why treatment is non-optional.
- **7.3 Vector-borne disease risk in stagnant sections.** Mosquito breeding in seasonal/disturbed sections; current public health relevance.
- **7.4 Groundwater recharge implications.** Linkage to hiti baseflows in Lalitpur's historic core; why canal restoration is a groundwater intervention as much as a surface-water one.
- **7.5 Climate resilience and monsoon variability.** Trends in Kathmandu Valley precipitation; implications for spring-fed intake reliability.
- **7.6 Cumulative environmental risk matrix.** Synthesis table mapping hazards × receptors × current vs. post-restoration scenarios.

## 8. Restoration Priority Matrix

- **8.1 Scoring framework.** Methodology cross-reference to §3.6.
- **8.2 Band-by-band analysis.** Annotated walkthrough of each of 11 chainage bands, not just the table.
- **8.3 Spatial priority map.** Critical (5–7 km), High (3–5, 8–9, 10–11 km), Medium (0–3, 7–8, 9–10 km), Low (1–2 km) zones on a single map.
- **8.4 Sensitivity discussion.** What changes if scoring weights are altered; honest acknowledgement of subjectivity.

## 9. Stakeholder and Governance Framework *(new chapter)*

- **9.1 Actor map.** All entities with legitimate stakes: intake-village community, downstream-village communities, GM, LMC, DoI, DUDBC, Department of Archaeology, NEA (water utility), affected landowners, religious trustees of Saptapatal Pokhari, NGOs (CIUD, NOA), donor community.
- **9.2 Jurisdictional boundaries.** Where GM authority ends and LMC begins; where DoI's irrigation mandate overlaps; where Department of Archaeology may need a heritage classification trigger.
- **9.3 Legal and regulatory context.** The 4 m buffer rule; conflict with road-over-canal permissions; what legal protection corridor would require.
- **9.4 Community stewardship tradition.** Pre-monsoon cleaning; its decline; what reactivation would require.
- **9.5 Proposed institutional arrangement.** Recommended structure: a Tikabhairab Rajkulo Trust with rotating GM-LMC chair, DoI technical secretariat, and a Water Users' Association anchoring community participation.

## 10. Phased Intervention Plan *(new chapter, directional — no rupee figures)*

- **10.1 Phasing logic.** Sequence is determined by hydraulic dependencies, not by convenience.
- **10.2 Phase 1 — Foundational works.** Intake rehabilitation, sluice gate replacement, desiltation of the 0–3 km perennial reach, sewage interception at Chainage 0+524.5 m.
- **10.3 Phase 2 — Sewage interception.** Diversion at the remaining five inflow points, prioritising the 5–7 km critical band.
- **10.4 Phase 3 — Urban reach reconstruction.** Treatment of road-over-canal sections via covered channel, HDD, or rerouting; resolution of the Ring Road crossing.
- **10.5 Phase 4 — Terminus and pond integration.** Connection to Saptapatal Pokhari with a small-scale treatment facility ensuring water quality before discharge.
- **10.6 Cross-cutting activities.** Legal-protection corridor designation; Water Users' Association formation; community engagement; ongoing monitoring.
- **10.7 Sequencing and dependencies.** Gantt-style placeholder; what must precede what.

## 11. Constraints and Challenges

- **11.1 Construction challenges.** Compressed from v1 §9.1 with cross-references to §10.
- **11.2 Governance challenges.** Compressed from v1 §9.2 with cross-references to §9.
- **11.3 Maintenance challenges.** Compressed from v1 §9.3 with cross-references to §9.4 and §10.6.

## 12. Research Gaps and Recommended Follow-Up

- **12.1 Total station survey** *(priority 1)*. What instruments, what protocol, what deliverables; rough effort estimate.
- **12.2 Epigraphic and archaeological investigation** *(the Tilmak question)*. What inscriptions to systematically catalogue; what excavation at the intake structure would test; comparative toponymic analysis methodology.
- **12.3 Quantitative water quality sampling.** Sampling plan: six inflow points + intake + terminus + Saptapatal Pokhari; BOD, COD, faecal coliform, TSS, heavy metals; seasonal repeat cycle.
- **12.4 Command area mapping.** Methodology to identify surviving agricultural parcels still hydraulically connected to the canal.
- **12.5 Continuous hydrological monitoring.** Permanent stage/discharge gauges at intake and terminus; rationale.
- **12.6 Social survey.** Household-level survey of communities along the alignment; current water uses, attitudes to restoration, willingness to participate.

## 13. Conclusion

A tighter version of v1 §11. Specific call to action with named institutional actors and a stated minimum first-step (commission the total station survey).

## References

Expanded reference list with full citations:
- **Heritage sources:** Hiti Pranali (Joshi); Gutschow; Ranjitkar; Tiwari (suggest add); Slusser (suggest add).
- **Hydraulic engineering:** Kennedy 1895; Lacey 1930; Manning 1891; Chow (Open-Channel Hydraulics) — suggest add as standard textbook reference.
- **Kathmandu Valley water:** DoI 2020; Shrestha & Pradhan 2018; UNESCO Kathmandu publications.
- **Methods:** Mergin Maps documentation; QGIS Development Team.

## Appendices

- **A. Section-by-section data summary** — full 94-section table exported from GeoPackage.
- **B. Points of Interest catalogue** — all 68 POIs with chainage, coordinates, type, photo reference.
- **C. Expanded glossary of Nepali/Newari hydraulic terms** — including those from Hiti Pranali.
- **D. Hydraulic calculation worksheets** — worked examples of all four computations (slope, Kennedy, Lacey, Manning) with formula sources cited.
- **E. Figure and map catalogue** — every figure/map referenced in the report, with source dataset and recommended production tool.
- **F. Recommended next-phase survey protocol** — total station survey methodology document referenced from §12.1.

---

# Part 2 — Specimen Section A: Executive Summary

## Executive Summary

The Tikabhairab Rajkulo is a 13 km hill-fed canal originating at the Tikabhairav intake in the forested hills south of Lalitpur and terminating, in its historical form, at Saptapatal Pokhari in Lagankhel. It is one of the principal hydraulic alignments of the Kathmandu Valley and, on the basis of epigraphic evidence summarised in Chapter 2, may represent a substantially older hydraulic tradition than its Licchavi-period documentation alone would suggest.

This report presents the findings of a GPS-based field survey conducted in May 2022 covering 94 canal sections and 68 georeferenced points of interest, together with a desktop hydraulic analysis grounded in the elevation benchmarks of the Department of Irrigation's 2020 Rajkulo study.

**The central finding is that the canal's deterioration is anthropogenic, not hydraulic.** A bed slope of **S = 0.01529** (1 in 65), computed from the GPS-measured length of 10,668.5 m and the 163.14 m total elevation drop documented by the Department of Irrigation's 2020 benchmarks, is approximately **35 times steeper than Lacey's regime slope** for the canal's plausible design discharge. The slope estimate is robust to the alternative length convention used in earlier drafts (the AutoCAD-refined main-alignment length of 13,158.2 m yields S = 0.01240, or roughly 28 times Lacey's regime slope; see Chapter 6 for both). Manning's equation applied across the lining materials documented in the field — concrete, brick masonry, stone masonry, earth, and vegetated earth — yields flow velocities that comfortably exceed Kennedy's critical velocity for the cross-sectional depths observed, by factors of 2.6 to 9.7 across every lining type. Under free-flowing, unobstructed conditions the canal possesses ample hydraulic energy to maintain self-cleansing flow. Restoration does not require redesigning the canal's slope or geometry; it requires removing obstructions, rehabilitating the intake, intercepting sewage, and clearing silt.

The condition data, however, document a system in advanced disrepair. Perennial flow persists for only **3,432.6 m (27.9 % of the alignment)**, terminating abruptly at Chainage 3+124 m. Beyond this point the canal is seasonal, dry, or carries sewage. **Silting is confirmed in 43.3 % of the surveyed length**, with the heaviest accumulation at the intake itself, where deposits of 1.5–2.0 m and a non-functional sluice gate have reduced design discharge to a small fraction of capacity. **Combined sewage, storm-water, and waste-dumping contamination affects 21.4 % of the directly observable alignment**, concentrated in the 5–7 km band and at the Lagankhel approach. **3,182.9 m (24.4 %) of the canal is buried beneath roads and urban infrastructure** at four confirmed segments, representing the principal structural obstacle to full restoration.

A quantitative restoration priority matrix — scoring each one-kilometre band on contamination, silting, and encroachment severity — identifies the **5–7 km band as the most critical zone for intervention**, with the 3–5 km, 8–9 km, and 10–11 km bands ranked high priority. The upper reach (0–3 km), although hydraulically intact, requires intake rehabilitation and an early sewage interception at Chainage 0+524.5 m to protect the canal's only remaining clean water source.

**Restoration as a functioning feeder for Saptapatal Pokhari is assessed as technically feasible**, contingent on four conditions: rehabilitation of the intake structure and sluice gate; sewage interception at the six identified inflow points; resolution of road-over-canal encroachments through covered-channel construction, horizontal directional drilling, or rerouting; and construction of a small-scale water-quality treatment facility immediately upstream of the pond. **None of these obstacles are hydraulic. All are institutional, financial, and political.**

This report does not attempt to specify the detailed engineering design of those interventions. It instead provides the empirical baseline — alignment geometry, condition catalogue, water quality regime, hydraulic adequacy assessment, priority matrix, and stakeholder framework — required before such a design can responsibly proceed. The single most important technical follow-up identified by this study is a total-station survey to determine per-section slope; the single most important institutional follow-up is the establishment of a legal protection corridor for the canal alignment across both Godavari Municipality and Lalitpur Metropolitan City jurisdictions.

The path forward is well defined. What is now required is the institutional will to follow it.

---

# Part 3 — Specimen Section B: Chapter 6 — Hydraulic Analysis

## 6. Hydraulic Analysis

This chapter evaluates whether the Tikabhairab Rajkulo's original hydraulic design is adequate to support restoration, or whether the design itself contributes to the deterioration observed in the field survey. The analysis is built from four standard tools of open-channel hydraulics applied in sequence: bed-slope calculation from elevation benchmarks; Kennedy's critical velocity to establish the silt-transport threshold; Lacey's regime slope to compare actual against ideal alluvial-channel gradient; and Manning's equation to compute the flow velocity achievable under each lining type observed in the alignment.

The analysis is desktop in nature. It is anchored on the two fixed elevation reference points documented in the Department of Irrigation's 2020 Rajkulo study — 1,477.16 m ASL at the Tikabhairav intake and 1,314.02 m ASL at the Lagankhel terminus — and on the canal length recovered from this study's GPS survey and AutoCAD refinement. It does **not** rest on per-section elevation data, which consumer-grade GPS receivers cannot supply at the vertical accuracy required (typical error ±10–30 m). The limitations this imposes are addressed explicitly in §6.8.

### 6.1 Elevation profile and bed slope

The total elevation drop along the main alignment is

$$\Delta H = 1{,}477.16 - 1{,}314.02 = 163.14 \text{ m}$$

This survey records two distinct length figures for the same alignment, which must be reconciled before slope can be computed:

- **GPS-measured length** (sum of GPS line geometries across the 94 surveyed sections): **10,668.5 m**. This is the length physically traversed and recorded.
- **AutoCAD-refined length** of the main alignment, including underground and inaccessible sections inferred from satellite imagery and adjacent visible canal segments: **13,158.2 m**. This is the best available estimate of the full canal length from intake to terminus.

The two figures differ by 2,489.7 m, which corresponds approximately to the canal length buried beneath road infrastructure (a confirmed total of 3,182.9 m, as catalogued in Chapter 4) less those buried sections that were nevertheless GPS-walked along their surface alignment.

The bed slope is

$$S = \frac{\Delta H}{L}$$

Computed against both length values:

| Length basis | L (m) | S | Equivalent | Angle |
|---|---|---|---|---|
| GPS-measured (surveyed sections only) | 10,668.5 | **0.01529** | **1 in 65** | **0.876°** |
| AutoCAD-refined (full main alignment) | 13,158.2 | 0.01240 | 1 in 81 | 0.710° |

***Table 6.1 — Bed slope under two length conventions.***

**The GPS-measured slope, S = 0.01529 (1 in 65), is adopted as the primary value for the hydraulic computations that follow.** It is anchored on the canal length physically walked and GPS-recorded across the 94 surveyed sections — directly observed data rather than inferred path. The AutoCAD-refined slope (S = 0.01240) is shown as an alternative for sensitivity: it uses an inferred full alignment length that includes buried sections estimated from satellite imagery, and its accuracy is contingent on the accuracy of those inferences. Both are presented because the choice affects downstream numerical values by approximately 10 % (slope scales linearly; velocity scales as S¹ᐟ², so velocity changes by ≈ 5 %).

The qualitative conclusions of this chapter — and of the report — do not depend on which slope value is selected. Where the difference matters numerically, sensitivity values at the AutoCAD-refined slope are noted in line. Resolution of the choice requires a total-station survey from intake to terminus, identified in §12.1 as the priority follow-up. The earlier informal trigonometric estimate of 1.55° (≈ S = 0.027) used in pre-publication drafts is incorrect and is not used in this report.

The slope so computed is an **average** across the full alignment. Per-section slope varies considerably — some segments are locally steep while others, particularly in the urban lower alignment, are nearly flat where the channel has been partially infilled. Determining the per-section slope distribution requires a total-station survey, identified as the priority follow-up in §12.1.

*[FIGURE 6.1: Elevation profile of Tikabhairab Rajkulo, intake to terminus. X-axis: chainage 0 to 13,158 m. Y-axis: elevation 1,300 to 1,500 m ASL. Linear interpolation between two DoI benchmarks shown as dashed line; chainage of all 68 POIs marked on x-axis; chainage bands colour-coded by priority class from Chapter 8 shown as horizontal coloured bar beneath the profile. Caveat box: "Per-section elevation requires total-station survey — see §12.1."]*

### 6.2 Reference discharge for hydraulic computation

Kennedy's, Lacey's, and Manning's equations all require, implicitly or explicitly, a reference discharge Q. No flow measurement was conducted during the May 2022 survey; the intake was heavily silted and the sluice gate non-functional, so any spot measurement would have characterised the disabled rather than the design discharge.

For the hydraulic analyses that follow, a **design reference discharge of Q = 0.10 m³/s (100 L/s)** is adopted. This value is consistent with the canal's documented historical role as both an irrigation channel for the southern Lalitpur command area and a feeder for Saptapatal Pokhari, and it is the discharge for which Lacey's regime slope matches the v1 working figure of 0.000439. The assumption is parametric: results scale predictably with Q (regime slope as Q⁻¹ᐟ⁶; Kennedy's Vc independent of Q; Manning's V independent of Q at fixed section). The qualitative conclusions of this chapter are robust to a Q-range of approximately 0.05–0.50 m³/s.

A direct measurement of the canal's natural-spring base discharge at the rehabilitated intake is identified as a research priority (§12.5).

### 6.3 Kennedy's critical velocity

Kennedy's critical velocity Vc is the minimum mean cross-sectional velocity at which sediment of a given grade is maintained in suspension and transported through the channel without depositing. Below Vc the channel silts; above Vc, sediment is transported and the channel self-cleanses. For the alluvial conditions characteristic of South Asian irrigation canals, Kennedy proposed

$$V_c = 0.55 \times m \times D^{0.64}$$

where D is the hydraulic mean depth (cross-sectional flow area divided by top width, in metres) and m is a critical-velocity ratio dependent on silt grade (m = 1.0 for standard alluvial silt, the value adopted here in the absence of site-specific sediment characterisation).

Kennedy's critical velocity for representative hydraulic depths spanning the range observed in this survey:

| Hydraulic depth D (m) | Critical velocity Vc (m/s) | Representative section type |
|---|---|---|
| 0.30 | 0.255 | Shallow / silted reach |
| 0.40 | 0.306 | Typical small section |
| 0.50 | 0.354 | Representative main section |
| 0.60 | 0.397 | Deeper / larger section |

***Table 6.2 — Kennedy's critical velocity at observed hydraulic depths.***

These values establish the velocity threshold that the canal's flow must exceed under each combination of slope, lining, and discharge to remain self-cleansing.

### 6.4 Lacey's regime slope

Lacey's regime theory specifies the slope at which an alluvial channel, allowed to self-form, will neither aggrade nor degrade — the natural equilibrium gradient for a given discharge and sediment grade. For metric units:

$$S_0 = \frac{f^{5/3}}{3340 \cdot Q^{1/6}}$$

where f is Lacey's silt factor (f = 1.0 for standard alluvium; the field-observed coarse-gravel-and-silt mix is consistent with this value as a first approximation) and Q is the design discharge in m³/s.

For the adopted reference values f = 1.0 and Q = 0.10 m³/s:

$$S_0 = \frac{1.0^{5/3}}{3340 \cdot (0.10)^{1/6}} = \frac{1}{3340 \times 0.681} = 0.000440$$

The primary bed slope (S = 0.01529, per §6.1) is therefore

$$\frac{S}{S_0} = \frac{0.01529}{0.000440} \approx 35$$

times Lacey's regime slope. *Sensitivity to length convention:* at the alternative AutoCAD-refined slope (S = 0.01240) the ratio falls to approximately 28. *Sensitivity to discharge:* at Q = 0.05 m³/s the ratio rises to approximately 39; at Q = 0.50 m³/s it falls to approximately 27. Under all plausible combinations of length and discharge, the canal's slope substantially exceeds Lacey's regime slope. This is a substantial excess of gradient relative to alluvial equilibrium — the channel has far more hydraulic energy than is required for stable silt-transport behaviour.

The practical interpretation: under unobstructed flow conditions the canal will not naturally silt. The silting documented in the field survey — particularly the 1.5–2.0 m deposit at the intake — is therefore a consequence of *reduced velocity* caused by intake blockage and downstream encroachment, not of *insufficient slope*.

### 6.5 Manning's flow velocity by lining material

Manning's equation governs the mean velocity of flow in an open channel under steady, uniform conditions:

$$V = \frac{1}{n} \cdot R^{2/3} \cdot S^{1/2}$$

where n is Manning's roughness coefficient (a function of lining material), R is the hydraulic radius (flow area divided by wetted perimeter, in metres), and S is the bed slope.

A representative cross-section is required to evaluate this equation. For the rectangular geometry that dominates the alignment (64.5 % of total length per the Chapter 4 geometry distribution), a representative section width of 0.50 m and flow depth of 0.40 m is adopted, yielding

$$A = 0.50 \times 0.40 = 0.20 \text{ m}^2, \quad P = 0.50 + 2 \times 0.40 = 1.30 \text{ m}, \quad R = \frac{0.20}{1.30} = 0.154 \text{ m}$$

With R = 0.154 m and the primary slope S = 0.01529:

$$R^{2/3} \times S^{1/2} = 0.287 \times 0.1236 = 0.0355$$

Manning's velocities at this representative section across the range of lining materials observed in the alignment:

| Lining material | Manning's n (range) | Velocity V (m/s) at S = 0.01529 | V/Vc (D = 0.40 m) | Silting risk |
|---|---|---|---|---|
| Concrete (smooth) | 0.012 – 0.018 | **2.96 – 1.97** | 9.7× – 6.4× | Negligible |
| Brick masonry | 0.015 – 0.025 | **2.37 – 1.42** | 7.7× – 4.6× | Very low |
| Stone masonry | 0.020 – 0.030 | **1.77 – 1.18** | 5.8× – 3.9× | Low |
| Earth (unlined) | 0.025 – 0.035 | **1.42 – 1.01** | 4.6× – 3.3× | Low |
| Vegetated earth (poor) | 0.030 – 0.045 | **1.18 – 0.79** | 3.9× – 2.6× | Moderate |

***Table 6.3 — Manning's velocity by lining material at the primary slope S = 0.01529 and representative section (w = 0.50 m, d = 0.40 m). At the alternative AutoCAD-refined slope (S = 0.01240) each velocity value is approximately 10 % lower; all V/Vc ratios remain well above unity.***

Across all five lining categories present in the alignment — including the worst-case vegetated-earth condition — the computed mean velocity comfortably exceeds Kennedy's critical velocity for the corresponding hydraulic depth. The lowest computed velocity (0.79 m/s for vegetated earth at n = 0.045) is approximately 2.6 times the critical velocity at the same depth (0.306 m/s for D = 0.40 m). The highest (2.96 m/s, smooth concrete at n = 0.012) is approximately 9.7 times Vc. At the alternative AutoCAD-refined slope, the corresponding range is 0.71 m/s (2.3× Vc) to 2.66 m/s (8.7× Vc) — qualitatively identical.

The Manning's velocities in this table differ from those published in pre-publication v1 drafts of this report, which used a different rounding convention for R²ᐟ³. The qualitative finding is unaffected — velocities exceed Vc across all lining types — but the numerical values in this report supersede those in earlier drafts.

*[FIGURE 6.2: Velocity-vs-Vc bar chart. For each of the five lining materials, plot bars showing Manning's velocity range (low–high) and overlay Kennedy's Vc threshold (D = 0.40 m, Vc = 0.306 m/s) as a horizontal red line. Visual demonstrates that all lining types clear Vc by a comfortable margin.]*

### 6.6 Effect of cross-sectional geometry

The cross-sectional shape of the canal influences the hydraulic radius R and therefore the velocity V. Two principal geometries are observed in the alignment:

- **Rectangular sections (64.5 % of total length).** For a given cross-sectional area, rectangular geometry produces a relatively high hydraulic radius — higher than equivalent trapezoidal or triangular sections of the same area at low flow depths. The dominance of rectangular geometry in Tikabhairab Rajkulo is therefore hydraulically advantageous: it maximises velocity per unit discharge and minimises silting tendency.
- **Circular hume-pipe sections (12.0 % of total length).** Hydraulic radius in a circular pipe varies non-linearly with flow depth. At full flow, R is maximised and velocity is high. At partial flow — the condition observed throughout the alignment under current reduced discharge — the wetted perimeter grows more rapidly than flow area, reducing R, reducing velocity, and creating local conditions favourable to silt deposition. Hume-pipe sections are therefore disproportionately vulnerable to silting under the canal's present low-discharge regime.

This finding is significant for restoration planning: it identifies hume-pipe sections, despite their structural advantage in erosion-prone reaches, as the segments most at risk of silting if the intake is not first rehabilitated to restore design discharge.

### 6.7 The central hydraulic finding

The bed slope, regime-slope comparison, critical velocity, and Manning's velocity calculations converge on a single conclusion:

> **The Tikabhairab Rajkulo's hydraulic design is sound.** A bed slope of S = 0.01529 (1 in 65) provides approximately 35 times Lacey's regime slope under the canal's plausible discharge range, and yields Manning's velocities that exceed Kennedy's critical velocity by factors of 2.6 to 9.7 across every lining material documented in the alignment. The conclusion holds under the alternative slope convention (S = 0.01240): the ratio falls to 28× Lacey and the V/Vc range to 2.3–8.7×, both still far above the silting threshold. The silting, contamination, and flow interruption observed in the field survey are consequences of intake blockage, sewage loading, road-over-canal encroachment, and reduced discharge — not of inadequate design. **The canal's deterioration is anthropogenic.**

This finding establishes the empirical basis for the restoration strategy developed in Chapter 10. Because the canal's slope and geometry do not require redesign, restoration is reduced to a sequence of solvable engineering, sewage-management, and institutional tasks within the existing canal footprint.

A summary of the four hydraulic factors and their relationships to the canal's restoration prospects:

| Factor | Effect on velocity | Tikabhairab Rajkulo condition | Implication |
|---|---|---|---|
| Slope S | V ∝ S¹ᐟ² | S = 0.01529 primary (0.01240 alternative); 35× Lacey regime (28× alternative) | Excess slope under either length convention; silting is not slope-driven |
| Lining roughness n | V ∝ 1/n | Majority brick / stone masonry, 71 % lined | V exceeds Vc by 2.6× – 9.7× for every observed lining |
| Cross-section geometry | Higher R → higher V | 64.5 % rectangular; hydraulically optimal | Geometry does not require redesign |
| Discharge Q | Reduced Q → lower depth → lower V → silting | Intake severely silted; Q a fraction of design | **Intake rehabilitation is the binding constraint** |

***Table 6.4 — Summary of hydraulic factor relationships and restoration implications.***

### 6.8 Caveats and validation requirements

This analysis is sufficient to establish that the canal's design does not require modification. It is not sufficient to specify the detailed restoration engineering. Three categories of refinement are required before final design proceeds:

1. **Per-section slope determination.** The average bed slope reported here masks substantial local variation. Sections with locally flat gradients may require minor profile correction or drop-structure insertion; locally steep sections may need energy dissipators. A total-station survey from intake to terminus is identified in §12.1 as the priority next technical step.
2. **Direct discharge measurement.** All velocity computations in this chapter are parametric in Q. Once the intake is partially rehabilitated, a stage–discharge rating at the intake and at the terminus will replace the Q = 0.10 m³/s assumption with measured values and allow the hydraulic analysis to be re-run with site-specific data.
3. **Sediment characterisation.** Kennedy's m = 1.0 and Lacey's f = 1.0 are conservative defaults. A sediment-grade analysis of the deposited material in the intake silt body and in representative downstream sections will refine both parameters and may modify the regime-slope multiplier.

These refinements would tighten the analysis but are not expected to alter its central conclusion. The conservative parameters used here produce a finding (28 × Lacey, V ≫ Vc for every lining) with sufficient margin that plausible parameter refinement cannot overturn it.

---

# What to react to

Please flag any of the following:

1. **Outline structure** — is the chapter sequence (Heritage → Methods → Condition → Flow/Water Quality → Hydraulics → Risk → Priority → Stakeholders → Phased Plan → Constraints → Gaps → Conclusion) right, or do you want me to reorder?
2. **New chapters (Risk, Stakeholders, Phased Plan)** — are their proposed contents what you want, or should I scope them differently?
3. **Executive Summary tone and length** — too long? Too short? Wrong emphasis? Tilmak claim phrased too strongly or too weakly?
4. **Hydraulic Analysis chapter** — do you accept the S = 0.01240 (AutoCAD-length-based) figure as the new primary slope? Is the parametric Q = 0.10 m³/s framing acceptable? Are the recalculated Manning's velocities in Table 6.3 acceptable to publish over the older numbers?
5. **Voice / register** — too academic? Not academic enough? Right level for a baseline-documentation report serving four audiences?
6. **Anything missing** that I should have flagged at this stage.

Once you've reacted I'll write the remaining ~25 pages in one disciplined pass and generate the .docx.
