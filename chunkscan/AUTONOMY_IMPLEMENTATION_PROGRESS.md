# Autonomous builder implementation progress

The full objective remains schematic-driven autonomous island construction, including navigation, stock discovery, inventory filling, repeated build/refill cycles, recovery, and final verification. The audit remains historical evidence, not the current implementation status.

## 2026-09-03: shared chest arrival and version vocabulary

Implemented:

- `ContainerInteraction.openingHit` now supplies the same loaded-world, eye-distance, visible-target-ray predicate to `Hud.fetchTo`, `ChestScan`, and `Withdraw.open`. Ordinary refill/discovery no longer starts withdrawal solely because the chest's block position is nearby. A ray hitting a wall, missing, starting inside the target, or exceeding reach cannot establish arrival.
- The locked 1.19 availability check translates the client's `iron_chain` and `short_grass` names to `chain` and `grass`. Live inventory/state IDs remain unchanged. This is a narrowly defined vocabulary translation, not permission to use newer blocks.

Evidence:

- Production sources and tests compile.
- 22 focused tests passed: `ContainerInteractionTest`, `VersionNamesTest`, and `BuildAuditTest`.
- The production-method probe against the same frozen 532,374-cell schematic now reports **zero** locked-profile name rejections, versus 237 in the historical audit. Output: `build/audit/autonomy/after-version-alias.json`.
- Whitespace diff check passed. No installed JAR was replaced.

Remaining: interaction-pose route selection and bounded approach recovery; withdrawal transaction acknowledgement; schematic state compilation and action recipes; immutable job/site registration; exact multi-plot/depot scope; shared action ownership/journal; inventory load planning/unloading; shulker recovery; access-preserving construction order; movement correctness; final coverage/commissioning; runtime integration and endurance proof. Chest visibility tests are offline geometry tests, not proof that the navigation system finds every usable pose. Name availability is not proof that a block can be placed.

Next implementation should introduce the shared execution context and state/action contracts rather than treat these fixes as a release. The goal is not complete.

## 2026-09-03: schematic state contract

Implemented `StateContract`, used by the production world/placement matcher. It retains imported property values, caches parsed contracts with a bounded cache, and distinguishes automatic neighbor-derived properties from required properties. Leaves' distance, stairs' shape, and fence/wall/pane/wire connections no longer prevent matching while their neighbors change. Facing, slab half/type, vine attachment, waterlogging, power, and rail geometry remain required. Unknown properties, invalid values, duplicate properties and malformed state specifications fail matching rather than silently succeeding.

The full suite passes: **473 tests, zero failures/errors/skips**, including five new state-contract scenarios and the existing orientation/completion tests. Log: `build/audit/state-contract-tests.log`. This corrects the neighbor-derived matching portion of A03; it does not implement multi-step fluid, power, rail or other commissioning actions. Those can still be blocked by an immediate placement-state requirement and need the forthcoming action lifecycle. No live placement run or new installed JAR is claimed.

## 2026-09-03: shared operation ownership

Added `ActionGate` and its client-thread adapter `AutomationControl`. The runtime tick paths for printer, digger, withdrawal, unbox, crafter, smelter, shop, farm and photo now participate in common ownership. An active operation retains ownership across ticks; blocked helper/withdrawal ticks do not advance their timers. Unbox can delegate withdrawal during its taking phase, and farm can synchronously delegate digging/placement without allowing unrelated callers through. Pending printer acknowledgements block new operations, including delegated farm actions, and are processed even without a standalone print design.

Movement pauses for owned interactions; queued withdrawal no longer independently freezes a different navigation-owning helper. Farm/photo retain their guidance while active and yield for container screens. Opening a container cancels the current digging swing so menu work cannot deadlock behind it. Digging releases ownership when its list empties and revalidates membership, loadedness, protection and reach before continuing. Disconnect clears all helper modes and ownership.

