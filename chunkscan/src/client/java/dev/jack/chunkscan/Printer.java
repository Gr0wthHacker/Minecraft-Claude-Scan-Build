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
	enum Verdict { PLACED, PARTIAL, MISMATCH, STILL_AIR, BLOCKED, NO_ITEM, NO_FACE, OUT_OF_REACH, REFUSED }

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
	/** Allocated once: this is asked per CELL, and a fresh six-element array each time is waste. */
	private static final Direction[] FACES = {Direction.UP, Direction.NORTH, Direction.SOUTH,
		Direction.EAST, Direction.WEST, Direction.DOWN};

	static Direction[] faces() {
		// Down first: a block placed on top of another is the commonest and the least ambiguous,
		// and it is what a player does. Sides before up, because clicking a ceiling is awkward and
		// more likely to be out of reach from a standing spot.
		return FACES;
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
	/**
	 * A state string's properties.
	 *
	 * <p><b>MEMOISED, AND THE RETURNED MAP IS UNMODIFIABLE FOR THAT REASON.</b> This parses a string
	 * and allocates a map, and it sits under `ActionRecipe.order`, `doubleSlab` and the placement
	 * sweep - all of which run per CELL over a design that is half a million cells. A design has a
	 * few hundred distinct states, so parsing each one once is the whole of the cost; sharing the
	 * map is only safe because nobody may now write to it, which the wrapper enforces rather than
	 * trusts.
	 */
	private static final java.util.concurrent.ConcurrentHashMap<String, Map<String, String>> PROPS =
		new java.util.concurrent.ConcurrentHashMap<>();

	static Map<String, String> props(String state) {
		Map<String, String> hit = PROPS.get(state);
		if (hit != null) return hit;
		Map<String, String> out = new HashMap<>();
		int b = state.indexOf('[');
		if (b >= 0 && state.endsWith("]")) {
			for (String part : state.substring(b + 1, state.length() - 1).split(",")) {
				int eq = part.indexOf('=');
				if (eq > 0) out.put(part.substring(0, eq).trim(), part.substring(eq + 1).trim());
			}
		}
		Map<String, String> shared = java.util.Collections.unmodifiableMap(out);
		if (PROPS.size() < 16384) PROPS.put(state, shared);
		return shared;
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
	/** Consecutive placements the server never acknowledged. One is lag; a run is a dead link. */
	private static int ackTimeouts;
	static final int ACK_TIMEOUT_LIMIT = 5;
	static final int INTERVAL_MIN = 2, INTERVAL_MAX = 12;
	// Since the loop last asked. THIS IS THE SIGNAL THE LOOP HAS NEVER HAD: a refusal is instant
	// knowledge, where the five-second station clock had to wait and then guess.
	private static int placedSince, refusedSince;	static void reset() {
		tries.clear();
		givenUp.clear();
		noPlacementUntil.clear();
		everCache.clear();
		everStale.clear();
		pending.clear();
        lastPlaceTick = Long.MIN_VALUE / 2;
        pendingLevel = null;
        pendingJournal = null;
		placed = mismatched = failed = 0;
		placedSince = refusedSince = 0;
		ackTimeouts = 0;
		interval = INTERVAL_MIN;
	}

	/**
	 * Forget every verdict that was about the world AS IT WAS. `everCache` says a cell can never be
	 * placed — true until the wall it needed goes in. `givenUp` says a cell refused twice — true
	 * until the lag that refused it passes. Neither was ever re-asked while a design was followed,
	 * so a cell written off in the first minute stayed written off all night, and the design could
	 * never complete. Called on a slow timer from the loop; the caches refill within their budget.
	 */	static void relax() {
		// THE OLD ANSWERS ARE KEPT AS A FALLBACK, NOT THROWN AWAY. Cleared outright, every cell past
		// the 400-per-recount budget read as placeable again (everPlaceableCached's "assume work"
		// default), so a course of cells the printer had already proved impossible came back as the
		// frontier every thirty seconds: a station chosen on it, nothing placed, the spot abandoned
		// and struck - the hovering over unplaceable groups Jack watched. A stale verdict stands
		// until the budget re-asks it.
		everStale.clear();
		everStale.putAll(everCache);
		everCache.clear();
		givenUp.clear();
		tries.clear();
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
            && !name.endsWith("_bed") && !name.equals("note_block") && !name.equals("jukebox")
            && !toggles(name);
    }

	/**
	 * Blocks a right-click USES rather than places against. The server runs the block's own use()
	 * first, so clicking one with a block in hand cycles a repeater's delay, flips a comparator,
	 * feeds a composter the held block, rings a bell - and places nothing. The cell was then given
	 * up and the toggle was permanent, in the machine room under the tree. Never a placement face.
	 */
	static boolean toggles(String name) {
		return name.equals("repeater") || name.equals("comparator") || name.equals("daylight_detector")
			|| name.equals("composter") || name.equals("bell") || name.endsWith("cake")
			|| name.equals("flower_pot") || name.startsWith("potted_") || name.equals("target")
			|| name.equals("lectern") || name.endsWith("cauldron") || name.equals("dragon_egg")
			|| name.equals("respawn_anchor") || name.equals("beehive") || name.equals("bee_nest")
			|| name.endsWith("candle") || name.endsWith("redstone_ore") || name.equals("tnt")
			|| name.equals("chiseled_bookshelf") || name.equals("decorated_pot") || name.endsWith("sign");
	}

    /** A normal inventory slot, never armor or offhand. */
	/**
	 * A stack that is somebody's STORAGE, not a building block: a shulker box with things in it, or
	 * anything with a name somebody gave it. A design cell of {@code white_shulker_box} must never
	 * be filled with a box full of the player's redstone.
	 */
	static boolean keepsake(ItemStack stack) {
		if (stack.has(net.minecraft.core.component.DataComponents.CUSTOM_NAME)) return true;
		var contents = stack.get(net.minecraft.core.component.DataComponents.CONTAINER);
		return contents != null && contents.nonEmptyItemCopyStream().findAny().isPresent();
	}

    static int inventorySlot(LocalPlayer p, String state, BlockState existing) {
        String item = ActionRecipe.cauldronIntermediate(existing, state) ? ActionRecipe.cauldronBucket(state) : ActionRecipe.itemFor(state);
        for (int i = 0; i < 36; i++) {
            ItemStack stack = p.getInventory().getItem(i);
            if (!stack.isEmpty() && keepsake(stack)) continue;
            if (!stack.isEmpty() && BuiltInRegistries.ITEM.getKey(stack.getItem()).getPath().equals(item)
				&& (stack.getItem() instanceof BlockItem || ((ActionRecipe.waterBucket(state)
					|| ActionRecipe.cauldronIntermediate(existing, state)) && stack.getItem() instanceof BucketItem))) return i;
        }
        return -1;
    }

	/**
	 * Could this cell EVER be placed from somewhere, given the world as it stands?
	 *
	 * <p>The loop asks {@link Work#placeableNow} where to go, and that asks one question: is any of
	 * the six neighbours solid. {@link #placement} - the thing that actually places - asks five more,
	 * and any of them can say no: the item's own {@code getStateForPlacement} has to yield the state
	 * the design wants, the result has to {@code canSurvive} there, the cell has to be unobstructed,
	 * and the block has to be one this profile and this server allow at all.
	 *
	 * <p><b>So the loop was choosing spots by the loose test and the printer was refusing them by the
	 * strict one.</b> A torch whose only solid neighbour is the wrong face, a plant over the wrong
	 * soil, a vine with nothing to cling to: every one of them has a solid neighbour, so every one of
	 * them stayed in the frontier for ever - clustered, flown to, stalled at, abandoned, and picked
	 * again on the next recount. That is <i>"it still seeks out blocks that it cant possibly place
	 * because theres nothing around them"</i>, and it is this repo's own rule about one source
	 * broken in the one place it costs a whole session: two tests, drifting, and the WRONG one
	 * steering.
	 *
	 * <p>This is {@link #placement} with the two things that depend on WHERE YOU STAND removed - the
	 * reach and the eye ray - so it answers about the cell rather than about the moment. Everything
	 * else is the same code path, which is what stops the two drifting again.
	 *
	 * <p>The stack is built from the registry rather than the inventory: whether you are carrying it
	 * is {@code carrying}'s question, and answering it here would call a cell unplaceable for being
	 * out of stock.
	 */
	/**
	 * An item by its registry path.
	 *
	 * <p>Everything else here goes the other way - a state to its key - so there was no forward
	 * lookup to borrow, and the registry has no by-path index. Built once and kept: this is asked
	 * per cell per recount, and walking twelve hundred items twice a second to answer it would be
	 * exactly the per-node cost this file has already paid for twice.
	 */
	private static Map<String, net.minecraft.world.item.Item> byPath;

	static net.minecraft.world.item.Item itemNamed(String path) {
		if (byPath == null) {
			byPath = new HashMap<>();
			for (var it : BuiltInRegistries.ITEM) {
				byPath.putIfAbsent(BuiltInRegistries.ITEM.getKey(it).getPath(), it);
			}
		}
		return byPath.get(path);
	}

	/**
	 * Verdicts already reached, and a budget on fresh ones.
	 *
	 * <p>Even at one evaluation a cell this is asked about every remaining cell every recount, and
	 * the cells it says NO to are by definition the ones that stay in the list for ever - so the
	 * expensive answer is the one paid for again and again. Cached, and bounded: a cell not yet
	 * looked at is treated as placeable, which is the safe direction (a wasted trip beats silently
	 * dropping real work) and converges over a few recounts.
	 */	private static final Map<Long, Boolean> everCache = new HashMap<>();
	/** Verdicts from before the last relax(): the answer while a cell waits for the budget. */
	private static final Map<Long, Boolean> everStale = new HashMap<>();
	/**
	 * Cells whose placement sweep found no angle, and the game tick until which they are not asked
	 * again. The sweep is the expensive half of a tick - yaw by pitch by face for every in-reach
	 * cell that fails - and a cell that had no angle from here a moment ago has none now. Half a
	 * second, because the body moves and the answer with it.
	 */
	private static final Map<Long, Long> noPlacementUntil = new HashMap<>();
	static final int NO_PLACEMENT_TICKS = 10;

	static boolean recentlyUnplaceable(net.minecraft.world.level.Level level, BlockPos pos) {
		Long until = noPlacementUntil.get(pos.asLong());
		return until != null && level.getGameTime() < until;
	}

	static void noteNoPlacement(net.minecraft.world.level.Level level, BlockPos pos) {
		if (noPlacementUntil.size() > 4096) noPlacementUntil.clear();
		noPlacementUntil.put(pos.asLong(), level.getGameTime() + NO_PLACEMENT_TICKS);
	}
	private static int everBudget;
	static final int EVER_PER_RECOUNT = 400;

	/** Called once per recount: a new look at the world is a new budget. */
	static void refreshPlaceability() {
		everBudget = EVER_PER_RECOUNT;
	}

	/** The world changed under us in a way no per-cell answer survives. */
	static void forgetPlaceability() {
		everCache.clear();
		everStale.clear();
	}

	/**
	 * A block just landed here, so its NEIGHBOURS may now be placeable.
	 *
	 * <p>`everCache` is keyed on the position of the cell being judged, and the judgement is about
	 * the world AROUND that cell - so placing a block never invalidated the verdicts that placing
	 * it had just changed. The wall a lantern was waiting for went in and the lantern stayed
	 * written off until the thirty-second `relax`, which is thirty seconds of a station standing
	 * over work it had already unblocked. Six cells, on the one event that can change the answer.
	 *
	 * <p>`forgetPlaceability` is the blunt version and had no callers at all; it stays as the way
	 * to drop everything when a design changes.
	 */
	static void forgetNear(BlockPos pos) {
		everCache.remove(pos.asLong());
		everStale.remove(pos.asLong());
		for (Direction d : Direction.values()) {
			long k = pos.relative(d).asLong();
			everCache.remove(k);
			everStale.remove(k);
			noPlacementUntil.remove(k);
		}
	}

	static boolean everPlaceableCached(Minecraft mc, BlockPos pos, String state) {
		Long key = pos.asLong();
		Boolean seen = everCache.get(key);
		if (seen != null) return seen;
		if (everBudget <= 0) return everStale.getOrDefault(key, true);   // not re-asked yet: the last answer, else assume work
		everBudget--;
		boolean ok = everPlaceable(mc, pos, state);
		everCache.put(key, ok);
		return ok;
	}

	/**
	 * Would placing here take the player's last way out?
	 *
	 * <p><b>Jack: <i>"its also still building completely around itself and getting fully stuck"</i>,
	 * and then <i>"consistently it will box itself in".</b></i> Every gate here was about the BLOCK -
	 * is it legal, supported, affordable, on the plot, inside the fence - and none of them was about
	 * the person holding the item. A station chosen inside its own work builds the last wall of a box
	 * around itself, and then nothing can reach anything.
	 *
	 * <p><b>AND THE FIRST VERSION ONLY REFUSED THE LID.</b> It asked for four walls AND a blocked
	 * ceiling, so a body left standing in a one-wide open-top shaft was allowed - and the next course
	 * of the same design then built that shaft taller with the body still in it. The rule is not
	 * "do not seal yourself in", it is <b>keep a way out</b>: after this block there must still be a
	 * side the body can walk or step through. A shaft you can only fly up is not a place a printer
	 * can work from, and the four-walls-plus-lid test never sees the commonest box of all - a ring at
	 * HEAD height, which {@link Burial#canLeave} is what finally measures.
	 *
	 * <p>The cell stays in `todo`: this is not a refusal for ever, it is a refusal FROM HERE. The
	 * station moves on its own clock and the block goes in from outside, which is how a person
	 * would have built it. That is why it lives in `placement` rather than in `everPlaceable` -
	 * a false NO cached against the cell would write the work off for good.
	 */
	static boolean wouldBoxIn(Minecraft mc, BlockPos pos) {
		if (mc.player == null || mc.level == null) return false;
		BlockPos feet = mc.player.blockPosition();
		// Only a cell touching the body's own column, or the one over a neighbour's head, can close
		// it in; everything else is somebody else's wall and none of this check's business. The
		// second course up matters because it is what decides whether a step out is climbable.
		int dx = Math.abs(pos.getX() - feet.getX()), dz = Math.abs(pos.getZ() - feet.getZ());
		int dy = pos.getY() - feet.getY();
		if (dx + dz > 1 || dy < 0 || dy > 2) return false;
		Burial.Solid world = Burial.of(mc.level);
		Burial.Solid after = (x, y, z) ->
			(x == pos.getX() && y == pos.getY() && z == pos.getZ()) || world.at(x, y, z);
		return Burial.exits(after, feet) == 0;
	}

	static boolean everPlaceable(Minecraft mc, BlockPos pos, String state) {
		if (mc.player == null || mc.level == null || !mc.level.isLoaded(pos)) return true;
		if (!Rules.inLockedProfile(state)) return false;
		if (Rules.serverListIsAuthoritative() && !Rules.isOnServer(state)) return false;
		// A filled cauldron deliberately has an empty-cauldron intermediate. Predicting stage one
		// against the FINAL state would cache every such cell as impossible before its dedicated
		// live-state executor can place the cauldron and use the bucket.
		if (ActionRecipe.cauldronFill(state)) return true;
		var stackItem = itemNamed(ActionRecipe.itemFor(state));
		// A bucket, a vine upgrade, anything that is not a plain BlockItem: not this check's
		// business. Say yes and let the placement path answer for it - a false NO here writes work
		// off for good, which is much worse than a wasted trip.
		if (!(stackItem instanceof BlockItem item2)) return true;
		BlockState existing = mc.level.getBlockState(pos);
		if (!existing.isAir()) return true;              // an upgrade path owns this cell
		ItemStack stack = new ItemStack(item2);
		Map<String, String> want = props(state);
		boolean upper = "top".equals(want.get("half")) || "top".equals(want.get("type"));
		// ---- AND DO NOT SWEEP AN ORIENTATION A BLOCK DOES NOT HAVE.
		//
		// A sign sweeps sixteen yaws; everything else swept five yaws by four pitches by six faces,
		// which is a hundred and twenty getStateForPlacement calls PER CELL. Run over the whole
		// frontier every recount that is hundreds of thousands of block-state computations on the
		// client thread twice a second - the client stutters, the approach never completes, and it
		// reads as the loop freezing in front of a chest two blocks away. It was my own doing.
		//
		// Most of this park is stone brick, moss and wool: blocks with no directional property at
		// all, whose placement cannot depend on where the player is looking. One evaluation answers
		// for them.
		float[] sweep = ActionRecipe.yawSweep(state);
		boolean directional = sweep != null || want.containsKey("facing") || want.containsKey("axis")
			|| want.containsKey("rotation") || want.containsKey("half") || want.containsKey("type")
			|| want.containsKey("face") || want.containsKey("hinge") || want.containsKey("attachment");
		float[] yaws = sweep != null ? sweep : directional ? new float[]{0, 90, 180, 270} : new float[]{0};
		// ---- AND PITCH ONLY WHERE IT CAN CHANGE THE ANSWER.
		//
		// Where the player is LOOKING vertically decides a facing of up or down, and which of
		// floor/wall/ceiling a button or lever takes. It decides nothing about a stair, a slab or
		// a wall: a stair's `half` and a slab's `type` come from WHERE IN THE FACE the click lands,
		// which `upper` already sets on the hit vector. Swept anyway it tripled the cost of the
		// most expensive question the loop asks, on the blocks this park is mostly made of.
		boolean vertical = "up".equals(want.get("facing")) || "down".equals(want.get("facing"))
			|| want.containsKey("face") || want.containsKey("vertical_direction");
		float[] pitches = vertical ? new float[]{0, -90, 90} : new float[]{0};
		LocalPlayer p = mc.player;
		float oldYaw = p.getYRot(), oldPitch = p.getXRot();
		try {
			for (Direction face : faces()) {
				BlockPos nb = pos.relative(face.getOpposite());
				if (!mc.level.isLoaded(nb) || !support(mc.level.getBlockState(nb))) continue;
				BlockHitResult hit = new BlockHitResult(hit(pos, face, upper), face, nb, false);
				for (float yaw : yaws) {
					for (float pitch : pitches) {
						p.setYRot(yaw); p.setXRot(pitch);
						BlockPlaceContext ctx = new BlockPlaceContext(p, InteractionHand.MAIN_HAND, stack, hit);
						ctx = item2.updatePlacementContext(ctx);
						if (ctx == null || !ctx.getClickedPos().equals(pos) || !ctx.canPlace()) continue;
						BlockState predicted = item2.getBlock().getStateForPlacement(ctx);
						if (predicted != null && Work.matches(predicted, state)
							&& predicted.canSurvive(mc.level, pos)
							&& mc.level.isUnobstructed(predicted, pos,
								net.minecraft.world.phys.shapes.CollisionContext.empty())) return true;
					}
				}
			}
		} finally { p.setYRot(oldYaw); p.setXRot(oldPitch); }
		return false;
	}

    record Placement(BlockHitResult hit, float yaw, float pitch) {}

    /** Check the real ray and vanilla's placement state before sending an interaction. */
	static Placement placement(Minecraft mc, BlockPos pos, String state, int slot) {
		if (mc.player == null || mc.level == null || slot < 0 || !mc.level.isLoaded(pos)) return null;
        if (!Rules.inLockedProfile(state) || (Rules.serverListIsAuthoritative() && !Rules.isOnServer(state))) return null;
        if (Islands.outside(ScanRunner.schematicsDir(mc), pos.getX(), pos.getZ())) return null;
        if (wouldBoxIn(mc, pos)) return null;            // never brick yourself in - see below
        if (!Bounds.contains(pos)) return null;           // the fence, at the one place every caller passes
        LocalPlayer p = mc.player;
        ItemStack stack = p.getInventory().getItem(slot);
		if (ActionRecipe.waterBucket(state) && stack.getItem() instanceof BucketItem) {
			return bucketPlacement(mc, pos);
		}
		if (ActionRecipe.cauldronIntermediate(mc.level.getBlockState(pos), state) && stack.getItem() instanceof BucketItem) {
			BlockHitResult ray = mc.level.clip(new ClipContext(mc.player.getEyePosition(), Vec3.atCenterOf(pos),
				ClipContext.Block.OUTLINE, ClipContext.Fluid.NONE, mc.player));
			return ray.getType() == net.minecraft.world.phys.HitResult.Type.BLOCK && ray.getBlockPos().equals(pos)
				&& mc.player.getEyePosition().distanceToSqr(ray.getLocation()) <= REACH * REACH
				? new Placement(ray, mc.player.getYRot(), mc.player.getXRot()) : null;
		}
        if (!(stack.getItem() instanceof BlockItem item)) return null;
		BlockState existing = mc.level.getBlockState(pos);
		if (ActionRecipe.slabIntermediate(existing, state)) return slabUpgrade(mc, pos, state, stack, item);
		if (ActionRecipe.vineIntermediate(existing, state)) return vineUpgrade(mc, pos, state, stack, item);
		if (ActionRecipe.glowLichenIntermediate(existing, state)) return glowLichenUpgrade(mc, pos, state, stack, item);
		// A REPLACEABLE BLOCK IS PLACED INTO, not refused. The frontier put a cell holding grass, a
		// fern or a snow layer into todo (Work.isReplaceable) and this refused it, so the cell was
		// "doable" for ever, nothing was placed, and no refusal was ever reported: a silent
		// station stall. Vanilla's own BlockPlaceContext replaces a replaceable clicked-through
		// block, so the prediction agrees with the server now.
		if (!existing.isAir() && !existing.canBeReplaced()) return null;
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
                    float[] sweep = ActionRecipe.yawSweep(state);
                    for (float yaw : sweep != null ? sweep : new float[]{oldYaw, 0, 90, 180, 270}) {
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
	/**
	 * Water only goes where it cannot go anywhere else: every horizontal neighbour and the cell
	 * below must already be solid in the WORLD, or already water. A source poured before its basin
	 * exists runs across the design and turns every neighbouring cell into a deviation nothing can
	 * place into. The world, not the design — a design cell that is not built yet holds nothing.
	 */
	/**
	 * The design's own water cells. A pool two cells wide could never be placed: each cell's
	 * neighbour was the other, still air, and `contained` refused both. A neighbour the design
	 * itself will fill with water is not a leak - the source spreads into it, and its own source
	 * follows. The pool's RIM still has to be solid, which is what `fluids.escapes` verified at
	 * generation.
	 */
	private static java.util.Set<Long> designWater = java.util.Set.of();

	static void setDesignWater(java.util.List<Work.Cell> cells) {
		java.util.Set<Long> out = new java.util.HashSet<>();
		for (Work.Cell c : cells) {
			if (ActionRecipe.waterBucket(c.block())) out.add(c.pos().asLong());
		}
		designWater = out;
	}

	static boolean contained(net.minecraft.world.level.Level level, BlockPos pos) {
		for (Direction d : new Direction[] {Direction.NORTH, Direction.SOUTH, Direction.EAST,
			Direction.WEST, Direction.DOWN}) {
			BlockPos nb = pos.relative(d);
			if (!level.isLoaded(nb)) return false;
			BlockState st = level.getBlockState(nb);
			if (st.blocksMotion()) continue;
			if (st.getFluidState().isSource()) continue;
			if (designWater.contains(nb.asLong())) continue;    // the pool's own next cell
			return false;
		}
		return true;
	}

	private static Placement bucketPlacement(Minecraft mc, BlockPos pos) {
		LocalPlayer p = mc.player;
		BlockState here = mc.level.getBlockState(pos);
		// FLOWING WATER IS NOT A BLOCK IN THE WAY. The first source of a pool flows into the pool's
		// other cells before their own sources go in; refusing "not air" there deadlocked every
		// pool wider than one cell after its first bucket.
		if (!here.isAir() && !(here.getFluidState().is(net.minecraft.world.level.material.Fluids.FLOWING_WATER)
			&& !here.getFluidState().isSource())) return null;
		if (!contained(mc.level, pos)) return null;
		for (Direction face : faces()) {
			BlockPos nb = pos.relative(face.getOpposite());
			if (!mc.level.isLoaded(nb) || !support(mc.level.getBlockState(nb))) continue;
			// A BUCKET USED ON A WATERLOGGABLE BLOCK WATERLOGS THAT BLOCK - a wall, a slab, a stair,
			// a pane - and a waterlogged kerb is a source flowing out of the pool it was meant to
			// hold. The target stays air, the cell is given up, and the flood is real.
			if (mc.level.getBlockState(nb).getBlock() instanceof net.minecraft.world.level.block.SimpleWaterloggedBlock) continue;
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
					&& ray.getBlockPos().equals(nb) && ray.getDirection() == face) {
					// A bucket is USED, not used-on: BucketItem overrides only use(), which casts
					// its own ray from the player's look. So the look must be set to the point the
					// ray above found, and the placement records the angles that put it there.
					Vec3 eye = p.getEyePosition();
					Vec3 dir = point.subtract(eye).normalize();
					float yaw = (float) Math.toDegrees(Math.atan2(-dir.x, dir.z));
					float pitch = (float) Math.toDegrees(-Math.asin(dir.y));
					return new Placement(new BlockHitResult(point, face, nb, false), yaw, pitch);
				}
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

    /** A hotbar slot a swap may take: empty first, then a plain block; never a tool or a keepsake. */
	static int swapSlot(LocalPlayer p) {
		var inv = p.getInventory();
		for (int i = 0; i < 9; i++) if (inv.getItem(i).isEmpty()) return i;
		for (int i = 0; i < 9; i++) {
			ItemStack st = inv.getItem(i);
			if (st.getItem() instanceof BlockItem && !keepsake(st)) return i;
		}
		return inv.getSelectedSlot();
	}

	/** The build journal is what makes a placement accountable; without it the loop STOPS, and says so. */
	private static void journalFailed(Minecraft mc, Exception why) {
		if (mc != null && mc.player != null) mc.player.sendSystemMessage(net.minecraft.network.chat.Component.literal(
			"[cscan] printer: the build journal cannot be written (" + why + ") — stopping"));
		Hud.stopForSafety(mc);
	}

    static Verdict place(Minecraft mc, BlockPos pos, String state) {
        if (busy() || !AutomationControl.enter(ActionGate.Owner.PRINT)) return Verdict.REFUSED;
        if (mc.player == null || mc.level == null || mc.gameMode == null || givenUpOn(pos)) return Verdict.REFUSED;
        if (Screens.container() != null) return Verdict.REFUSED;
        LocalPlayer p = mc.player;
        int slot = inventorySlot(p, state, mc.level.getBlockState(pos));
        if (slot < 0) return Verdict.NO_ITEM;
        Placement plan = placement(mc, pos, state, slot);
        if (plan == null) return Verdict.NO_FACE;
        if (slot >= 9) {
			// Vanilla SWAP moves a main-inventory stack to a hotbar slot - and NOT the selected one
			// blindly: after a dig the selected slot is the pickaxe, and swapping it into the pack
			// left every later dig bare-handed. Take an empty hotbar slot, else one holding a plain
			// block, and select it first so the click lands where the stack goes.
			int dest = swapSlot(p);
			p.getInventory().setSelectedSlot(dest);
			mc.gameMode.handleContainerInput(p.inventoryMenu.containerId, slot, dest, ContainerInput.SWAP, p);
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
				journalFailed(mc, unavailable);
				return Verdict.REFUSED;
			}
		}
		try {
			if (ActionRecipe.waterBucket(state) && p.getInventory().getItem(slot).getItem() instanceof BucketItem) {
				mc.gameMode.useItem(p, InteractionHand.MAIN_HAND);
			} else {
				mc.gameMode.useItemOn(p, InteractionHand.MAIN_HAND, plan.hit());
			}
			p.swing(InteractionHand.MAIN_HAND);
			pendingSequence = ((PredictionAccess) mc.level).chunkscan$sequence();
			pendingLevel = mc.level;
			pending.add(new Attempt(pos, state, Verdict.STILL_AIR, ""));
			lastPlaceTick = mc.level.getGameTime();
		} catch (RuntimeException uncertain) {
			// A packet may have left before a local failure. The start record intentionally remains.
			journalFailed(mc, uncertain);
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
                // ONE MISSING ACK IS LAG, NOT A VERDICT. It used to end the whole follow session,
                // which turned every five-second server hitch into a night of nothing. The
                // attempt counts as a refusal of that cell and the pace backs off; only a RUN of
                // them says the link is dead.
                for (Attempt a : pending) journal(a, Verdict.STILL_AIR, "no ack");
                pending.clear();
                pendingJournal = null;
                interval = Math.min(INTERVAL_MAX, interval * 2);
                if (++ackTimeouts >= ACK_TIMEOUT_LIMIT) {
                    ackTimeouts = 0;
                    if (mc.player != null) mc.player.sendSystemMessage(net.minecraft.network.chat.Component.literal(
                        "[cscan] printer: " + ACK_TIMEOUT_LIMIT + " placements in a row got no server"
                        + " acknowledgement — stopping until the server answers"));
                    Hud.stopForSafety(mc);
                } else if (mc.player != null && ackTimeouts == 1) {
                    mc.player.sendSystemMessage(net.minecraft.network.chat.Component.literal(
                        "[cscan] printer: no placement acknowledgement in 5s — slowing down"));
                }
            }
            return out;
        }
        ackTimeouts = 0;
		for (Attempt a : new ArrayList<>(pending)) {
			BlockState st = mc.level.getBlockState(a.pos());
			if (st.isAir()) {
				int n = tries.merge(key(a.pos()), 1, Integer::sum);
				interval = Math.min(INTERVAL_MAX, interval + 1);   // the server is saying no: ease off
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
				forgetNear(a.pos());        // the neighbours it just gave a face to
				
				interval = INTERVAL_MIN;                            // it is taking them: full pace
				out.add(new Attempt(a.pos(), a.want(), Verdict.PLACED, got));
			} else if (ActionRecipe.slabIntermediate(st, a.want()) || ActionRecipe.cauldronIntermediate(st, a.want())
				|| ActionRecipe.vineIntermediate(st, a.want())
				|| ActionRecipe.glowLichenIntermediate(st, a.want())) {
				// HALF WAY IS NOT WRONG. A double slab is two clicks and a many-faced vine is one per
				// face; placement() builds them that way on purpose, and this then called the first
				// click a MISMATCH, gave the cell up for thirty seconds and told the station to move.
				placedSince++;                                      // progress, so the station stays
				interval = INTERVAL_MIN;
				out.add(new Attempt(a.pos(), a.want(), Verdict.PARTIAL, got));
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
			journalFailed(Minecraft.getInstance(), ignored);
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
