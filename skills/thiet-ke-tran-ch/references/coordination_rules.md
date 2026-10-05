# Coordination and Conflict Resolution Rules

## 1. Conflict-check sequence

For every proposed device, check:

1. Is it inside a wardrobe / closet footprint?
2. Does it overlap another device?
3. Does it violate lighting-spacing rules?
4. Does it violate wall-offset rules?
5. Does it obstruct access-panel opening?
6. Does it conflict with door swing / shower screen / tall joinery?
7. Does HVAC airflow create comfort or detector issues?
8. Does it compromise life-safety requirements?
9. Does it create a poor visual offset that can be corrected by moving a lower-priority item?

---

## 2. Wardrobe conflict

IF device center or device footprint intersects wardrobe footprint:
- set STATUS = CONFLICT;
- do not finalize placement;
- propose relocation outside wardrobe zone.

IF device is life-safety equipment:
- set STATUS = TECHNICAL REVIEW REQUIRED;
- issue CRITICAL warning;
- do not delete the device;
- request fire / technical consultant coordination.

---

## 3. Lighting spacing conflict

IF adjacent general lights < 1200 mm:
- first reduce fixture count or widen grid;
- do not approve compressed spacing for symmetry.

IF nearest light row to wall < 500 mm:
- move row inward;
- target approximately 600 mm where room dimension permits.

---

## 4. Light vs sprinkler

- sprinkler compliance has priority;
- move light first where practical;
- re-balance remaining lights after movement;
- do not create a light spacing < 1200 mm after rebalancing.

---

## 5. Light vs detector

- keep a visually readable separation;
- move the light first if detector position is technically constrained;
- preserve overall lighting grid where possible.

---

## 6. Detector vs supply air

- identify potential airflow interference;
- do not place detector in a location that the technical design identifies as ineffective;
- coordinate with fire and HVAC consultants when required.

---

## 7. Pendant vs technical devices

Establish a protected visual zone around pendant lighting.

If sprinkler / detector / grille conflicts:
- technical compliance remains primary;
- move lower-priority devices when possible;
- otherwise flag architectural coordination issue.

---

## 8. WC alignment conflict

When a technically constrained ceiling device cannot align with basin / WC / shower axis:
- retain the technically required position;
- align nearby lower-priority lighting to recover order;
- issue DESIGN WARNING if the ceiling composition remains visibly irregular.

---

## 9. Access-panel conflict

If access panel clashes with:
- light;
- grille;
- sprinkler;
- detector;
- wardrobe;
- door swing;
- shower screen;

then move the access panel first if maintenance access remains valid.

Never locate an access panel where it cannot open or where the serviced equipment cannot be reached.

---

## 10. Final room grading

PASS:
All hard rules and technical constraints are satisfied.

PASS WITH WARNING:
No hard-rule violation; minor architectural / coordination issue remains.

REVISE:
One or more HARD_RULE violations remain.

TECHNICAL REVIEW REQUIRED:
Life-safety or MEP requirement cannot be resolved from available information.