The final full suite passes: **477 tests, zero failures/errors/skips**. Four new ownership tests exercise cross-tick exclusion, handoff after completion, unbox delegation, farm delegation, and explicit clearing. Log: `build/audit/action-control-tests.log`. These are offline ownership/state tests, not proof of the complete runtime scheduling behavior on the server. The gate does not yet provide durable action identities, inventory transaction acknowledgements, dimension-change reconciliation, complete cancellation/asset recovery, or a persisted job scheduler. Those remain required for the goal; no release was installed.

## 2026-09-03: server-observed withdrawal reconciliation

Inspected the local 26.2 packet classes and server handler bytecode (`build/audit/server-packets-javap.txt`). The server's container-click handler updates remote predicted slots before broadcasting changes; correct predictions need not generate a matching slot echo. Waiting for arbitrary menu-state changes is therefore not an acknowledgement protocol.

Added packet-handler hooks and `MenuObservations` to retain copies of server-sent full/slot content, isolated by connection and invalidated on menu reopening. Withdrawal waits for a fresh full view instead of a nonzero menu state ID. After each quick-move it closes and reopens the same chest, then `InventoryTransfer` requires matching source loss and destination gain for the exact item/components before counting progress. If the live menu has diverged from the baseline, it refreshes that baseline before clicking. The operation retains ownership while reopening.

This deliberately costs an extra menu round trip per transferred stack. It is a functioning reconciliation strategy for vanilla's suppressed prediction echoes; throughput optimization remains necessary after runtime validation. Mismatched or unknown transfer results stop the build for inspection rather than using predicted stock. Unbox no longer starts breaking after failed withdrawal, and confirmed withdrawal progress refreshes its timeout. Automatic recovery of a box left by a failed transaction remains unfinished.

Container indexing now skips unconfirmed transfers and menus that differ from observed server state; it rereads verified contents at close instead of writing an older tick snapshot. Connection observations clear on disconnect.

Validation: **481 tests, zero failures/errors/skips**, including partial-stack reconciliation, rejected/unrelated changes, component identity, immutable observations and menu reuse. The first fixture attempt exposed missing offline item-component initialization; the test now explicitly binds its fixture item's defaults. Final log: `build/audit/inventory-observation-tests.log`. Declared mixin classes compile and target methods/signatures were inspected, but mixin application and the close/reopen transaction have not yet been exercised in a launched client/server. No installed JAR changed. The full goal remains active.

## 2026-09-03: exact plot bounds and shared site depots

`islands.json` supports explicit half-open rectangle bounds and a `site` membership field. Plot containment takes precedence over proximity to a bedrock center. Registered plots permit only their exact union; unknown coordinates are excluded, and an invalid/empty explicit registry does not fall back to a different plot or retain partial permissions. Storage scope can include the origin plot's linked site members while preserving dimension/storage-type filtering. Legacy radius entries remain supported and have separate sites by default.

Python `Plot`/`islands.plot_of` and reports consume the same exact extent. Capture refresh preserves explicit bounds/site metadata and refuses to carry it onto a different bedrock center. Existing Python callers retain inclusive `Plot.bounds` output. Schema and limitations: `SITE_REGISTRY.md`.

`audit/prepare_site_fixture.py` derives a separate expanded-park registry from the frozen profile and the existing park-anchor tool, checking the union against `park_final.world.json`. The actual production-method probe with that configuration reports **0 / 532,374 cells excluded by plot geometry**, and **66 eligible cached containers**, versus 359,647 excluded cells and zero eligible containers in the original audit. This establishes configured geometry/scope behavior only; it does not verify live permissions, stock or approach routes. Evidence: `build/audit/site-model/probe.json` and its input hashes. The real game profile was not edited, and the preview schematic remains unregistered for live construction.

