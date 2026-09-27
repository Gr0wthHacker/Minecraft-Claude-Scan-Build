## What this system can and cannot build (2026-08-19)

Settled by PLAYER RECEPTION, not by the rubric and not by my renders. The builds players picked out
are the **sky bird** (an 83-block wingspan of layered primaries) and the **giraffe** (a neck); the
**gecko** — splayed limbs on a wall — is the next best thing in the repo. Every animal that reads
badly is a mammal.

**The line is PLANAR/COLUMNAR against VOLUMETRIC.** A spread wing, a neck, a stilt leg, a splayed
limb: flat sheets and straight tapers, which is what voxels render natively. A cat's shoulder or a
bear's haunch is compound volumetric muscle, which voxels render worst of anything — and no amount
of scale rescues it. The jaguar at 2.6x and 60,000 blocks failed exactly as the 27-block one did.

This is not the same as "hardware vs muscle", which was my earlier guess and was the wrong cut. An
elephant's trunk is hardware AND a taper; a caiman's body is hardware and still a volume.

**Build these:** birds, bats, wading birds, reptiles with splayed limbs, anything whose identity is
an outline. `heron.py` and `bat.py` are the two worked examples, both bespoke — the quadruped family
system is built around a mammal barrel and should not be used for them.

**Do not build:** cats, bears, or anything whose species is carried by muscle mass. `quadruped.py`
still holds eight of them and they score GOOD; the score is measuring the wrong thing.

**Amended 2026-08-27 by the download corpus** - see "Reading other people's builds" below. The
line is not the species, it is whether the silhouette decomposes into LIMBS: a curled cat built as
one convex mass reads instantly, and a corpus of 31 outside builds contains no realistically-
proportioned quadruped at all.

