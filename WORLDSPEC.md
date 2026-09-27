# Skyblock World Specification

`mcbuild` world planning is explicitly bounded to a real Skyblock island or marked build point. It does not infer an infinite overworld or overwrite existing island assets.

Compile a brief with:

```powershell
python -m mcbuild worldspec skypark.world.json --out out/skypark.world.plan.json --enforce
```

## Required site contract

```json
{
  "name": "Sky Park",
  "seed": 17,
  "site": {
    "mode": "skyblock",
    "anchor": [100, 72, -50],
    "build_plane": 72,
    "bounds": [0, 0, 96, 96],
    "entry_points": [[2, 48]],
    "protected": [[46, 46, 50, 50]]
  }
}
```

`anchor` is the captured/marked world point. All bounds, regions, plots, and route points are local to that point. `protected` boxes reserve starter chests, bedrock, transit, or completed infrastructure. The compiler refuses regions and plots outside the stated island envelope.

Every public module also declares exact `access_points`, not a vague nearby plot. `worldspec --enforce` proves those points reach the declared island entry through the full-width public path graph.

Routes may use `[x,z]` control points for level paving or `[x,y,z]` points for actual physical infrastructure. Three-dimensional `path`, `ramp`, `stairs`, and `bridge` routes compile grade-limited courses, deck cells, start/end anchors, bridge supports, and rail requirements before a themed renderer places blocks.

Declare `view_corridors` for arrival-to-landmark and street-to-skyline views. A module with a real placed footprint cannot consume a protected corridor, preventing later build passes from burying the park's visual hierarchy.

## World layers

1. **Platform:** declared build plane, foundations, void-safe retaining edges, vertical supports.
2. **Infrastructure:** paths, rail, bridges, stairs, ramps, water channels, utility/service routes.
3. **Shell:** blueprint-backed buildings, landmarks, and ride stations.
4. **Interior:** rooms, queues, mechanics, storage, and staff/service access.
5. **Detail:** landscape, lighting, props, signage, and controlled visual variation.
6. **Review:** route, mechanics, composition, render, and parallel-promotion evidence.

## Scaling safely

`mcbuild.world.SparseWorld` stores only occupied cells in 16-block chunks, avoiding a giant dense schematic allocation for empty Skyblock void. `mcbuild.buildgraph.schedule` assigns chunks and dependencies to workers; duplicate chunk ownership and cyclic dependencies fail before generation. `mcbuild.cache.impacted` identifies only artifacts that must rebuild after a changed source/config/dependency hash.

`worldexport.export_chunks` writes a Litematica **and scan sidecar** per occupied chunk, so the resulting artifacts can be passed directly to `mcbuild worldvalidate --entry X Y Z --destination X,Y,Z ...` for an assembled-world collision, headroom, and walking audit.

The existing planner remains the source of truth for an approved island plan. WorldSpec adds the larger composition envelope around it, rather than replacing existing captures, path contracts, or frozen parallel manifests.
