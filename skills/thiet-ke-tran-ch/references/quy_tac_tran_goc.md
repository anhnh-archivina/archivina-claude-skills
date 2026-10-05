# Archivina Apartment Ceiling Design Skill

## 1. Purpose

This skill assists Claude in developing and reviewing reflected ceiling plans (RCP) for apartment units similar to Archivina's sample apartment ceiling layouts.

The skill shall:
- read architectural plans, room boundaries, furniture, sanitary fixtures and available MEP/firefighting information;
- identify each room type;
- establish architectural ceiling axes;
- propose positions for lighting and ceiling-mounted technical devices;
- coordinate lighting, HVAC, fire alarm, sprinkler and maintenance access;
- detect conflicts and issue warnings;
- preserve architectural order, symmetry and alignment without compromising life-safety or technical requirements.

This skill is intended for DESIGN ASSISTANCE and COORDINATION.
It does not replace final calculations, code compliance review, manufacturer requirements, fire-protection design, HVAC design or authority approval.

---

## 2. Reference drawing conventions

The reference apartment drawing contains the following ceiling devices:
- 600 x 600 mm access panel;
- 200 x 200 mm exhaust fan;
- outdoor surface-mounted light at loggia;
- recessed LED downlight D90;
- pendant light point in living / dining;
- WC recessed LED downlight D90;
- mirror light D65;
- 300 x 300 mm fresh-air grille;
- 150 x 1200 mm return-air grille;
- 150 x 1200 mm supply-air grille;
- addressable smoke detector;
- fixed-temperature addressable heat detector;
- pendent sprinkler D15, 68°C, K=5.6 US;
- pendent sprinkler D15, 93°C, K=5.6 US.

Treat these as project-reference device families. Do not assume that every future apartment uses exactly the same device size or quantity. Always read the project input and device schedule first.

---

## 3. Rule classification

Every rule in this skill belongs to one of four classes:

### HARD_RULE
Must be satisfied unless a higher-priority life-safety or statutory requirement makes it impossible.

### TECHNICAL_RULE
Must follow MEP, fire-safety, manufacturer or consultant requirements.

### DESIGN_RULE
Architectural coordination rule used to obtain a rational and visually ordered ceiling.

### PREFERENCE
Recommended solution when no higher-priority requirement prevents it.

When two rules conflict, use the priority system in Section 5 and issue a coordination warning.

---

## 4. Required input

Before designing the ceiling, identify as many of the following as possible:

1. Room boundaries and clear room dimensions.
2. Ceiling boundary and ceiling levels.
3. Doors and door swings.
4. Windows, façade and loggia.
5. Furniture:
   - beds;
   - wardrobes / closets;
   - sofa;
   - TV wall;
   - coffee table;
   - dining table;
   - kitchen cabinets;
   - refrigerator;
   - loose furniture.
6. Sanitary fixtures:
   - wash basin;
   - WC;
   - shower;
   - bathtub;
   - floor drain where relevant.
7. Fixed joinery.
8. HVAC equipment and duct routes where available.
9. Fire-protection information.
10. Plumbing / electrical / FCU service zones.
11. Existing ceiling-mounted devices.
12. Ceiling access requirements.

If critical information is missing, do not invent it. State the assumption or issue a warning.

---

## 5. System priority

Use the following priority when resolving conflicts:

P1 — Mandatory life safety
- sprinkler;
- smoke detector;
- heat detector;
- other mandatory fire-safety devices.

P2 — MEP performance
- supply air;
- return air;
- fresh air;
- exhaust;
- devices whose location affects system performance.

P3 — Maintenance access
- access panels;
- service clearances.

P4 — Functional lighting
- mirror light;
- kitchen task lighting;
- other task lighting.

P5 — Decorative / general lighting
- pendant light;
- downlight composition.

P6 — Visual alignment
- symmetry;
- equal spacing;
- grid continuity.

IMPORTANT:
A lower-priority item shall not force a mandatory life-safety device into a non-compliant position.
However, when a higher-priority device creates a major architectural conflict, Claude must flag it for coordination rather than silently accepting a poor layout.

---

## 6. Universal ceiling design rules

### 6.1 Room-based design
Treat each enclosed room or functional zone as a separate ceiling-design module.

Typical room types:
- living;
- dining;
- bedroom;
- kitchen;
- WC / bathroom;
- multipurpose room;
- corridor / entrance;
- loggia.

Do not impose one global grid on the entire apartment if it produces poor room-by-room alignment.

### 6.2 Establish design axes
For each room, determine:
- room geometric axis;
- furniture axis;
- sanitary-fixture axis;
- façade / window axis;
- ceiling feature axis.

Select the dominant axis according to room function.

### 6.3 Lighting spacing — HARD_RULE
For general ceiling lights:
- clear center-to-center distance between adjacent lights shall NOT be less than 1200 mm;
- distance from the nearest row of lights to the nearest wall shall NOT be less than 500 mm;
- preferred distance from the nearest row of lights to the wall is approximately 600 mm where room dimensions permit.

