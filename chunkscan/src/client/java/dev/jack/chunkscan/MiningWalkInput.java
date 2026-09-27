package dev.jack.chunkscan;

import net.minecraft.client.Minecraft;
import net.minecraft.client.player.LocalPlayer;
import net.minecraft.client.player.ClientInput;
import net.minecraft.world.entity.player.Input;
import net.minecraft.world.phys.Vec2;
import net.minecraft.world.phys.Vec3;

/** Mining uses vanilla ground acceleration and collision handling, not injected velocity. */
final class MiningWalkInput {
    private static LocalPlayer owner;
    private static ClientInput previous;
    private static final Drive drive = new Drive();

    private static final class Drive extends ClientInput {
        float forward;
        @Override public void tick() {
            keyPresses = new Input(forward > 0, false, false, false, false, false, false);
            moveVector = new Vec2(0, forward);
        }
    }

    static float turn(float yaw, float target) {
        float delta = (target - yaw) % 360;
        if (delta <= -180) delta += 360;
        if (delta > 180) delta -= 360;
        return yaw + Math.max(-12, Math.min(12, delta));
    }

    static float forwardAmount(float yaw, float target, double distance) {
        double alignment = Math.cos(Math.toRadians(target - yaw));
        // Turn in place before accelerating, so sharp corners cannot cut across walls.
        return alignment < 0.98 ? 0 : (float)Math.min(1, distance / 0.5);
    }

    static void stop(Minecraft mc) {
        if (owner != null && owner.input == drive) owner.input = previous;
        owner = null;
        previous = null;
        drive.forward = 0;
        drive.tick();
    }

    static void walk(Minecraft mc, LocalPlayer p, Vec3 aim) {
        double dx = aim.x-p.getX(), dz = aim.z-p.getZ();
        if (dx*dx+dz*dz < 0.01) { stop(mc); return; }
        float yaw = (float)Math.toDegrees(Math.atan2(-dx,dz));
        p.setYRot(turn(p.getYRot(), yaw));
        p.setSprinting(false);
        if (owner != p || p.input != drive) {
            stop(mc);
            owner = p;
            previous = p.input;
            p.input = drive;
        }
        // Own the actual vanilla movement input. Synthetic key states can be reset by
        // focus/screens before KeyboardInput samples them, leaving only camera motion.
        drive.forward = forwardAmount(p.getYRot(), yaw, Math.sqrt(dx*dx+dz*dz));
        drive.tick();
        // A vanilla grounded jump, never the jump-key double tap that enables flight.
        if (drive.forward > 0 && p.onGround() && aim.y > p.getY()+0.6) p.jumpFromGround();
    }
}
