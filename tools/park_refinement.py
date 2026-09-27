"""Apply the reviewed furnishings after terrain hollowing and plant decluttering."""
from pathlib import Path
from mcbuild import scan


def apply(model, origin, artifact=None):
    artifact = Path(artifact or Path(__file__).resolve().parents[1] / 'out/PF Premium Refinement.litematic')
    addition = scan.load(str(artifact))
    bounds = tuple(origin[i] + model.shape_xyz[i] for i in range(3))
    if any(addition.origin[i] < origin[i] or addition.origin[i] + addition.size[i] > bounds[i] for i in range(3)):
        raise ValueError('Refinement must stay inside the existing park bounds')
    context = scan.Scan(model, {'origin': dict(zip(('x','y','z'),origin))}, '', '')
    merged, overlaps = scan.merge(context, addition.model, addition.origin)
    if overlaps:
        raise ValueError(f'Refinement clashes with {overlaps} existing cells; review placements before rebuilding')
    return merged