If the room is too small to satisfy these rules:
1. reduce the number of lights;
2. reconsider the lighting layout;
3. issue a warning if the rule still cannot be satisfied.

Never compress the lighting grid below 1200 mm simply to maintain symmetry.

### 6.4 Wardrobe / closet exclusion zone — HARD_RULE
Do NOT place ceiling lights or ceiling-mounted devices within the plan footprint of a wardrobe / closet.

The wardrobe footprint shall be treated as a CEILING DEVICE EXCLUSION ZONE.

This applies to:
- downlights;
- pendant points;
- supply-air grilles;
- return-air grilles;
- fresh-air grilles;
- detectors;
- access panels;
- other ceiling devices.

For fire-safety equipment:
- never delete or relocate a mandatory fire-safety device solely to satisfy the wardrobe rule;
- if a mandatory device is required within or above the wardrobe zone, flag a CRITICAL COORDINATION WARNING and request review by the fire consultant / relevant technical consultant.

If a proposed layout contains a ceiling device inside the wardrobe footprint:
- mark the device as CONFLICT;
- identify the wardrobe;
- recommend moving the device or adjusting the wardrobe;
- do not silently approve the layout.

### 6.5 Alignment
Where technically possible:
- align device centers to common axes;
- align rectangular grilles with wall / ceiling geometry;
- keep repeated devices on clean rows;
- maintain consistent edge offsets;
- avoid small accidental offsets between adjacent devices.

### 6.6 Avoid device clustering
Do not bunch together downlights, sprinkler heads, detectors and grilles unless required.

If multiple devices occupy the same ceiling zone:
1. keep required technical clearances;
2. preserve a readable composition;
3. move the lower-priority device first.

### 6.7 Do not use room center mechanically
The room center is not automatically the correct location.

Examples:
- pendant light follows dining table center;
- bedroom ceiling composition follows bed axis;
- WC devices follow sanitary-fixture axes;
- mirror light follows basin / mirror axis.

---

## 7. Room rules

Detailed rules are stored in:
`references/room_rules.md`

Always apply the room-specific rules after the universal rules.

---

## 8. Device rules

Detailed device rules are stored in:
`references/device_rules.md`

Always apply device-specific technical and coordination rules.

---

## 9. Conflict-resolution rules

Detailed coordination logic is stored in:
`references/coordination_rules.md`

Claude must perform a conflict check before finalizing any RCP.

---

## 10. Design workflow

Execute the following sequence.

### STEP 01 — Read the architectural plan
Identify walls, doors, glazing, room names and fixed geometry.

### STEP 02 — Create room boundaries
Generate a closed boundary for each room / functional zone.

### STEP 03 — Detect furniture and fixed joinery
At minimum detect:
- beds;
- wardrobes;
- sofa;
- TV;
- coffee table;
- dining table;
- kitchen cabinets;
- sanitary fixtures.

### STEP 04 — Generate exclusion zones
Create:
- wardrobe exclusion zone;
- other project-specific no-device zones;
- maintenance restrictions if known.

### STEP 05 — Determine room axes
Determine the primary and secondary ceiling-design axes.

### STEP 06 — Place high-value architectural lighting
Place:
- pendant points;
- mirror lights;
- task lights.

### STEP 07 — Generate general-lighting grid
Place downlights according to:
- room / furniture axis;
- minimum light-to-light spacing = 1200 mm;
- minimum light-row-to-wall offset = 500 mm;
- preferred wall offset ≈ 600 mm;
- wardrobe exclusion zones;
- room-specific rules.

### STEP 08 — Place HVAC devices
Place:
- supply air;
- return air;
- fresh air;
- exhaust.

Respect airflow performance and room-specific comfort rules.

### STEP 09 — Place life-safety devices
Place:
- sprinkler;
- smoke detector;
- heat detector.

Technical / fire-safety requirements govern final locations.

### STEP 10 — Place maintenance devices
Locate access panels based on the equipment requiring service.

### STEP 11 — Coordinate
Run:
- overlap check;
- spacing check;
- wardrobe-zone check;
- alignment check;
- airflow conflict check;
- maintenance-access check;
- life-safety conflict check.

### STEP 12 — Rebalance the ceiling
After technical devices are coordinated, rebalance the lower-priority architectural devices to recover a clean ceiling composition.

### STEP 13 — Final validation
Do not output "APPROVED" if any HARD_RULE or unresolved critical technical conflict remains.

---

## 11. Required validation checks

Before completing the RCP, verify all of the following:

### Lighting
- [ ] Adjacent general lights are at least 1200 mm center-to-center.
- [ ] Nearest light row is at least 500 mm from wall.
- [ ] Approx. 600 mm wall offset is used where practical.
- [ ] Lighting follows room / furniture / fixture logic.
- [ ] No light is inside wardrobe footprint.

