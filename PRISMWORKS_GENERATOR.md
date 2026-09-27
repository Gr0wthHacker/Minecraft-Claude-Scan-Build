# Prismworks Generator Contract

Prismworks is the right-hand replacement land defined in [PARK_FINAL_ARCHITECTED_PLAN.md](PARK_FINAL_ARCHITECTED_PLAN.md). Its generators produce physical, bounded modules only; the server integration layer remains explicit and must never be implied by decorative blocks.

## Available modules

| Config | Generator kind | Physical result | Not certified by generation |
| --- | --- | --- | --- |
| `configs/prism_ascent.yaml` | `ascent` | connected bubble-lift Spire, launch deck, supported descending landings, water catches, observer balconies, return floor | actual bubble travel, catch safety, checkpoint timing/reset |
| `configs/prism_array.yaml` | `array` | a 35 by 35 navigable maze, fixed solved route, recoverable branches, connected colour markers | sign rule comprehension and player walkthrough |
| `configs/resonance_vault.yaml` | `vault` | shell, distinct supported stations, entry/exit/service apertures | the three-input completion circuit and reset |

All three use only the active `skyblock-1.19` server registry. The Ascent's nominal 88 block lift is intentionally below the park vertical allowance; its world placement owns the final Y value and view corridors.

## Generator boundary

A generator may state an in-game proof obligation under `requires_in_game`. It must not claim that obligation is done merely because a litematic contains water, buttons, lamps, or signs.

The grass-payment chest is server-authoritative: the server integration verifies the deposited item is grass and releases the paid run. A comparator or observer, if used, is only local acknowledgement/reset feedback. Do not make a redstone item filter the payment authority.

The Vault likewise has physical station geometry but no fictional completion circuit. Add the actual circuit in a dedicated redstone ticket, then prove simultaneous/ordered inputs, result opening, reset, failure recovery, and maintenance isolation in a live world.

## Required config contract

Every public Prismworks config needs:

- typed player anchors for approach, entry/boarding, exit, and service;
- a design brief with enforced footprint/height expectations;
- an enforced `fun_contract`;
- finish settings that do not hollow or discard route/support geometry.

For an experience, `fun_contract` requires nonempty player verbs, a visible outcome, reset, service access, and bypass. Routes or scenic support instead declare their spatial job. This rejects polished-looking modules with no player purpose.

## Normal verification

```powershell
python -m pytest tests/test_prismworks.py tests/test_generator_contract.py tests/test_design_quality.py -q
python -m mcbuild gen configs/prism_ascent.yaml --out-dir out
python -m mcbuild gen configs/prism_array.yaml --out-dir out
python -m mcbuild gen configs/resonance_vault.yaml --out-dir out
```

Then use the generated sidecar and visual review packet before siting into the 600 by 200 WorldSpec. Run the in-game proof listed above before a module is promoted as functional.

