package dev.jack.chunkscan;

import net.minecraft.client.Minecraft;
import net.minecraft.client.player.LocalPlayer;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.item.BlockItem;
import net.minecraft.world.item.BucketItem;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.phys.Vec3;
import net.minecraft.world.level.ClipContext;
import net.minecraft.world.item.context.BlockPlaceContext;
import net.minecraft.world.inventory.ContainerInput;
import net.minecraft.network.protocol.game.ServerboundMovePlayerPacket;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;

/** Normal block interactions with live support, visibility, state prediction and server acknowledgement. */
final class Printer {
	/** Vanilla reach is ~4.5; stay inside it so a placement is never refused for distance alone. */
	static final double REACH = 4.2;
	/** Ticks between placements. Vanilla holding right-click is one per tick; this is gentler. */
	static int interval = 2;
	/** A cell that has failed this many times is somebody else's problem. */
	static final int MAX_TRIES = 2;

	private Printer() {}

	/** What one attempt turned into, once the world has been looked at again. */
	enum Verdict { PLACED, MISMATCH, STILL_AIR, BLOCKED, NO_ITEM, NO_FACE, OUT_OF_REACH, REFUSED }

	record Attempt(BlockPos pos, String want, Verdict verdict, String got) {}

	// ---------------------------------------------------------------- geometry

	/**
	 * A face to click, given the cell we want to fill.
	 *
	 * <p>You place a block by clicking an existing one and the new block appears against the face
	 * you clicked, so what is needed is a solid NEIGHBOUR and the direction from it back to us.
	 * Returns null when the cell is floating — which is the scaffolding question the loop already
	 * asks, answered here from the same evidence.
	 */
	static Direction[] faces() {
		// Down first: a block placed on top of another is the commonest and the least ambiguous,
		// and it is what a player does. Sides before up, because clicking a ceiling is awkward and
		// more likely to be out of reach from a standing spot.
		return new Direction[] {Direction.UP, Direction.NORTH, Direction.SOUTH,
			Direction.EAST, Direction.WEST, Direction.DOWN};
	}

	/**
	 * Where in the clicked face to aim, so that {@code half}/{@code type} come out right.
	 *
	 * <p>A slab is {@code type=bottom} when the hit is in the lower half of the clicked face and
	 * {@code top} when it is in the upper half; a stair's {@code half} is the same question. Aim
	 * at the middle and you get whichever the geometry happens to give, which is how you end up
	 * with a flight you cannot walk up.
	 */
	static Vec3 hit(BlockPos target, Direction faceFromNeighbour, boolean upperHalf) {
		BlockPos nb = target.relative(faceFromNeighbour.getOpposite());
		double y = upperHalf ? 0.75 : 0.25;
		double cx = nb.getX() + 0.5, cy = nb.getY() + 0.5, cz = nb.getZ() + 0.5;
		return switch (faceFromNeighbour) {
			case UP -> new Vec3(cx, nb.getY() + 1.0, cz);
			case DOWN -> new Vec3(cx, nb.getY(), cz);
			case NORTH -> new Vec3(cx, nb.getY() + y, nb.getZ());
			case SOUTH -> new Vec3(cx, nb.getY() + y, nb.getZ() + 1.0);
			case WEST -> new Vec3(nb.getX(), nb.getY() + y, cz);
			case EAST -> new Vec3(nb.getX() + 1.0, nb.getY() + y, cz);
		};
	}

	/** Parse `stone_brick_stairs[facing=east,half=top]` into what the aiming needs to know. */
	static Map<String, String> props(String state) {
		Map<String, String> out = new HashMap<>();
		int b = state.indexOf('[');
		if (b < 0 || !state.endsWith("]")) return out;
		for (String part : state.substring(b + 1, state.length() - 1).split(",")) {
			int eq = part.indexOf('=');
			if (eq > 0) out.put(part.substring(0, eq).trim(), part.substring(eq + 1).trim());
		}
		return out;
	}

	// ---------------------------------------------------------------- the pass

