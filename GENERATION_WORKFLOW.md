# Production Generation Workflow

Every substantial Skyblock module follows this sequence:

```text
strict WorldSpec → greybox → review/gate → detailed generator → cache → assemble → worldvalidate → visual packet → promotion
```

## 1. Greybox first

Create a blueprint and run:

```powershell
python -m mcbuild greybox building.json --out out/building-greybox.litematic
```

Approve only when the footprint, vertical massing, rooms, entrances/exits, service access, path connection, and skyline role are correct. Do not add expensive façade, redstone, landscaping, or interiors before this gate.

## 2. Strict detail generation

Detailed module configs use `world_contract: true`, a `blueprint`, typed anchors, a declared role, and the Skyblock 1.19 profile. They may opt into reuse with:

```yaml
cache_dir: out/cache
```

The pipeline reports generation time and output block count. Identical source/config/profile input reuses its cached artifact rather than regenerating.

## 3. Assemble and prove

Generate infrastructure with `worldbuild`, emit module configs from `worldspec --emit`, then use `worldvalidate` across the placed artifacts. Promotion requires compatibility, collision, route, mechanics, budget, and visual-review evidence.

## 4. Spend detail deliberately

High detail: arrival, landmark, ride approach, queue, exit, skyline, food/recovery, key interiors.

Low detail: hidden backs, void-facing structural fill, concealed service corridors, repetitive secondary walls.

This keeps quality per block, generation second, and player minute high.
