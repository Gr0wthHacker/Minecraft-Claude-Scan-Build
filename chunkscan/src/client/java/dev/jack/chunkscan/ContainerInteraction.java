package dev.jack.chunkscan;

import net.minecraft.client.Minecraft;
import net.minecraft.core.BlockPos;
import net.minecraft.world.level.ClipContext;
import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.phys.HitResult;
import net.minecraft.world.phys.Vec3;

import java.util.Comparator;
import java.util.stream.Stream;

/** One arrival predicate shared by chest navigation and the interaction executor. */
final class ContainerInteraction {
    private ContainerInteraction() {}

    static BlockHitResult openingHit(Minecraft mc, BlockPos target) {
        if (mc.player == null || mc.level == null || !mc.level.isLoaded(target)) return null;
		return openingHit(mc, target, mc.player.getEyePosition());
    }

	/** A loaded, body-clear point from which the actual chest ray is valid. */
	static BlockPos approach(Minecraft mc, BlockPos target) {
		if (mc.player == null || mc.level == null || !mc.level.isLoaded(target)) return null;
		var space = mc.player.getAbilities().flying ? Nav.of(mc.level) : Nav.standable(mc.level);
		double eyeHeight = mc.player.getEyePosition().y - mc.player.getY();
		return approachCells(target).filter(p -> mc.level.isLoaded(p) && mc.level.isLoaded(p.above())
			&& space.at(p.getX(), p.getY(), p.getZ())
			&& openingHit(mc, target, new Vec3(p.getX() + .5, p.getY() + eyeHeight, p.getZ() + .5)) != null)
			.min(Comparator.comparingDouble(p -> p.distSqr(mc.player.blockPosition()))).orElse(null);
	}

	static Stream<BlockPos> approachCells(BlockPos target) {
		return java.util.stream.IntStream.rangeClosed(-4, 4).boxed().flatMap(dx ->
			java.util.stream.IntStream.rangeClosed(-2, 2).boxed().flatMap(dy ->
				java.util.stream.IntStream.rangeClosed(-4, 4).mapToObj(dz -> target.offset(dx, dy, dz))));
	}

	private static BlockHitResult openingHit(Minecraft mc, BlockPos target, Vec3 eye) {
		BlockHitResult hit = mc.level.clip(new ClipContext(eye, Vec3.atCenterOf(target),
			ClipContext.Block.OUTLINE, ClipContext.Fluid.NONE, mc.player));
		return accepts(eye, target, hit, Withdraw.REACH) ? hit : null;
	}

    static boolean accepts(Vec3 eye, BlockPos target, BlockHitResult hit, double reach) {
        return hit != null && hit.getType() == HitResult.Type.BLOCK
            && hit.getBlockPos().equals(target) && !hit.isInside()
            && eye.distanceToSqr(hit.getLocation()) <= reach * reach;
    }
}