Validation: **484 Java tests, zero failures/errors/skips**, including the whole 120,000-column park footprint, exact outer edges, linked versus unrelated depots, and malformed registry handling. **4 Python tests pass** for exact/legacy bounds, capture refresh preservation, and invalid extents. Final Java log: `build/audit/site-bounds-tests.log`. Full autonomy remains incomplete: job registration/context, protected volumes, durable recovery, navigation/action recipes and launched-client end-to-end proof are still required.


## 2026-09-03: conservative walking transitions

Removed the walking-to-flight-space route fallback and the later direct-steering fallback on foot. Ground routing now requires loaded feet/head clearance and immediate known support. Explicit transitions allow cardinal one-block ascent/descent with headroom/approach checks, reject unsupported diagonal corners, and prohibit vertical-only and multi-block drop edges. Ground paths retain individual edges rather than flight line-of-sight shortcuts, simplification or loose waypoints. Walking arrival uses feet height and a tight horizontal tolerance; grounded execution rechecks its next edge and stops/replans if it is invalid. Flight steering is unchanged.

Validation: **490 Java tests, zero failures/errors/skips**, including six ground movement tests for footing, diagonal corners, ascent, descent, arrival height and actual route edge continuity. Log: `build/audit/ground-path-tests.log`. An initial compile error passing the flight observation adapter instead of the client level was corrected before this successful run.

This is a conservative integer-grid guard, not a complete movement physics engine. Slab/stair collision shapes, jump trajectories, airborne replanning, flight-loss recovery, interaction-pose selection and runtime navigation remain unproven. No claim is made that every chest can now be reached. The installed JAR/profile is unchanged; previous candidate JARs predate these source fixes. Full autonomy and release readiness remain incomplete.


## 2026-09-03: world/input binding for automatic resume

Saved sessions now include `ResumeBinding`: multiplayer server address (or canonical local world directory), dimension, and a SHA-256 fingerprint of the selected schematic/work source, registration sidecar and island registry. File identity includes names and absence. Restore checks this binding before following the design or enabling movement. Missing legacy bindings, changed context, changed bytes or unreadable inputs pause resume with a reason. Failure to capture a binding clears the previous saved intent rather than retaining a stale automatic restart. Session replacement uses a temporary sibling and atomic move where supported, with replacement fallback; failed writes attempt to clear stale intent.

Validation: **494 Java tests, zero failures/errors/skips**. Four added tests cover same-size/same-timestamp source mutation, missing/changed sidecars, registry creation, server/dimension mismatch, persistence replacement and unbound legacy sessions. Log: `build/audit/resume-binding-tests.log`. Production client APIs compile; no reconnect was exercised in a launched client.

This is a resume prerequisite, not completion of A01 or A16. Active runs still need immutable snapshots and action journals. Hashing runs at remember/restore boundaries and needs asynchronous staging for large inputs; the files are not read as a transactional snapshot. A server address does not distinguish server-side world resets or island reassignment. Preview registration enforcement, protected-volume policy, in-flight reconciliation and delayed post-join context checks remain required. Explicitly restarting records a new binding; that is not yet a formal rebase workflow. No installed JAR/profile was changed. The full autonomy goal remains incomplete.


## 2026-09-03: pin input revisions during followed builds

Added `ActiveBuild`: a followed design prepares a private source/sidecar/island-registry copy under `.cscan-build-inputs/revision-*`. Preparation compares the expected binding, copied bytes and a second source fingerprint, and decodes the private schematic/work list before publishing the revision. Failed preparation removes its partial copy and leaves the previous active revision intact. Each accepted copy includes a provenance `revision.json`.

Production work, design origin/dig, facing/order/existence and island-scope readers use that revision for the active design/site. Chest observations remain in the live profile. File deletion, regeneration, origin changes or introduction of a new preferred schematic cannot silently replace active work. A later explicit start prepares a new revision. Stop, disconnect and terminal following transitions clear the active redirect. Saved intent uses the active binding rather than rereading changed source files. Restore passes its expected binding through preparation, closing the earlier check-to-follow gap for changed files.

