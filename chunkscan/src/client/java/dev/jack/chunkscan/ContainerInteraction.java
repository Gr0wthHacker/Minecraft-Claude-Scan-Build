package dev.jack.chunkscan;

import net.minecraft.client.Minecraft;
import net.minecraft.core.BlockPos;
import net.minecraft.world.level.ClipContext;
import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.phys.HitResult;
import net.minecraft.world.phys.Vec3;

import java.util.Comparator;
import java.util.Set;
import java.util.stream.Stream;

/**
 * Where to stand to open a container, and whether you can open it from where you are.
 *
 * <p>Jack: <i>"it doesnt get close enough to chests, chests need to be within 2 blocks"</i>. The
 * first version of {@link #approach} chose the candidate NEAREST THE PLAYER that had a clear line to
 * the chest inside {@link Withdraw#REACH} — which is a cell up to four and a half blocks from the
 * chest, and the flight then parked up to three short of THAT. Two other things followed from it:
 *
 * <ul>
 * <li>the candidate could stand ON THE FLOOR beside the chest. The autopilot never descends inside
 *     {@link Autopilot#GROUND_CLEAR} of a floor (touching it ends flight on this server), so it
 *     hovered two blocks over the cell it was sent to and the opening test never passed;</li>
 * <li>and because the choice was relative to the player, it moved as the player moved, so the
 *     destination changed under the flight.</li>
 * </ul>
 *
 * <p>An approach cell now has to have a CLEAR CELL UNDER IT, so a body hovering in it keeps more
 * than a block of air beneath — see {@link #HOVER_CLEAR} — and candidates are ranked by how close
 * they are to the CHEST, with {@link #CLOSE} blocks preferred outright, and only then by how far
 * they are from the player. Cells that have already been tried and failed to open from are passed
 * in and skipped, so a chest with an awkward face gets a second angle rather than an infinite wait.
 */
final class ContainerInteraction {
    private ContainerInteraction() {}

	/** Horizontal distance from the chest inside which an approach cell is preferred outright. */
	static final int CLOSE = 2;
	/** Clear cells required under an approach cell, so hovering in it is not standing on a floor. */
	// TWO, NOT ONE. Jack: "it can't be within 1 block beneath when flying to place because it will
	// auto stop flying" - that is why GROUND_CLEAR is two and a half everywhere else, and the chest
	// approach was the one place the body was flown to a block of air over a floor. Every fetch
	// was therefore a chance to lose flight, and "within 2 blocks" is a HORIZONTAL ask: from a cell
	// two clear cells over the chest's own floor the eyes are ~3.4 from a chest one block over,
	// inside Withdraw.REACH, and the opening ray is still tested from exactly that cell.
	static final int HOVER_CLEAR = 2;

    static BlockHitResult openingHit(Minecraft mc, BlockPos target) {
        if (mc.player == null || mc.level == null || !mc.level.isLoaded(target)) return null;
		return openingHit(mc, target, mc.player.getEyePosition());
    }

	static BlockPos approach(Minecraft mc, BlockPos target) {
		return approach(mc, target, Set.of());
	}

	static BlockPos approach(Minecraft mc, BlockPos target, Set<Long> tried) {
		if (mc.player == null || mc.level == null || !mc.level.isLoaded(target)) return null;
		boolean flying = mc.player.getAbilities().flying;
		double eyeHeight = mc.player.getEyePosition().y - mc.player.getY();
		BlockPos me = mc.player.blockPosition();
		Comparator<BlockPos> best = Comparator.comparingInt((BlockPos p) -> rank(p, target))
			.thenComparingDouble(p -> p.distSqr(target))
			.thenComparingDouble(p -> p.distSqr(me));
		// A CELL TO HOVER IN IS PREFERRED, AND A CELL TO STAND IN IS STILL A CELL.
		//
		// Measured off Jack's own session log: three chests in a row answered `cannot find
		// anywhere to open ... from` and were cooled off for a minute, and one of them was a
		// chest the loop had successfully opened four minutes earlier. The difference was not
		// the chest, it was whether the body happened to be FLYING: hovering asks for two clear
		// cells UNDER the approach cell, and a chest stands on a floor. The only cell that can
		// satisfy that is two courses above the floor beside it, so a chest under any ceiling
		// lower than three - a shop, a store room, a niche, most of this island - has no
		// hovering approach at all, and the whole index became unopenable the moment autofly
		// was on. Reported as: the collection constantly breaks.
		//
		// Landing beside a chest is what a player does, and it is safe in the one way that
		// matters here: there is a floor under you by construction, so losing flight costs a
		// double-tap (Autopilot.regain) rather than the void. Hovering is still first choice -
		// it keeps the flight - and this is the fallback rather than the rule.
		if (flying) {
			BlockPos hover = candidates(mc, target, tried, Nav.of(mc.level), eyeHeight)
				.filter(p -> hoverable(mc, p)).min(best).orElse(null);
			if (hover != null) return hover;
		}
		return candidates(mc, target, tried, Nav.standable(mc.level), eyeHeight).min(best).orElse(null);
	}

	/**
	 * Does opening the chest from this cell mean landing in it?
	 *
	 * <p>The caller has to know, because a flight guided at a cell it cannot hover in holds its
	 * ground clearance and never arrives - which is the six-second wait `Hud.FETCH_STUCK_MS`
	 * exists to break out of. Told, the flight descends and lands instead.
	 */
	static boolean mustLand(Minecraft mc, BlockPos approach) {
		return mc.player != null && mc.level != null
			&& mc.player.getAbilities().flying && !hoverable(mc, approach);
	}

	private static Stream<BlockPos> candidates(Minecraft mc, BlockPos target, Set<Long> tried,
	                                           Nav.Passable room, double eyeHeight) {
		var space = Bounds.within(room);
		return approachCells(target)
			.filter(p -> !tried.contains(p.asLong()))
			.filter(Bounds::contains)                   // an approach cell outside the fence is refused, six seconds at a time
			.filter(p -> mc.level.isLoaded(p) && mc.level.isLoaded(p.above())
				&& space.at(p.getX(), p.getY(), p.getZ())
				&& openingHit(mc, target, eyeAt(p, eyeHeight)) != null);
	}

	/** Where the eyes are when the body hovers in a cell — the same point the flight aims at. */
	static Vec3 eyeAt(BlockPos p, double eyeHeight) {
		Vec3 feet = Autopilot.flyTo(p);
		return new Vec3(feet.x, feet.y + eyeHeight, feet.z);
	}

	/** A cell a flight can hover in without standing on anything: air under it, and loaded. */
	private static boolean hoverable(Minecraft mc, BlockPos p) {
		for (int d = 1; d <= HOVER_CLEAR; d++) {
			BlockPos b = p.below(d);
			if (!mc.level.isLoaded(b) || mc.level.getBlockState(b).blocksMotion()) return false;
		}
		return true;
	}

	/** 0 for a cell within {@link #CLOSE} of the chest horizontally, 1 for anything further. */
	static int rank(BlockPos p, BlockPos target) {
		int dx = Math.abs(p.getX() - target.getX()), dz = Math.abs(p.getZ() - target.getZ());
		return Math.max(dx, dz) <= CLOSE ? 0 : 1;
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
