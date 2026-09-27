package dev.jack.chunkscan;

/** Grounded grid transitions: walk, one-block step/jump, or one-block descent. */
final class WalkingSpace implements Nav.Passable {
    /** Validate the planned ground edge, not the transient block occupied mid-jump. */
    static boolean committedStepFits(Nav.Passable ground, net.minecraft.core.BlockPos from,
                                     net.minecraft.core.BlockPos next) {
        if (from == null || !ground.at(next.getX(), next.getY(), next.getZ())) return false;
        return from.equals(next) || Nav.stepFits(ground, from.getX(), from.getY(), from.getZ(),
            next.getX()-from.getX(), next.getY()-from.getY(), next.getZ()-from.getZ());
    }

    static net.minecraft.world.phys.Vec3 horizontalStep(net.minecraft.world.phys.Vec3 feet,
                                                       net.minecraft.world.phys.Vec3 aim, double speed) {
        var delta = new net.minecraft.world.phys.Vec3(aim.x-feet.x, 0, aim.z-feet.z);
        double distance = delta.length();
        return distance <= speed ? delta : delta.scale(speed/distance);
    }

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

    /** The same walk confined to the cells {@code cell} allows - see Bounds.within. */
    WalkingSpace confined(Nav.Passable cell) {
        Nav.Passable b = body;
        return new WalkingSpace((x, y, z) -> cell.at(x, y, z) && b.at(x, y, z), footing);
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
