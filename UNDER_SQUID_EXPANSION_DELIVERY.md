# Under-Squid Expansion Delivery

## Built result

The lower scene is now **The Sounder in the Dark**. Entry and exit both use parkour at the
squid's mouth. The former surface shaft is disabled in the Abyss Market configuration and absent
from the regenerated artifact.

The complete addition contains:

- a 200-course open-mouth sperm-whale leviathan behind the squid, with blunt forehead,
  nineteen-course gape, lined palate, projecting jaw, teeth, eyes, offset blowhole, fins,
  broad flukes, and three sucker-scar groups;
- separate Hunt and Wake parkour strands between the existing Crown and Prism descent rests and
  the two mouth galleries;
- a lower slime catch and a nine-course ladder return on each strand;
- a five-by-four glazed tail sightline with an exact excavation manifest below the 60-cell cap;
- three incomplete oxidized-copper sound frames with sparse pearlescent light;
- a mouth-only Abyss Market rebuilt without its legacy surface shaft.

## Generated artifacts

| Artifact | Blocks | Purpose |
| --- | ---: | --- |
| `out/Abyss Market.litematic` | 2,908 | Existing interior, regenerated for mouth-only access |
| `out/Abyss Mouth Access.litematic` | 450 | Inbound/outbound parkour, rests, miss catch, recovery ladders |
| `out/Abyss Sperm Whale.litematic` | 66,709 | Leviathan-scale predator landmark |
| `out/Abyss Sounding.litematic` | 164 | Tail glazing, overlook fixtures, and sound frames |
| `out/under_squid_plan/Abyss Expansion Complete.litematic` | 117,066 | Squid plus every lower-scene addition with dig manifests applied |

The greybox gate is preserved in `out/Abyss Mouth Access Greybox.litematic`,
`out/Abyss Sperm Whale Greybox.litematic`, and `out/Abyss Sounding Greybox.litematic`.

## Verified constraints

- Leviathan reservation: X97500-97614, Y95-179, Z80255-80469.
- The whale is offset west of the overlook so the reveal receives a readable three-quarter
  view of its forehead, open mouth, projecting jaw, body taper, and banked flukes.
- Its anatomy replaces the former rectangular hull with a rising spermaceti forehead,
  underslung projecting jaw, low dorsal hump and knuckles, small readable eyes, asymmetric
  pectorals, and banked flukes that remain visible from the overlook.
- Whale collision count against Park Complete, squid, and market: zero.
- Mouth access collision count against Park Complete, Well, Rig, both descents, squid, and
  market: zero.
- Sounding collision count after its 27-cell declared tail excavation: zero.
- No block in the mouth-access artifact reaches Y170, so it cannot form a surface entrance.
- Static frames ship as the reliable fallback. No reactive redstone behavior is claimed.

## Promotion gate

Offline geometry and collision checks are complete. Before calling the course live, prove both
one-way strands, each miss catch and ladder return, two-player passing at the mouth, the interior
return, and the final Prism recovery in the actual server movement model.
