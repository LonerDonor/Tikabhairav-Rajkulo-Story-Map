TIKABHAIRAB RAJKULO — OPEN SURVEY DATA
======================================

Field survey of the Tikabhairab Rajkulo canal, Lalitpur, Nepal, 4–11 May 2022.
107 canal sections, 68 points of interest, 96 historic branch lines.
Interactive map: https://lonerdonor.github.io/Tikabhairav-Rajkulo-Story-Map/

LICENCE
Creative Commons Attribution 4.0 International (CC BY 4.0)
https://creativecommons.org/licenses/by/4.0/
You may share and adapt the data, including commercially, as long as you give credit.

HOW TO CITE
Joshi, H. R. (2022). Tikabhairab Rajkulo field survey, May 2022 [Data set]. Living Heritage Map of the Tikabhairab Rajkulo. https://lonerdonor.github.io/Tikabhairav-Rajkulo-Story-Map/

COORDINATES
WGS 84 (EPSG:4326), longitude/latitude in decimal degrees.

HOW 'condition' IS DERIVED
  Lost      the canal could not be seen
  Critical  sewage or waste dumping recorded, and silting present
  Poor      sewage or waste dumping recorded, no silting
  Fair      silting present, no sewage or waste
  Good      none of the above recorded
  No data   nothing was recorded (includes the 12 CAD-only sections)

CAVEATS
- Chainage is a main-line distance; parallel branches restart from their upstream section.
- Elevations are a straight-line interpolation, not measured levels.
- Sections with gps_walked = false have approximate geometry and no field observations.
- Notes and comments are reproduced as the surveyors wrote them.

FILES
  rajkulo_sections.geojson / .csv            canal sections
  rajkulo_points_of_interest.geojson / .csv  points of interest
  rajkulo_historic_branches.geojson          historic distributary network (canal_id)

SECTION FIELDS
  pdf_n                Section number in the CAD drawings (intake → outlet order)
  mergin_fid           Feature id in the Mergin Maps survey layer (blank = not GPS-walked)
  tole                 Locality / surveyor's section label, as recorded
  gps_walked           true = geometry walked with GPS in May 2022; false = approximate CAD-only placeholder
  chainage_start_m     Main-line distance from the intake at the start of the section (m)
  chainage_end_m       Main-line distance from the intake at the end of the section (m) = Station Point
  length_m             Section length (m)
  elevation_interp_m   Elevation interpolated linearly between the intake (1,477.16 m) and the outlet (1,314.02 m); not measured
  flow                 Flow regime observed: Perennial / Seasonal / Unknown
  water_quality        Every water-quality value recorded, separated by '; '
  sewage_or_waste      true if Sewage or Waste Dumping was among the water-quality values
  silting              Present / Absent
  lined                Yes / No
  shape                Rectangular / Circular
  width_cm             Inner width (cm), rectangular sections
  height_cm            Inner height (cm), rectangular sections
  diameter_cm          Diameter (cm), circular sections
  condition            Derived class: Good / Fair / Poor / Critical / Lost / No data (rules in DATA_README.txt)
  notes                Surveyor's field notes, as recorded (English)
  photos               Photo URLs, separated by '; '
  surveyed_at          Date and time the section was recorded

POINT-OF-INTEREST FIELDS
  fid                  Point id in the Mergin Maps POI layer
  category             Contamination / Cross Drainage / Encroachment / Vulnerable Zone / Intake Structure / Observation Point
  comment              Surveyor's comment, as recorded (English)
  lon                  Longitude (WGS 84)
  lat                  Latitude (WGS 84)
  photos               Photo URLs, separated by '; '