Validation: **498 Java tests, zero failures/errors/skips** in the final full run (`build/audit/active-build-tests.log`). Four new tests exercise source/sidecar replacement, pinned cells/origin/dig/facing, a subsequent revision, work-file deletion and schematic introduction, site isolation, stale expected identity, corrupt replacement and partial-copy cleanup. An earlier full run failed the existing wall-clock-budget navigation coverage threshold (23/31 roomy routes); that run is retained as `active-build-tests-first.log`. Subsequent full runs passed without changing that navigation implementation/test. This variability is not evidence of reliable runtime routing.

Remaining: staging/hash/decode is synchronous and needs a cancellable preparation state; snapshot retention needs journal-aware garbage collection; arbitrary external edits to private copies are not currently monitored. Resume still requires matching original inputs, rather than resuming directly from a journal-owned persisted revision. This integration covers followed builds, not all standalone print/dig/helper commands or a durable fleet job. Active dimension/server transition enforcement, preview registration, action journal, inventory load planning and live end-to-end proof remain required. No JAR/profile was installed or live build claimed. Full autonomy remains incomplete.

## 2026-09-03: durable placement action evidence

`BuildJournal` records a followed-build placement before the client sends its use-item packet and records a terminal observed verdict only after the printer verifies the world. It is append-only JSONL in the source schematic directory and binds each event to world, dimension and input revision. A disconnect, missing server acknowledgement, local failure after packet dispatch, or inability to write a completion event leaves the action unresolved and stops automation. A failure to write the start record prevents the click entirely.

Before a build starts, visible pending cells are reconciled from the actual loaded world: matching state becomes `PLACED`, air becomes `STILL_AIR`, and a different block becomes `MISMATCH`. Unloaded cells remain unresolved. Any unresolved action in the same world/dimension blocks both resuming and a rebased/new revision, so replacing input files cannot erase uncertainty about a physical edit.

Validation: **502 Java tests, zero failures/errors/skips**. Four new journal tests cover start/terminal records, rejected/mismatched outcomes, revision versus physical-context isolation, and malformed/truncated journals. Log: `build/audit/journal-tests.log`. This is local filesystem/state-machine proof only. It does not prove the mixin acknowledgement arrives in a real client/server session, nor does it journal digging, temporary shulkers, inventory deltas, or complete a durable scheduler. No JAR/profile was installed. Full autonomy remains incomplete.

## 2026-09-03: durable withdrawal transfer evidence

Every followed-build quick-move now writes a `withdrawal` start record before `handleContainerInput`. Its terminal record is written only after the reopened, server-observed menu proves exact source loss and matching inventory gain. Confirmed movement records the transferred amount; `NO_CHANGE` records a zero transfer. Conflicts, menu closure, timeout, packet/local exception, unavailable start journal, and unavailable completion journal stop automation and preserve the unresolved record. Thus a possibly moved stack cannot become assumed material after reconnect.

Placement-world reconciliation intentionally does not resolve withdrawal entries. A chest/inventory transfer cannot be reconstructed safely from a target block state, so it remains a named hard stop in the same server/dimension even if a schematic revision changes.

Validation: **503 Java tests, zero failures/errors/skips** in `build/audit/withdraw-journal-tests.log`, including a transfer journal scenario across revisions and its explicit terminal outcome. This is not launched-client proof of container packet behavior, and it does not yet journal shulker unpack/recovery, inventory unloading, digging, craft/smelt/shop actions or a durable scheduler. No JAR/profile was installed. Full autonomy remains incomplete.

## 2026-09-03: autonomous-build registration gate

`ActiveBuild.prepare` now requires a real `.litematic`, its `.scan.json`, a non-preview/non-provisional/non-rebase `anchor_status`, and explicit `"automation_approved": true`. This is checked before input snapshotting, navigation, withdrawal or placement. The frozen `Park Complete` sidecar says `PREVIEW placement; rebase before building`, so it is rejected even if someone adds the approval flag. Bare work lists remain usable for manual tooling but cannot enter the unattended build loop.

