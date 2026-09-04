# Prismworks v1 - archived 2026-09-03

Jack's verdict: "prism in its current state is not a theme park, its a collection of
buildings; this is a failure of design."

Kept whole so nothing is lost: 14 designs (litematic + sidecar + work.json + renders)
and their 14 configs, exactly as shipped. Nothing here is tracked in `sync.yaml` any
more; nothing regenerates. To bring a piece back, copy the config into `configs/` and
re-run the pipeline against the current `Park Complete`.

## What was here, measured off out/Park Complete.litematic

    56,030 blocks over a 180 x 200 plot (36,000 columns)

    100%    of the plot is paved
     13.0%  of columns carry anything 3+ courses tall
      4.6%  carry anything 12+ courses tall - i.e. an actual building
    Y198-286: 88 courses used upward, 448 cells below the build plane, and
              261 courses of void underneath it never touched

    polished_blackstone_bricks 21,407 + smooth_basalt 9,197 = 54% of the land in
    two dark greys

## Why it failed, in one line each

- SIX BOXES IN A CORNER AND A LAWN. Half the plot is grass with a path grid on it.
  A path that crosses nothing is not circulation, it is a diagram.
- THE HEADLINE RIDE HAS NO RIDE IN IT. `pf_prismworks_prism_ascent.yaml` says so in
  its own docstring: "THE PARKOUR COURSE IS NOT IN HERE... This design is the SPIRE
  the course will be hung on." It shipped as a decorated tower and reads as one.
- ONE VALUE, ONE HUE. Six greys between L38 and L73 is a ladder inside one family,
  which this repo has now concluded four separate times cannot draw a line.
- THE WYRM ARCH STANDS ON A LAWN CONNECTED TO NOTHING.
- THE UNUSED DIMENSION IS DOWN. The plot's largest free asset is the 261 courses of
  void beneath it, and v1 put 448 cells there.

Superseded by the Prismworks v2 plan (spiral descent).