### Wardrobes
- [ ] All wardrobe footprints are detected.
- [ ] No ceiling-mounted device is inside wardrobe footprint.
- [ ] Any unavoidable life-safety conflict is clearly flagged.

### Bedrooms
- [ ] Downlights are not directly above pillow zone where avoidable.
- [ ] Supply air does not discharge directly toward pillow / head zone.
- [ ] Access panel is outside bed zone where practical.

### WC / bathroom
- [ ] Ceiling devices are coordinated with sanitary-fixture axes.
- [ ] Basin-related light aligns with basin / mirror axis.
- [ ] WC-zone device layout is intentional and ordered.
- [ ] Shower-zone device layout is intentional and ordered.
- [ ] Access panel does not compromise fixture use or maintenance.

### HVAC
- [ ] Supply and return are not unintentionally short-circuited.
- [ ] Diffusers align with ceiling geometry where technically possible.
- [ ] Supply air avoids direct uncomfortable discharge toward bed / long-stay seating.

### Fire safety
- [ ] Sprinkler positions are checked against fire-design requirements.
- [ ] Detector positions are checked against fire-design requirements.
- [ ] Detector / sprinkler positions are not changed only for aesthetic alignment.
- [ ] Technical conflicts are flagged.

### Maintenance
- [ ] Each access panel corresponds to an actual maintenance need.
- [ ] Access panel is reachable and openable.
- [ ] Access panel is visually minimized in primary rooms where possible.

---

## 12. Warning levels

Use these exact warning categories.

### CRITICAL
Life-safety / code / mandatory technical conflict.

Example:
`CRITICAL: Mandatory sprinkler requirement conflicts with wardrobe exclusion zone. Fire consultant coordination required.`

### HARD-RULE WARNING
Archivina internal ceiling-design rule is violated.

Example:
`HARD-RULE WARNING: Downlight spacing is 980 mm < 1200 mm minimum.`

### COORDINATION WARNING
MEP / architectural coordination is unresolved.

Example:
`COORDINATION WARNING: Supply-air grille conflicts with pendant-light zone.`

### DESIGN WARNING
Layout is technically possible but architecturally weak.

Example:
`DESIGN WARNING: Access panel is positioned in the visual center of the living room; move toward a secondary ceiling zone if service access permits.`

---

## 13. Output format

For every room, output:

1. Room name.
2. Primary design axis.
3. Ceiling devices.
4. Proposed coordinates or relative positions.
5. Key dimensions.
6. Conflicts.
7. Warnings.
8. Recommended adjustments.
9. Status:
   - PASS;
   - PASS WITH WARNING;
   - REVISE;
   - TECHNICAL REVIEW REQUIRED.

Example:

ROOM: BEDROOM 01
PRIMARY AXIS: BED CENTERLINE

DOWNLIGHT_01
- X: ...
- Y: ...
- relation: left of bed axis

DOWNLIGHT_02
- X: ...
- Y: ...
- relation: right of bed axis

CHECKS
- light spacing: 1350 mm -> PASS
- wall offset: 610 mm -> PASS
- wardrobe overlap: NONE -> PASS
- supply air to pillow: NONE -> PASS

STATUS: PASS

---

## 14. AutoCAD-oriented output

When requested to generate data for AutoCAD / AutoLISP / Core Console, provide each device as a structured record:

DEVICE_ID
ROOM
DEVICE_TYPE
BLOCK_NAME
X
Y
Z
ROTATION
WIDTH
HEIGHT
SYSTEM
PRIORITY
STATUS
WARNING

Example:

DEVICE_ID: BR01_DL_01
ROOM: BEDROOM_01
DEVICE_TYPE: DOWNLIGHT
BLOCK_NAME: LT-DL-D90
X: 3250
Y: 4680
Z: CEILING_LEVEL
ROTATION: 0
SYSTEM: LIGHTING
PRIORITY: P5
STATUS: PASS
WARNING: NONE

Coordinates must come from the actual drawing coordinate system when available.
Do not invent coordinates from a raster image unless explicitly instructed to create an approximate conceptual layout.

---

## 15. Core behavior

Claude shall act as a ceiling-design coordinator, not merely a symbol-placement engine.

Always:
- understand room use;
- understand furniture;
- establish axes;
- protect wardrobe exclusion zones;
- obey minimum lighting spacing;
- coordinate equipment;
- prioritize life safety;
- issue explicit warnings.

Never:
- scatter devices randomly;
- force every device to the room center;
- place devices inside wardrobe footprint without warning;
- compress downlight spacing below 1200 mm to achieve symmetry;
- place the first light row closer than 500 mm to the wall without warning;
- move fire-safety devices purely for aesthetics;
- claim regulatory compliance without the required project-specific technical verification.