Validation: **504 Java tests, zero failures/errors/skips** in `build/audit/preflight-tests.log`. New preflight cases cover unregistered work, preview status and missing explicit approval, as well as an approved registered fixture. This does not provide a live rebase/approval tool, validate server permissions, or authorize the frozen preview. No JAR/profile was installed. Full autonomy remains incomplete.

## 2026-09-03: legal chest approach poses

Storage scans and refills now route to a loaded, body-clear candidate cell whose estimated eye position has a real, in-reach ray to the chest. They no longer intentionally aim the navigator at the solid chest block. Flight candidates use flight clearance; grounded candidates require immediate support. The withdrawal executor still repeats the ray from the actual player eye before opening. If no legal pose is currently visible, it reports an approach search and does not open the chest.

Validation: **505 Java tests, zero failures/errors/skips** in `build/audit/chest-approach-tests.log`. The interaction test covers the complete nearby candidate lattice alongside existing reach, occlusion and inside-hit checks. Candidate selection against live collision/ray data compiles and remains unproven in a launched client; this does not certify every chest is reachable or replace full interaction-pose path planning. No JAR/profile was installed. Full autonomy remains incomplete.

The read-only production preflight probe against the frozen `Park Complete` sidecar returned: `REJECTED: registration says 'PREVIEW placement; rebase before building'`. Evidence: `build/audit/preflight/park-complete.txt`. This confirms the actual audited preview is blocked by the runtime gate rather than only a synthetic test fixture.

## 2026-09-03: candidate package verification

The candidate was rebuilt after subsequent source changes. The current uninstalled `build/libs/chunkscan-0.8.1.jar` has SHA-256 `40f9f01ada7ddb8a2aac257d4ea82540c478c3e00338bf5ff96e16b23a37d968`. Archive inspection confirmed the earlier package contains `ActiveBuild`, `BuildJournal`, the packet listener mixin and the mixin manifest; the current build is produced by the same verified Gradle jar task. The running LiquidLauncher profile still contains only the original `mods/chunkscan-0.8.0.jar`; it was read-only inspected and not replaced. A Fabric launched-client/server test remains required before this candidate is usable as evidence of a working autonomous builder.

## 2026-09-03: action-recipe preflight coverage

Added `ActionRecipe` preflight classification. It permits ordinary single-BlockItem placements and rejects action families that the printer does not yet implement: fluids, cauldrons, signs, wall attachments, rails/redstone, multi-blocks, multi-face attachments and double slabs. `ActiveBuild` performs this after decoding its immutable copy and before publishing a runnable job, so an approved schematic cannot start a refill trip only to fail at the first special block.

The read-only frozen Park Complete measurement reports: 7,491 fluid cells, 10,297 multi-face attachments, 2,521 redstone/rail cells, 161 wall signs, four wall attachments, ten multi-block cells, one cauldron and one sign configuration. Evidence: `build/audit/action-recipes/park-complete.json`. This explains substantially more than the previous 8,475 no-matching-BlockItem lower bound: direct inventory identity was not the only unsupported semantic.

Validation: **508 Java tests, zero failures/errors/skips** in `build/audit/action-recipe-tests.log`, including family classification and closed preflight. The probe bootstraps registries only to decode the frozen litematic; it does not start a client or modify the profile. Recipe implementation, stateful commissioning and live fixtures remain required. No JAR/profile was installed. Full autonomy remains incomplete.

## 2026-09-03: balanced multi-material refill loads

The fetch loop now chooses the least-covered addressable material during an active refill trip and caps each material at four stacks before rotating. A single-material job still takes all available room. This prevents the first large shortfall from consuming every empty slot before wood, glass or another required material can enter the pack. Target selection remains based on live confirmed carrying counts and the storage index; withdrawal still reconciles every stack before the next planning pass.