	private static final Map<String, Integer> tries = new HashMap<>();
	private static final Set<String> givenUp = new HashSet<>();
	private static final List<Attempt> pending = new ArrayList<>();
	private static long lastPlaceTick;
    private static int pendingSequence;
    private static Object pendingLevel;
	/** Non-null only for a followed build revision. A reset leaves it unresolved on disk. */
    private static String pendingJournal;
	private static int placed, mismatched, failed;
	// Since the loop last asked. THIS IS THE SIGNAL THE LOOP HAS NEVER HAD: a refusal is instant
	// knowledge, where the five-second station clock had to wait and then guess.
	private static int placedSince, refusedSince;

	static void reset() {
		tries.clear();
		givenUp.clear();
		pending.clear();
        lastPlaceTick = Long.MIN_VALUE / 2;
        pendingLevel = null;
        pendingJournal = null;
		placed = mismatched = failed = 0;
		placedSince = refusedSince = 0;
	}

	/** True while this printer is the thing placing blocks, so the loop knows to trust its report. */
	static boolean driving() {
		return ChunkScanClient.printDesign != null;
	}

	/**
	 * What has happened since the last call, and RESETS. Two numbers, because they mean opposite
	 * things: cells that went in are progress, cells that were refused are proof this spot is not
	 * buildable from here and there is nothing to wait for.
	 */
	static int[] drainReport() {
		int[] r = {placedSince, refusedSince};
		placedSince = refusedSince = 0;
		return r;
	}

	static int placed() { return placed; }

	static int mismatched() { return mismatched; }

	static int failed() { return failed; }

	static boolean givenUpOn(BlockPos p) {
		return givenUp.contains(key(p));
	}

	private static String key(BlockPos p) {
		return p.getX() + "," + p.getY() + "," + p.getZ();
	}

	/** Which hotbar slot holds this block, or -1. Only the hotbar: a click uses what is held. */
	static int hotbarSlot(LocalPlayer p, String block) {
		String want = Rules.shortName(block);
		for (int i = 0; i < 9; i++) {
			ItemStack st = p.getInventory().getItem(i);
			if (st.isEmpty() || !(st.getItem() instanceof BlockItem)) continue;
			if (BuiltInRegistries.ITEM.getKey(st.getItem()).getPath().equals(want)) return i;
		}
		return -1;
	}

    static boolean support(BlockState state) {
        String name = BuiltInRegistries.BLOCK.getKey(state.getBlock()).getPath();
        return !state.isAir() && !state.canBeReplaced() && state.blocksMotion()
            && !Storage.isContainer(name) && !name.endsWith("_door") && !name.endsWith("_trapdoor")
            && !name.endsWith("_fence_gate") && !name.endsWith("_button") && !name.equals("lever")
            && !name.endsWith("_bed") && !name.equals("note_block") && !name.equals("jukebox");
    }

    /** A normal inventory slot, never armor or offhand. */
    static int inventorySlot(LocalPlayer p, String state) {
        String item = ActionRecipe.itemFor(state);
        for (int i = 0; i < 36; i++) {
            ItemStack stack = p.getInventory().getItem(i);
            if (!stack.isEmpty() && BuiltInRegistries.ITEM.getKey(stack.getItem()).getPath().equals(item)
				&& (stack.getItem() instanceof BlockItem || (ActionRecipe.waterBucket(state)
					&& stack.getItem() instanceof BucketItem))) return i;
        }
        return -1;
    }

    record Placement(BlockHitResult hit, float yaw, float pitch) {}

