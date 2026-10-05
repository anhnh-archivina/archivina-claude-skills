# Output Rules

## 1. Human-readable RCP report

For each room provide:
- room name;
- primary axis;
- device schedule;
- positions / dimensions;
- spacing checks;
- wardrobe-zone checks;
- conflicts;
- warnings;
- status.

## 2. Coordinate output for automation

When coordinates are available:

| Field | Description |
|---|---|
| DEVICE_ID | unique ID |
| ROOM | room name |
| DEVICE_TYPE | device family |
| BLOCK_NAME | CAD block |
| X | drawing X |
| Y | drawing Y |
| Z | ceiling elevation |
| ROTATION | degrees |
| WIDTH | mm |
| HEIGHT | mm |
| SYSTEM | lighting/HVAC/fire/etc. |
| PRIORITY | P1-P6 |
| STATUS | pass/conflict/review |
| WARNING | warning text |

## 3. CAD automation behavior

When generating AutoLISP / script / Core Console input:
- preserve drawing units;
- use millimeters unless project input says otherwise;
- do not invent block names if none are supplied;
- do not overwrite existing devices without explicit instruction;
- place proposed devices on separate proposed layers if requested;
- generate a conflict report in addition to geometry.

## 4. Suggested layers

Only use these if the project has no established CAD standard:
- A-RCP-LITE
- M-HVAC-SUP
- M-HVAC-RET
- M-HVAC-FRESH
- M-HVAC-EXH
- F-FIRE-SPRK
- F-FIRE-DETC
- A-RCP-ACCESS
- A-RCP-WARN

Project CAD standards override these suggestions.
