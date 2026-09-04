package dev.jack.chunkscan;

/** Grounded grid transitions: walk, one-block step/jump, or one-block descent. */
final class WalkingSpace implements Nav.Passable {
    private final Nav.Passable body;
    private final Nav.Passable footing;

    WalkingSpace(Nav.Passable body, Nav.Passable footing) {
        this.body = body;
        this.footing = footing;
    }

    @Override public boolean at(int x, int y, int z) {
        return body.at(x,y,z) && footing.at(x,y-1,z);
    }

    static boolean arrived(net.minecraft.world.phys.Vec3 feet, net.minecraft.core.BlockPos node) {
        double dx = feet.x - (node.getX()+0.5), dz = feet.z - (node.getZ()+0.5);
        return dx*dx + dz*dz <= 0.09 && Math.abs(feet.y-node.getY()) <= 0.25;
    }

    boolean step(int x, int y, int z, int dx, int dy, int dz) {
        if (Math.abs(dx)>1 || Math.abs(dy)>1 || Math.abs(dz)>1 || (dx==0 && dz==0)) return false;
        if (!at(x,y,z) || !at(x+dx,y+dy,z+dz)) return false;
        if (dy != 0) {
            // Diagonal height changes need a swept jump model; take cardinal steps instead.
            if (Math.abs(dx)+Math.abs(dz) != 1) return false;
            return dy > 0 ? body.at(x,y+1,z) : body.at(x+dx,y,z+dz);
        }
        return (dx==0 || dz==0) || (at(x+dx,y,z) && at(x,y,z+dz));
    }
}