Validation: **510 Java tests, zero failures/errors/skips** in `build/audit/load-plan-tests.log`. New tests prove the planner rotates after a four-stack load and preserves full-pack behavior for a single material. This is allocation-policy proof only; actual chest travel, stock changes, slot stacking and server container behavior still require a launched-client fixture. No JAR/profile was installed. Full autonomy remains incomplete.

## 2026-09-03: double-slab recipe

Double slabs are no longer classified as unsupported. A requested `type=double` slab accepts a matching top/bottom slab as a deliberate intermediate, retains it in the todo set, and plans the next item use against that existing slab. The second placement must predict the requested double state before dispatch; a different non-air block remains a mismatch. This is the first multi-use block recipe rather than a preflight-only classification.

Validation: **511 Java tests, zero failures/errors/skips** in `build/audit/double-slab-tests.log`, including desired/intermediate distinction and non-slab rejection. Client placement geometry compiles, but the two-click vanilla behavior needs a launched-client fixture before being counted as live proof. Vines, fluids, signs, rails, redstone, doors/beds and mechanics remain blocked by preflight. No JAR/profile was installed. Full autonomy remains incomplete.

## 2026-09-03: multi-face vine recipe

Vines now use the same intermediate-action model as double slabs. A valid subset of the requested north/east/south/west/up faces remains in the work list. A new use is accepted only if prediction adds a requested face, and the last face can become the exact final state. Extra/unrequested faces, a different block, or a non-progressing use remain failures. This removes ordinary multi-face vines from special-action preflight while retaining `glow_lichen` as unsupported.

The frozen Park Complete report now has 7,491 fluid cells, 2,521 redstone/rail cells, 161 wall signs, 76 remaining multi-face attachments, four wall attachments, ten multi-block cells, one cauldron and one sign configuration: **10,265** blocked cells. The earlier 10,297 vine block count is now recipe-covered; the difference is due to the schematic's separate attachment classes. Evidence: `build/audit/action-recipes/park-complete.json`.

Validation: **512 Java tests, zero failures/errors/skips** in `build/audit/vine-recipe-tests.log`, including partial, final, no-progress and extra-face cases. This is not proof that the live server accepts every vine re-use/ray combination. Fluids, rails/redstone, signs, doors/beds, glow lichen, attachments and mechanics remain blocked. No JAR/profile was installed. Full autonomy remains incomplete.

## 2026-09-03: vanilla door and bed initiators

Doors and beds are now treated as vanilla multi-cell item actions rather than unimplemented special recipes. The work ordering places a door's lower half and a bed's foot before their upper/head cells, which vanilla creates from the initiating item use. The generated secondary cells are left for normal reconciliation after their initiators have been attempted; they are not falsely budgeted as extra items or preflight blockers.

The frozen Park Complete report no longer lists any `multi-block placement` cells. Its remaining unsupported actions are 7,491 fluid bucket placements, 2,521 redstone/rail commissioning cells, 161 wall-sign configuration cells, 76 multi-face attachments, four wall attachments, one cauldron fill and one sign configuration: **10,255** blocked cells. Evidence: `build/audit/action-recipes/park-complete.json`.

Validation: **513 Java tests, zero failures/errors/skips** in `build/audit/multiblock-tests.log`, including lower-before-upper door ordering, foot-before-head bed ordering and ordinary-block neutrality. This is source-level recipe ordering, not launched-client proof of a particular server's door/bed interaction rules. Fluids, rails/redstone, signs, glow lichen, attachments and mechanics remain blocked. No JAR/profile was installed. Full autonomy remains incomplete.

## 2026-09-03: water-bucket construction action

Water is now a real item action. Every `water` cell requests `water_bucket` from the inventory and indexed chests, so material counts, capacity checks, balanced fetch selection and withdrawal no longer look for an impossible `water` item. The printer accepts only a water bucket for this recipe, finds an in-reach visible supporting face with the same collision/ray checks as normal placement, sends the ordinary interaction, and keeps the action pending until the server acknowledgement and a world-state check. Only a source (`level=0`, or an unqualified water state) is eligible; shaped flowing water and lava remain preflight-blocked. The frozen schematic has no flowing-water blocker.

