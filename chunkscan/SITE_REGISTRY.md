# Exact plots and linked storage

`islands.json` now accepts exact half-open bounds and explicit site membership. Existing entries without these fields keep their radius-based footprint and a site named after the island itself.

```json
{
  "islands": {
    "islandleft": {
      "cx": 97600,
      "cz": 80400,
      "radius": 49,
      "site": "park",
      "bounds": {
        "min_x": 97500,
        "min_z": 80300,
        "max_x_exclusive": 97700,
        "max_z_exclusive": 80500
      }
    }
  }
}
```

This entry covers exactly X97500..97699 and Z80300..80499. When `bounds` is present it controls geometry; `radius` remains legacy metadata. The bedrock center must be inside the declared bounds. Java placement checks and Python `plot_of`/`Plot.contains` use the same extent. Python `Plot.bounds` retains its existing **inclusive** return convention for callers. Capture refresh preserves bounds and site; it refuses to apply old exact bounds to a different bedrock center.

Containers can supply a design from any registered plot with the same `site` as its origin plot. Dimension matching and storage-type filtering still apply. Islands without explicit site membership do not share stock merely because they have the same owner or are nearby. A known registry excludes all unregistered coordinates. An empty or malformed registry disables Java automatic placement and storage fallback; an absent registry retains the older single-plot behavior.

`audit/prepare_site_fixture.py` derives a separate park configuration from the frozen audit registry and `tools/park_anchor.py`, cross-checks it against `park_final.world.json`, and writes only `build/audit/site-model`. Run the existing `AutonomyProbe` with that directory as both inputs to compare actual schematic/depot coverage. This is a diagnostic configuration, not a change to the game profile or approval of the preview schematic.

Remaining job-context requirements include server identity, permission verification, protected volumes, immutable registration, separately controlled depot permissions, and restart reconciliation. Plot membership alone does not establish those requirements.
