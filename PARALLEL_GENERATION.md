# Parallel generation

Large plans are generated in isolated lanes, then assembled once. This is for agents producing
assets; player/build-account allocation remains `mcbuild fleet`.

```powershell
python -m mcbuild parallel --prepare park_centre
python -m mcbuild parallel --scope park_centre midway
python -m mcbuild parallel --run park_centre midway
python -m mcbuild parallel --run park_centre frontier
python -m mcbuild parallel --run park_centre hollow
python -m mcbuild parallel --validate park_centre
python -m mcbuild parallel --gate park_centre
python -m mcbuild parallel --promote park_centre --name "Park Centre Complete"
```

`--prepare` only accepts an approved planner plan. It freezes one config per module under
`out/parallel/<plan>/configs` and writes `parallel.json`. The file is immutable: change the plan,
approve it, and prepare a new plan name rather than modifying inputs beneath a running worker.

Each worker may read the frozen configs and write only below its own
`out/parallel/<plan>/lanes/<lane>/out` directory. For the theme park, `params.land` naturally
creates the `midway`, `frontier`, and `hollow` lanes. This makes output ownership explicit and
keeps agents from overwriting shared YAML or another worker's `.litematic`/sidecar pair.

Validation refuses missing artifacts and any block claimed by two different lanes. Intentional
overlaps within one lane are preserved as whole module artifacts and resolved only at assembly,
in approved plan order (first writer wins), matching the established layers workflow. The assembler
is single-writer and publishes one complete litematic plus sidecar; it preserves block states and
tile entities from winning modules.

## Acceptance evidence

Frozen configs carry a SHA-256 digest. A worker refuses a changed config and writes an
`evidence.json` record for every artifact: litematic and sidecar hashes, audit result, block count,
component sizes, mechanics manifest, and whether it rendered the artifact. The acceptance gate
requires all evidence, clean local audits, complete staging, and zero cross-lane claims before
promotion.

Each lane also has an explicit allowed write root and optional `owned_files` declared by the
approved plan. An orchestrator should pass an agent's changed paths to `parallel.check_paths()`
before accepting source changes; shared generators and frozen configs are denied by default.

The gate deliberately reports visitor-route endpoints, entity/ride behaviour, and visual judgement
as plan-specific review items. Those need dedicated contracts such as the existing park-flow and
ride suites; a generic schematic union cannot prove them honestly.