The frozen Park Complete action report now excludes 7,491 water cells. Remaining unsupported actions are 2,521 redstone/rail commissioning cells, 161 wall-sign configuration cells, 76 multi-face attachments, four wall attachments, one cauldron fill and one sign configuration: **2,765** blocked cells. Evidence: `build/audit/action-recipes/park-complete.json`.

Validation: **514 Java tests, zero failures/errors/skips** in `build/audit/water-bucket-tests.log`, including the water-to-bucket material mapping and explicit lava rejection. This has not yet been exercised in a launched client or against a server's fluid-flow rules. The builder therefore still needs an in-game contained-basin fixture before water placement is counted as release proof. No JAR/profile was installed. Full autonomy remains incomplete.

## 2026-09-03: wall-torch placement

Wall torches are ordinary `BlockItem` uses, not a separate configuration action: the existing printer already performs state prediction, support selection, visible-face ray checking and acknowledgement verification. They are consequently removed from preflight classification while signs remain blocked because their text/configuration is a distinct menu interaction.

The frozen Park Complete action report removes four wall-torch cells. Remaining unsupported actions are 2,521 redstone/rail commissioning cells, 161 wall-sign configuration cells, 76 multi-face attachments, one cauldron fill and one sign configuration: **2,761** blocked cells. Evidence: `build/audit/action-recipes/park-complete.json`.

Validation: **514 Java tests, zero failures/errors/skips** in `build/audit/wall-torch-tests.log`, including the explicit wall-torch recipe classification. A launched-client fixture remains needed to prove the client/server interaction sequence. No JAR/profile was installed. Full autonomy remains incomplete.

## 2026-09-03: unpowered redstone-wire construction

Unpowered redstone wire is now treated as an ordinary placement recipe. A wire with no explicit power or `power=0` uses the normal `BlockItem` prediction, state verification and acknowledgement path; its side connections are already correctly treated as neighbor-derived by `StateContract`. Any wire requiring power stays behind commissioning, as do powered/detector rails, repeaters and comparators.

The frozen Park Complete detailed measurement identifies 818 such wire cells and confirms that the redstone/rail blocker drops from 2,521 to 1,703. The remaining unsupported actions are 1,703 redstone/rail commissioning cells, 161 wall-sign configuration cells, 76 multi-face attachments, one cauldron fill and one sign configuration: **1,942** blocked cells. Evidence: `build/audit/action-recipes/park-complete.json` and `build/audit/action-recipes/park-complete-detail.json`.

Validation: **514 Java tests, zero failures/errors/skips** in `build/audit/redstone-wire-tests.log`, including unpowered wire acceptance and powered-wire rejection. This is source-level coverage; an in-game circuit fixture remains required before redstone placement is release proof. No JAR/profile was installed. Full autonomy remains incomplete.

## 2026-09-03: glow-lichen multi-face recipe

Glow lichen now follows the same acknowledged multi-use action model as vines across all six faces. A partial state remains work only when every existing face is requested; an interaction is accepted only when it adds a requested face and yields another valid partial state or the exact target. This prevents an unwanted extra face from being normalized into completion.

The frozen Park Complete report removes all 76 glow-lichen attachment cells. Remaining unsupported actions are 1,703 redstone/rail commissioning cells, 161 wall-sign configuration cells, one cauldron fill and one sign configuration: **1,866** blocked cells. Evidence: `build/audit/action-recipes/park-complete.json`.

Validation: **515 Java tests, zero failures/errors/skips** in `build/audit/glow-lichen-tests.log`, including partial, progress and exact-final lichen states. This still needs a launched-client fixture for the actual face/ray sequence. No JAR/profile was installed. Full autonomy remains incomplete.