    /** Check the real ray and vanilla's placement state before sending an interaction. */
    static Placement placement(Minecraft mc, BlockPos pos, String state, int slot) {
		if (mc.player == null || mc.level == null || slot < 0 || !mc.level.isLoaded(pos)) return null;
        if (!Rules.inLockedProfile(state) || (Rules.serverListIsAuthoritative() && !Rules.isOnServer(state))) return null;
        if (Islands.outside(ScanRunner.schematicsDir(mc), pos.getX(), pos.getZ())) return null;
        LocalPlayer p = mc.player;
        ItemStack stack = p.getInventory().getItem(slot);
		if (ActionRecipe.waterBucket(state) && stack.getItem() instanceof BucketItem) {
			return bucketPlacement(mc, pos);
		}
        if (!(stack.getItem() instanceof BlockItem item)) return null;
		BlockState existing = mc.level.getBlockState(pos);
		if (ActionRecipe.slabIntermediate(existing, state)) return slabUpgrade(mc, pos, state, stack, item);
		if (ActionRecipe.vineIntermediate(existing, state)) return vineUpgrade(mc, pos, state, stack, item);
		if (ActionRecipe.glowLichenIntermediate(existing, state)) return glowLichenUpgrade(mc, pos, state, stack, item);
		if (!existing.isAir()) return null;
        boolean upper = "top".equals(props(state).get("half")) || "top".equals(props(state).get("type"));
        float oldYaw = p.getYRot(), oldPitch = p.getXRot();
        try {
            for (Direction face : faces()) {
                BlockPos nb = pos.relative(face.getOpposite());
                if (!mc.level.isLoaded(nb) || !support(mc.level.getBlockState(nb))) continue;
                var shape = mc.level.getBlockState(nb).getShape(mc.level, nb);
                for (var box : shape.toAabbs()) {
                    Vec3 pt = hit(pos, face, upper);
                    // Actual shape surface: slabs are not full cubes.
                    double x = Math.max(nb.getX()+box.minX+0.001, Math.min(pt.x, nb.getX()+box.maxX-0.001));
                    double y = Math.max(nb.getY()+box.minY+0.001, Math.min(pt.y, nb.getY()+box.maxY-0.001));
                    double z = Math.max(nb.getZ()+box.minZ+0.001, Math.min(pt.z, nb.getZ()+box.maxZ-0.001));
                    pt = switch(face) {
                        case UP -> new Vec3(x, nb.getY()+box.maxY, z);
                        case DOWN -> new Vec3(x, nb.getY()+box.minY, z);
                        case EAST -> new Vec3(nb.getX()+box.maxX, y, z);
                        case WEST -> new Vec3(nb.getX()+box.minX, y, z);
                        case SOUTH -> new Vec3(x, y, nb.getZ()+box.maxZ);
                        case NORTH -> new Vec3(x, y, nb.getZ()+box.minZ);
                    };
                    if (p.getEyePosition().distanceToSqr(pt) > REACH * REACH) continue;
                    Vec3 inside = pt.add(-face.getStepX()*0.001, -face.getStepY()*0.001, -face.getStepZ()*0.001);
                    BlockHitResult ray = mc.level.clip(new ClipContext(p.getEyePosition(), inside,
                        ClipContext.Block.OUTLINE, ClipContext.Fluid.NONE, p));
                    if (ray.getType() != net.minecraft.world.phys.HitResult.Type.BLOCK
                        || !ray.getBlockPos().equals(nb) || ray.getDirection() != face) continue;
                    BlockHitResult hit = new BlockHitResult(pt, face, nb, false);
                    for (float yaw : new float[]{oldYaw, 0, 90, 180, 270}) {
                        for (float pitch : new float[]{oldPitch, 0, -90, 90}) {
                            p.setYRot(yaw); p.setXRot(pitch);
                            BlockPlaceContext context = new BlockPlaceContext(p, InteractionHand.MAIN_HAND, stack, hit);
                            context = item.updatePlacementContext(context);
                            if (context == null || !context.getClickedPos().equals(pos) || !context.canPlace()) continue;
                            BlockState predicted = item.getBlock().getStateForPlacement(context);
							if (predicted != null && (Work.matches(predicted, state) || ActionRecipe.vineProgress(existing, predicted, state)
								|| ActionRecipe.glowLichenProgress(existing, predicted, state)) && predicted.canSurvive(mc.level, pos)
                                && mc.level.isUnobstructed(predicted, pos, net.minecraft.world.phys.shapes.CollisionContext.empty()))
                                return new Placement(hit, yaw, pitch);
                        }
                    }
                }
            }
        } finally { p.setYRot(oldYaw); p.setXRot(oldPitch); }
        return null;
    }

