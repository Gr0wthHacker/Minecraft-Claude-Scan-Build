"""Consolidate the frozen workload and offline Java probe; run after both diagnostics."""
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parents[2]
audit = root / 'chunkscan/build/audit/autonomy'
workload = json.loads((audit / 'workload.json').read_text(encoding='utf-8'))
probe = json.loads((audit / 'java-probe.json').read_text(encoding='utf-8'))
assert workload['nonair'] == probe['cells'], 'Inputs changed between diagnostics'
for name, digest in probe['input_sha256'].items():
    assert workload['manifest'][name]['sha256'] == digest, f'Input revision mismatch: {name}'
containers = json.loads((audit / 'snapshot/storage.json').read_text(encoding='utf-8'))['containers']
depots = {}
for name, xmin, xmax, zmin, zmax in [('left',97500,97700,80300,80500),
        ('middle',97500,97700,80500,80700), ('right',97500,97700,80700,80900),
        ('old_main',-24249,-24150,29951,30050)]:
    rows = [c for c in containers if xmin <= c['x'] < xmax and zmin <= c['z'] < zmax
            and c.get('dimension') == 'minecraft:overworld']
    depots[name] = {'cached_records': len(rows),
                   'cached_loose_items': sum(sum(c.get('items', {}).values()) for c in rows),
                   'cached_boxed_items': sum(sum(c.get('inBoxes', {}).values()) for c in rows)}
sources = sorted((root / 'chunkscan/src/client/java').rglob('*.java'))
hashes = {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
result = {'date':'2026-09-03', 'live_game_verified':False, 'workload':workload,
          'production_method_probe':probe, 'cached_storage_by_expanded_plot':depots,
          'source_sha256':hashes,
          'prior_candidate_validation':json.loads((audit.parent / 'validation.json').read_text(encoding='utf-8'))}
(root / 'chunkscan/audit/evidence.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print(json.dumps({'depot_counts':depots, 'source_files':len(sources),
                  'outside_percent':round(100*probe['cells_rejected_by_current_plot_model']/probe['cells'],2),
                  'no_direct_item':sum(probe['no_matching_block_item_cells'].values()),
                  'snapshot_sha256':workload['manifest']['Park Complete.litematic']['sha256']},indent=2))
