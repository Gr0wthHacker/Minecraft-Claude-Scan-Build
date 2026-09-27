# Generator mechanics contract

Every output from `mcbuild` records a `mechanics` manifest in its sidecar. The manifest is derived
from the finished schematic using Mojang registry kinds, so it names what the design really uses,
not what its config meant to use.

| Family | Local verifier | Boundary |
| --- | --- | --- |
| Redstone | `mcbuild.circuit` | Entity/world inputs are stated with `set_signal` or `observe`. |
| Rails | `mcbuild.circuit` and ride contracts | Cart kinematics still need an in-game ride. |
| Fluids | `mcbuild.fluids` | Flow and containment are modelled; boats/entity motion are not. |
| Traversal/access | `mcbuild.walk`, `audit.check_climb` | Tests prove a route, not player judgement. |
| Lighting | `mcbuild.nightlight` | Block-light propagation is modelled. |
| Containers | contracts or operator metadata | Inventory/entity movement is an explicit input. |
| Hazards | audit plus generator safety contracts | Fire, lava, TNT, and fall outcomes require their own contracts. |
| Signage | audit support/state checks | Sign text is present in schematic tile data. |

The target is Minecraft Java **1.19**. New mechanics are added only with a source, a capability
entry, and a regression test. Tutorials are design references; they never substitute for a local
contract test.

## Build-purpose contracts

The manifest also records a generator's *role*. Every public generator receives the universal
construction contract (legal states, support, stable components and a bill of materials), so even
small dressing generators are covered. Bridges additionally carry continuity, clearance and
support obligations; paths carry traversability and deliberate access; sculptures carry
connectedness, support, silhouette and material-hierarchy obligations. Rides, buildings and
landscapes receive their corresponding route, access, state, fluid and terrain obligations. A
derived design can declare one or more top-level `roles` in its YAML config.