	/** A water bucket uses the same legal support/ray calculation as a block, but is not a BlockItem. */
	private static Placement bucketPlacement(Minecraft mc, BlockPos pos) {
		LocalPlayer p = mc.player;
		if (!mc.level.getBlockState(pos).isAir()) return null;
		for (Direction face : faces()) {
			BlockPos nb = pos.relative(face.getOpposite());
			if (!mc.level.isLoaded(nb) || !support(mc.level.getBlockState(nb))) continue;
			for (var box : mc.level.getBlockState(nb).getShape(mc.level, nb).toAabbs()) {
				Vec3 wanted = hit(pos, face, false);
				double x = Math.max(nb.getX() + box.minX + 0.001, Math.min(wanted.x, nb.getX() + box.maxX - 0.001));
				double y = Math.max(nb.getY() + box.minY + 0.001, Math.min(wanted.y, nb.getY() + box.maxY - 0.001));
				double z = Math.max(nb.getZ() + box.minZ + 0.001, Math.min(wanted.z, nb.getZ() + box.maxZ - 0.001));
				Vec3 point = switch (face) {
					case UP -> new Vec3(x, nb.getY() + box.maxY, z);
					case DOWN -> new Vec3(x, nb.getY() + box.minY, z);
					case EAST -> new Vec3(nb.getX() + box.maxX, y, z);
					case WEST -> new Vec3(nb.getX() + box.minX, y, z);
					case SOUTH -> new Vec3(x, y, nb.getZ() + box.maxZ);
					case NORTH -> new Vec3(x, y, nb.getZ() + box.minZ);
				};
				if (p.getEyePosition().distanceToSqr(point) > REACH * REACH) continue;
				Vec3 inside = point.add(-face.getStepX() * 0.001, -face.getStepY() * 0.001, -face.getStepZ() * 0.001);
				BlockHitResult ray = mc.level.clip(new ClipContext(p.getEyePosition(), inside,
					ClipContext.Block.OUTLINE, ClipContext.Fluid.NONE, p));
				if (ray.getType() == net.minecraft.world.phys.HitResult.Type.BLOCK
					&& ray.getBlockPos().equals(nb) && ray.getDirection() == face)
					return new Placement(new BlockHitResult(point, face, nb, false), p.getYRot(), p.getXRot());
			}
		}
		return null;
	}

	private static Placement slabUpgrade(Minecraft mc, BlockPos pos, String state, ItemStack stack, BlockItem item) {
		LocalPlayer p = mc.player;
		BlockHitResult ray = mc.level.clip(new ClipContext(p.getEyePosition(), Vec3.atCenterOf(pos),
			ClipContext.Block.OUTLINE, ClipContext.Fluid.NONE, p));
		if (ray.getType() != net.minecraft.world.phys.HitResult.Type.BLOCK || !ray.getBlockPos().equals(pos)
			|| p.getEyePosition().distanceToSqr(ray.getLocation()) > REACH * REACH) return null;
		BlockPlaceContext context = new BlockPlaceContext(p, InteractionHand.MAIN_HAND, stack, ray);
		context = item.updatePlacementContext(context);
		if (context == null || !context.getClickedPos().equals(pos) || !context.canPlace()) return null;
		BlockState predicted = item.getBlock().getStateForPlacement(context);
		if (predicted == null || !Work.matches(predicted, state)) return null;
		return new Placement(ray, p.getYRot(), p.getXRot());
	}

	private static Placement vineUpgrade(Minecraft mc, BlockPos pos, String state, ItemStack stack, BlockItem item) {
		LocalPlayer p = mc.player;
		BlockState before = mc.level.getBlockState(pos);
		BlockHitResult ray = mc.level.clip(new ClipContext(p.getEyePosition(), Vec3.atCenterOf(pos),
			ClipContext.Block.OUTLINE, ClipContext.Fluid.NONE, p));
		if (ray.getType() != net.minecraft.world.phys.HitResult.Type.BLOCK || !ray.getBlockPos().equals(pos)
			|| p.getEyePosition().distanceToSqr(ray.getLocation()) > REACH * REACH) return null;
		BlockPlaceContext context = new BlockPlaceContext(p, InteractionHand.MAIN_HAND, stack, ray);
		context = item.updatePlacementContext(context);
		if (context == null || !context.getClickedPos().equals(pos) || !context.canPlace()) return null;
		BlockState predicted = item.getBlock().getStateForPlacement(context);
		if (predicted == null || !ActionRecipe.vineProgress(before, predicted, state)) return null;
		return new Placement(ray, p.getYRot(), p.getXRot());
	}

	private static Placement glowLichenUpgrade(Minecraft mc, BlockPos pos, String state, ItemStack stack, BlockItem item) {
		LocalPlayer p = mc.player;
		BlockState before = mc.level.getBlockState(pos);
		BlockHitResult ray = mc.level.clip(new ClipContext(p.getEyePosition(), Vec3.atCenterOf(pos),
			ClipContext.Block.OUTLINE, ClipContext.Fluid.NONE, p));
		if (ray.getType() != net.minecraft.world.phys.HitResult.Type.BLOCK || !ray.getBlockPos().equals(pos)
			|| p.getEyePosition().distanceToSqr(ray.getLocation()) > REACH * REACH) return null;
		BlockPlaceContext context = new BlockPlaceContext(p, InteractionHand.MAIN_HAND, stack, ray);
		context = item.updatePlacementContext(context);
		if (context == null || !context.getClickedPos().equals(pos) || !context.canPlace()) return null;
		BlockState predicted = item.getBlock().getStateForPlacement(context);
		if (predicted == null || !ActionRecipe.glowLichenProgress(before, predicted, state)) return null;
		return new Placement(ray, p.getYRot(), p.getXRot());
	}

    static Verdict place(Minecraft mc, BlockPos pos, String state) {
        if (busy() || !AutomationControl.enter(ActionGate.Owner.PRINT)) return Verdict.REFUSED;
        if (mc.player == null || mc.level == null || mc.gameMode == null || givenUpOn(pos)) return Verdict.REFUSED;
        if (Screens.container() != null) return Verdict.REFUSED;
        LocalPlayer p = mc.player;
        int slot = inventorySlot(p, state);
        if (slot < 0) return Verdict.NO_ITEM;
        Placement plan = placement(mc, pos, state, slot);
        if (plan == null) return Verdict.NO_FACE;
        if (slot >= 9) {
            // Vanilla SWAP moves a main-inventory stack to the selected hotbar slot.
            mc.gameMode.handleContainerInput(p.inventoryMenu.containerId, slot, p.getInventory().getSelectedSlot(),
                ContainerInput.SWAP, p);
            lastPlaceTick = mc.level.getGameTime();
            return Verdict.NO_ITEM; // wait for the next tick, never click with the old held item
        }
        p.getInventory().setSelectedSlot(slot);
        p.setYRot(plan.yaw()); p.setXRot(plan.pitch());
        p.connection.send(new ServerboundMovePlayerPacket.Rot(plan.yaw(), plan.pitch(), p.onGround(), p.horizontalCollision));
		// Persist before the packet. If the client dies after this point the result is UNKNOWN,
		// which is the only safe state until a later world observation reconciles it.
		ActiveBuild.Snapshot revision = ActiveBuild.current(ScanRunner.schematicsDir(mc), ChunkScanClient.printDesign);
		if (revision != null) {
			try { pendingJournal = BuildJournal.begin(revision.sourceDirectory(), revision.binding(), pos, state); }
			catch (java.io.IOException unavailable) {
				Hud.off();
				return Verdict.REFUSED;
			}
		}
		try {
			mc.gameMode.useItemOn(p, InteractionHand.MAIN_HAND, plan.hit());
			p.swing(InteractionHand.MAIN_HAND);
			pendingSequence = ((PredictionAccess) mc.level).chunkscan$sequence();
			pendingLevel = mc.level;
			pending.add(new Attempt(pos, state, Verdict.STILL_AIR, ""));
			lastPlaceTick = mc.level.getGameTime();
		} catch (RuntimeException uncertain) {
			// A packet may have left before a local failure. The start record intentionally remains.
			Hud.off();
			throw uncertain;
		}
        return Verdict.PLACED;
    }

	/**
	 * Look at every pending cell and decide what actually happened.
	 *
	 * <p>THIS IS THE SIGNAL THE LOOP HAS NEVER HAD. Called a few ticks after the attempts, so the
	 * server has had time to answer; a cell still air is a failure, a cell holding the wrong STATE
	 * is a mismatch and is never counted as built.
	 */
	static List<Attempt> verify(Minecraft mc) {
		List<Attempt> out = new ArrayList<>();
		if (mc.level == null) return out;
        if (pendingLevel != null && pendingLevel != mc.level) { reset(); return out; }
        if (!pending.isEmpty() && !acknowledged(pendingSequence, ((PredictionAccess)mc.level).chunkscan$acknowledged())) {
            if (mc.level.getGameTime() - lastPlaceTick > 100) {
                Hud.off();
                pending.clear();
                if (mc.player != null) mc.player.sendSystemMessage(net.minecraft.network.chat.Component.literal(
                    "[cscan] printer paused: no server placement acknowledgement after 5 seconds"));
            }
            return out;
        }
		for (Attempt a : new ArrayList<>(pending)) {
			BlockState st = mc.level.getBlockState(a.pos());
			if (st.isAir()) {
				int n = tries.merge(key(a.pos()), 1, Integer::sum);
				if (n >= MAX_TRIES) {
					givenUp.add(key(a.pos()));
					failed++;
					refusedSince++;
					out.add(new Attempt(a.pos(), a.want(), Verdict.STILL_AIR, "air"));
				}
				journal(a, Verdict.STILL_AIR, "air");
				continue;                       // one more go before writing it off
			}
			String got = BuiltInRegistries.BLOCK.getKey(st.getBlock()).getPath();
			// `Work.matches` is the SAME comparison `/cscan check` uses, so a cell the printer
			// calls placed and a cell the check calls built can never disagree.
			if (Work.matches(st, a.want())) {
				placed++;
				placedSince++;
				out.add(new Attempt(a.pos(), a.want(), Verdict.PLACED, got));
			} else {
				mismatched++;
				refusedSince++;
				givenUp.add(key(a.pos()));      // placing over it would mean breaking it
				out.add(new Attempt(a.pos(), a.want(), Verdict.MISMATCH, got));
			}
			journal(a, out.getLast().verdict(), got);
		}
		pending.clear();
		pendingJournal = null;
		return out;
	}

	private static void journal(Attempt attempt, Verdict verdict, String observed) {
		if (pendingJournal == null || pendingLevel == null) return;
		ActiveBuild.Snapshot revision = ActiveBuild.current(
			ScanRunner.schematicsDir(Minecraft.getInstance()), ChunkScanClient.printDesign);
		if (revision == null) return;
		try { BuildJournal.finish(revision.sourceDirectory(), revision.binding(), pendingJournal, verdict, observed); }
		catch (java.io.IOException ignored) {
			// The start record is intentionally retained: failed completion is unknown, not success.
			Hud.off();
		}
	}

	static boolean acknowledged(int sequence, int ack) { return ack >= sequence; }

	static boolean busy() {
		return !pending.isEmpty();
	}

	static boolean ready(Minecraft mc) {
		return mc.level != null && mc.level.getGameTime() - lastPlaceTick >= interval;
	}

	static String report() {
		return placed + " placed, " + mismatched + " wrong state, " + failed + " refused";
	}
}
