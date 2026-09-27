package dev.jack.chunkscan;

import net.minecraft.client.Minecraft;
import net.minecraft.client.player.LocalPlayer;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.network.chat.Component;
import net.minecraft.world.inventory.ContainerInput;
import net.minecraft.world.item.ItemStack;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;

/**
 * Finds actual quartz in loaded terrain and cuts supported corridors toward it on foot.
 * Search is incremental, bounded by the authorized mining area and 4096 corridor cells,
 * and currently stays at the starting tunnel height. Unsafe or stalled deposits are skipped.
 * No target means stop, never speculative tunneling. Stash and emergency handling remain local
 * to the session; no mining coordinates survive a relog.
 */
final class Miner {

	/** What we came for. */
	static final String ORE = "nether_quartz_ore";

	/** What a corridor is cut through, and what plugs a lava face. */
	static final String PLUG = "netherrack";

	/** Corridor cells checked for lava before any of them is committed to. */
	static final int LOOKAHEAD = 4;

	/** How far from the body to look for ore the corridor has exposed. */
	static final int HARVEST_RADIUS = 5;

	/** Slots kept free so a full pack still has room for what the next swing drops. */
	static final int RESERVE_SLOTS = 3;

	/** Stacks of {@link #PLUG} held back from the stash, for plugging and bridging. */
	static final int PLUG_KEEP = 64;

	/** Below this many uses left, a pickaxe is not worth starting another block with. */
	static final int PICK_RESERVE = 16;

	/** Health at which the trip is over. Ten is five hearts: enough to survive the walk out. */
	static final float DANGER_HEALTH = 10.0f;

	/**
	 * ...and the health below which being ON FIRE is also a reason to go.
	 *
	 * <p>Burning alone is too twitchy to escape on. In the Nether you catch light off a stray flame
	 * and it costs a heart or two; a trip that ends every time that happens ends in the first
	 * minute. It is a danger when it is burning you DOWN, which is what this pairs it with.
	 */
	static final float BURNING_HEALTH = 14.0f;

	/** How far the escape command has to move us before we believe it ran. Rally's number. */
	static final double MOVED_ENOUGH = 8.0;

	/** Ticks to let the world arrive after the escape before anything is decided. Rally's number. */
	static final int LANDING_TICKS = 120;

	/** ...after which the escape command is not sent again this session. Two proofs, not one. */
	static final int DEAD_ESCAPE_LIMIT = 2;

	/** Ticks between re-planning. The swing itself continues every tick; only the THINKING waits. */
	static final int STEP_TICKS = 4;

	/** Consecutive turns with nothing dug between them, after which the box is finished. */
	static final int TURN_LIMIT = 4;

	/** How near the stand the body has to be before the plan may move past it. */
	static final double ARRIVE = 2.0;

	/** Ticks between two attempts to move a pickaxe out of the pack. A SWAP is not synchronous. */
	static final int SWAP_COOLDOWN = 20;

	/** Ticks a wall-in may spend before it reports what it managed and stops. */
	static final int WALL_TRIES = 80;

	/**
	 * Nothing broken and no ground gained for this long, and this face is not working.
	 *
	 * <p>The stash trip has a clock and the escape has one; the DIGGING had none at all. A body that
	 * cannot reach its own stand, or a face the digger refuses for a reason that is neither lava nor
	 * the boundary — a protected block, a tool that will not break it — is a miner standing still
	 * with a full plan and a healthy-looking state, which is this project's signature failure.
	 */
	static final long MINE_STALL_MS = 45_000;

	/** Ticks any one leg of a stash trip may take before it is not going to happen. */
	static final long STASH_LEG_MS = 60_000;

	/** Attempts to open the stash from a spot we have already walked to. */
	static final int OPEN_TRIES = 40;

	/** Bridging attempts over one drop before the drop is treated as a wall. */
	static final int BRIDGE_TRIES = 3;

	/** Deposit passes that move nothing, after which the chest is full. */
	static final int STASH_FAIL_LIMIT = 5;

	private Miner() {}

	// ---------------------------------------------------------------- state

	private static boolean on;
	private static String dimension = "";
	private static BlockPos origin, areaMin, areaMax, stash;
	private static Direction heading;
	private static int depth = 1;
	private static int turns;
	private static int bridgeTries;
	private static int mined, trips;
	private static long nextPlan;
	private static List<BlockPos> plan = List.of();
	private static String lastWord = "";

	private static String escapeCommand = "";
	private enum Escape { NO, TELEPORT, WALLING }
	private static Escape escapePhase = Escape.NO;
	private static int escapeLanding;
	private static BlockPos escapeFrom;
	private static int deadEscape;
	private static List<BlockPos> wallCells = List.of();
	private static int wallTries;
	private static long nextSwap;
	/** The heading the current run of turns started from - see turnAway. */
	private static Direction turnBase;
	/** When the current leg of a stash trip began, so a leg that cannot finish says so. */
	private static long stashLegAt;
	/** When this face last produced anything - a block broken, or a step forward. */
	private static long progressAt;
	private static int openTries;

	private enum Stash { NO, GOING, OPENING, PUTTING, RETURNING }
	private static Stash stashing = Stash.NO;
	private static int stashFails;
	private static long nextPut;

	static boolean running() {
		return on;
	}


	// ---------------------------------------------------------------- the decisions (pure)

	/** The two cells of the corridor face at this depth: what a body walks through. */
	static List<BlockPos> face(BlockPos origin, Direction heading, int depth) {
		BlockPos foot = origin.relative(heading, depth);
		return List.of(foot, foot.above());
	}

	/** Where the body stands to cut {@link #face}: one step behind it, which is always in reach. */
	static BlockPos standFor(BlockPos origin, Direction heading, int depth) {
		return origin.relative(heading, depth - 1);
	}

	/** Every cell of the corridor from here to the lookahead — what the lava scan is run over. */
	static List<BlockPos> segment(BlockPos origin, Direction heading, int depth, int ahead) {
		List<BlockPos> out = new ArrayList<>();
		for (int d = depth; d < depth + ahead; d++) out.addAll(face(origin, heading, d));
		return out;
	}

	/**
	 * Is the pack full enough to be worth a trip?
	 *
	 * <p>A RESERVE rather than zero, because the swing that fills the last slot still drops
	 * something, and an ore broken with nowhere to put it is an ore left on the floor of a corridor
	 * nobody comes back to.
	 */
	static boolean full(int emptySlots, int reserve) {
		return emptySlots <= reserve;
	}

	/**
	 * Does this stay in the pack when the rest goes in the chest?
	 *
	 * <p>A KEEP list rather than a deposit list, and that is the load-bearing choice: a deposit list
	 * silently leaves behind anything nobody thought of, which over a long run is a pack full of
	 * gold nuggets and a miner that thinks it is full. Everything goes in except the things the job
	 * itself needs.
	 *
	 * @param plugHeld how much {@link #PLUG} is already spoken for by earlier slots this pass
	 */
	static boolean keep(String item, boolean damageable, boolean edible, int count, int plugHeld) {
		if (damageable) return true;                       // the pickaxe, and anything else with a bar
		// Food is yours and not the miner's to spend. NOTHING HERE EATS - see the class note; the
		// health gate escapes rather than heals, so a long run ends on health eventually.
		if (edible) return true;
		if (item.endsWith("_bucket") || item.equals("bucket")) return true;
		if (item.contains("shulker_box")) return true;     // a box is storage, not cargo
		if (item.equals(PLUG)) return plugHeld < PLUG_KEEP; // a stack to plug and bridge with
		return false;
	}

	/**
	 * Which way to turn when the corridor ahead is refused.
	 *
	 * <p>Left, then right, then back the way we came — and back is LAST because it retraces a
	 * corridor that is already cut and already stripped. Never a random heading: a branch tunnel
	 * that wanders is one you cannot walk out of.
	 */
	static Direction turn(Direction heading, int attempt) {
		return switch (attempt % 3) {
			case 0 -> heading.getClockWise();
			case 1 -> heading.getCounterClockWise();
			default -> heading.getOpposite();
		};
	}

	/** Did the escape actually move us? A command that silently does nothing is a death. */
	static boolean moved(BlockPos before, BlockPos after) {
		return before == null || after == null
			|| Math.sqrt(after.distSqr(before)) >= MOVED_ENOUGH;
	}

	// ---------------------------------------------------------------- start / stop

	/**
	 * Begin. Every refusal here is a sentence you can act on rather than a job that sits still.
	 *
	 * @param radius half-width of the box this may work in, in X and Z
	 */
	static String start(Minecraft mc, int radius) {
		if (mc.level == null || mc.player == null) return "no world";
		if (Hud.following()) {
			return "a build is running (/cscan follow off first) — one job drives the arrow at a time";
		}
		LocalPlayer p = mc.player;
		BlockPos here = p.blockPosition();

		BlockPos chest = nearestContainer(mc, here);
		if (chest == null) {
			return "no chest within " + STASH_SEARCH + " blocks. Put one where you are standing —"
				+ " it is where the quartz goes, and the miner walks back to it when the pack is full.";
		}

		on = true;
        deposit = null;
        oreSearch = null;
        rejectedOre.clear();
		dimension = mc.level.dimension().identifier().toString();
		origin = here;
		heading = p.getDirection();
		depth = 1;
		turns = 0;
		mined = 0;
		trips = 0;
		plan = List.of();
		stash = chest;
		stashing = Stash.NO;
		stashFails = 0;
		escapePhase = Escape.NO;
		wallCells = List.of();
		turnBase = null;
		nextSwap = 0;
		openTries = 0;
		deadEscape = 0;
		escapeFrom = null;
		nextPlan = 0;
		progressAt = System.currentTimeMillis();
		lastWord = "";
		if (escapeCommand.isBlank()) escapeCommand = Rally.home();
		areaMin = new BlockPos(here.getX() - radius, here.getY() - AREA_DOWN, here.getZ() - radius);
		areaMax = new BlockPos(here.getX() + radius, here.getY() + AREA_UP, here.getZ() + radius);
		Digger.reset();
		Digger.authorize(areaMin, areaMax, dimension);

		String note = "mining " + heading.getName() + " from " + Wand.fmt(here)
			+ ", inside " + radius + " blocks, stash at " + Wand.fmt(chest)
			+ ". Escape: /" + escapeCommand + ".";
		Autopilot.set(false);
		note += " Walking only; flight is disabled for the mining trip.";
		return note;
	}

	/** Half-heights of the working box around the starting course. */
	static final int AREA_UP = 6;
	static final int AREA_DOWN = 6;
	/** How far from the start a stash chest may be and still be the stash. */
	static final int STASH_SEARCH = 12;

	static String stop(Minecraft mc) {
		boolean was = on;
		on = false;
		escapePhase = Escape.NO;
		wallCells = List.of();
		stashing = Stash.NO;
		plan = List.of();
		Digger.pause(mc);
		Digger.clearAuthorization();
		Hud.stopGuiding();
		return was ? report() : "the miner was not running";
	}

	static String report() {
		return mined + " ore broken, " + trips + " trip" + (trips == 1 ? "" : "s")
			+ " to the stash" + (lastWord.isBlank() ? "" : " — " + lastWord);
	}

	static String status() {
		if (!on) return "the miner is off. /cscan mine <radius> starts it where you stand.";
		return (deposit == null ? "searching for quartz" : "quartz at " + Wand.fmt(deposit.ore())) + ", " + report()
			+ (stashing != Stash.NO ? " [stashing: " + stashing + "]" : "")
			+ (escapePhase != Escape.NO ? " [" + escapePhase + "]" : "");
	}

	/** Stop, say why, and leave the sentence where the report can find it. */
	private static String halt(Minecraft mc, String why) {
		lastWord = why;
		stop(mc);
		return why;
	}

	// ---------------------------------------------------------------- the tick

	static String tick(Minecraft mc) {
		if (!on || mc.level == null || mc.player == null || mc.gameMode == null) return null;
		LocalPlayer p = mc.player;

		// A WORLD THAT IS NOT THE ONE WE STARTED IN IS A WORLD THESE COORDINATES MEAN NOTHING IN.
		// Checked before anything, including the danger gate: a box, a heading and a stash position
		// carried through a portal address somebody else's build.
		if (!mc.level.dimension().identifier().toString().equals(dimension)) {
			// ...unless we ASKED to be somewhere else, in which case a new world is the proof the
			// escape worked. Judged here rather than in escapeTick because this check runs first, and
			// without it a successful teleport out of the Nether reported as an unexplained dimension
			// change and never counted as the escape working.
			if (escapePhase == Escape.TELEPORT) {
				escapePhase = Escape.NO;
				return halt(mc, "out — /" + escapeCommand() + " moved us to another dimension. " + report());
			}
			return halt(mc, "the dimension changed — the miner stopped rather than digging at the"
				+ " same numbers somewhere else");
		}

		if (escapePhase != Escape.NO) return escapeTick(mc, p);

		String danger = danger(mc, p);
		if (danger != null) return beginEscape(mc, p, danger);

		// The swing continues EVERY tick — startDestroyBlock is only the beginning of a break, and
		// throttling this would leave the pickaxe hanging in the air. Only the THINKING waits.
		Digger.authorize(areaMin, areaMax, dimension);
		long now = mc.level.getGameTime();

		if (stashing != Stash.NO) return stashTick(mc, p);

		if (now >= nextPlan) {
			nextPlan = now + STEP_TICKS;
			String said = replan(mc, p);
			if (said != null) return said;
		}
		int before = Digger.broke();
		String said = Digger.tick(mc, plan);
		if (Digger.broke() > before) {
			mined += Digger.broke() - before;
			turns = 0;                                     // progress: the box is not finished
			progressAt = System.currentTimeMillis();
		}
		return said;
	}

	/** Rebuild the work list and decide where to stand. Null unless there is something to say. */
	private static String replan(Minecraft mc, LocalPlayer p) {
		if (full(emptySlots(p), RESERVE_SLOTS)) {
			// LET GO OF THE BLOCK FIRST. Nothing ticks the digger while the stash runs, so a target
			// left set stays set - and AutomationControl.blocksMovement pins the body while the digger
			// is busy, which is right for a swing and fatal here: the miner would have stood at the
			// face with a full pack, unable to walk to the chest, and nothing would have said why.
			Digger.pause(mc);
			step(Stash.GOING);
			stashFails = 0;
			return "pack full — " + mined + " ore so far, taking it to the stash";
		}
		String tool = ensureTool(mc, p);
		if (tool != null) return halt(mc, tool);
		// Nothing usable in the HOTBAR yet: a click uses what is held, so swinging now is swinging a
		// bare hand at netherrack with the give-up clock running, which writes the cell off.
		if (usablePick(p, 0, 9) < 0) {
			plan = List.of();
			return null;
		}

        if (deposit != null && System.currentTimeMillis() - progressAt > MINE_STALL_MS) {
            rejectedOre.add(deposit.ore());
            deposit = null;
            Digger.pause(mc);
        }
        if (deposit != null && !isQuartz(mc, deposit.ore())) deposit = null;
        if (deposit == null) {
            Digger.pause(mc);
            plan = List.of();
            Hud.stopGuiding();
            if (oreSearch == null) oreSearch = new QuartzSearch.Search(p.blockPosition());
            deposit = oreSearch.advance(new QuartzSearch.World() {
                public boolean corridor(BlockPos feet) { return miningCorridor(mc, feet); }
                public boolean ore(BlockPos cell) { return isQuartz(mc, cell); }
            }, rejectedOre, 32);
            if (deposit == null && !oreSearch.done()) return null;
            oreSearch = null;
            if (deposit == null) return halt(mc,
                "no reachable quartz found within the 4096-cell loaded, supported corridor search; move to another area");
            oreStep = 0;
            progressAt = System.currentTimeMillis();
        }
        // Keep the stash return point on the last occupied corridor cell.
        while (oreStep < deposit.path().size()
            && WalkingSpace.arrived(p.position(), deposit.path().get(oreStep))) {
            origin = deposit.path().get(oreStep++);
            depth = 1;
            progressAt = System.currentTimeMillis();
        }
        BlockPos next = deposit.path().get(Math.min(oreStep, deposit.path().size()-1));
        if (!miningCorridor(mc, next)) {
            rejectedOre.add(deposit.ore());
            deposit = null;
            plan = List.of();
            Digger.pause(mc);
            Hud.stopGuiding();
            return "quartz approach became unsafe; selecting another deposit";
        }
        var work = new ArrayList<BlockPos>();
        for (BlockPos cell : List.of(next.above(), next))
            if (!mc.level.getBlockState(cell).isAir()) work.add(cell);
        if (!work.isEmpty()) {
            // Dig only the next corridor face on a proven route to known quartz.
            plan = List.copyOf(work);
            Hud.stopGuiding();
        } else {
            plan = List.of();
            Digger.pause(mc);
            Hud.guideMine(next, "walking to quartz at " + Wand.fmt(deposit.ore()));
        }
        return null;
    }

    private static QuartzSearch.Deposit deposit;
    private static QuartzSearch.Search oreSearch;
    private static int oreStep;
    private static final java.util.Set<BlockPos> rejectedOre = new java.util.HashSet<>();

    private static boolean isQuartz(Minecraft mc, BlockPos cell) {
        return mc.level.isLoaded(cell) && mc.level.getBlockState(cell).is(
            net.minecraft.world.level.block.Blocks.NETHER_QUARTZ_ORE);
    }

    private static boolean miningCorridor(Minecraft mc, BlockPos feet) {
        for (BlockPos c : List.of(feet, feet.above())) {
            if (!Digger.authorizedHere(dimension, c) || !Bounds.contains(c)
                || !mc.level.isLoaded(c)) return false;
            var state = mc.level.getBlockState(c);
            if (!state.isAir() && !state.is(net.minecraft.world.level.block.Blocks.NETHERRACK)
                && !state.is(net.minecraft.world.level.block.Blocks.NETHER_QUARTZ_ORE)) return false;
        }
        return mc.level.isLoaded(feet.below()) && mc.level.getBlockState(feet.below()).blocksMotion()
            && LavaGuard.scan(LavaGuard.of(mc.level), List.of(feet, feet.above()),
                LavaGuard.SEGMENT_CLEAR) == null;
    }

	/**
	 * Take the next heading, or stop.
	 *
	 * <p>The new corridor starts at the STAND the old one reached, never at wherever the body
	 * happens to be standing. The body lags the plan - it is walking, and it may be most of a
	 * corridor behind after a stash trip - and re-origining on it would start a branch in the middle
	 * of the last one, from a position that is different every time the same decision is taken.
	 */
	private static String turnAway(Minecraft mc, LocalPlayer p, String why) {
		// THE ROTATION IS FROM A FIXED BASE, not from the heading we have just abandoned. Rotating
		// from the current one walks back through headings that have already failed - clockwise then
		// anticlockwise from the NEW heading is the original one again - and inside TURN_LIMIT that
		// left one of the four cardinals never tried at all.
		if (turns == 0) turnBase = heading;
		if (++turns > TURN_LIMIT) {
			return halt(mc, "boxed in — every way on from " + Wand.fmt(standFor(origin, heading, depth))
				+ " runs into " + why + ". " + report());
		}
		// ...and the same insurance: the old target is on a cell we have just turned away from.
		Digger.pause(mc);
		progressAt = System.currentTimeMillis();          // a new face gets its own clock
		origin = standFor(origin, heading, depth);
		heading = turn(turnBase, turns - 1);
		depth = 1;
		plan = List.of();
		bridgeTries = 0;
		return "turning " + heading.getName() + " — " + why;
	}

	// ---------------------------------------------------------------- finding the ore

	/**
	 * Ore near the body that a swing could actually land on.
	 *
	 * <p>EXPOSED only — at least one air face — because that is what a pickaxe can reach, and
	 * because a vein unravels itself: take the front block and the one behind it is exposed on the
	 * next pass. No vein-following code, no dig-in depth to tune, and no way for it to chase a seam
	 * out of the working box.
	 */
	static List<BlockPos> exposedOre(Minecraft mc, LocalPlayer p) {
		List<BlockPos> out = new ArrayList<>();
		BlockPos me = p.blockPosition();
		// One mutable cursor rather than 1,331 BlockPos per sweep, five sweeps a second. The registry
		// lookup is the real cost here and it is only paid for cells that are not air.
		BlockPos.MutableBlockPos q = new BlockPos.MutableBlockPos();
		for (int dx = -HARVEST_RADIUS; dx <= HARVEST_RADIUS; dx++) {
			for (int dy = -HARVEST_RADIUS; dy <= HARVEST_RADIUS; dy++) {
				for (int dz = -HARVEST_RADIUS; dz <= HARVEST_RADIUS; dz++) {
					q.set(me.getX() + dx, me.getY() + dy, me.getZ() + dz);
					if (!mc.level.isLoaded(q)) continue;
					var st = mc.level.getBlockState(q);
					if (st.isAir()) continue;
					if (!ORE.equals(BuiltInRegistries.BLOCK.getKey(st.getBlock()).getPath())) continue;
					if (!exposed(mc, q)) continue;
					out.add(q.immutable());
				}
			}
		}
		out.sort(Comparator.comparingDouble(ore -> ore.distSqr(me)));
		return out;
	}

	private static boolean exposed(Minecraft mc, BlockPos q) {
		for (Direction d : Direction.values()) {
			BlockPos n = q.relative(d);
			if (mc.level.isLoaded(n) && mc.level.getBlockState(n).isAir()) return true;
		}
		return false;
	}

	// ---------------------------------------------------------------- the tool

	/**
	 * The best slot holding something that will still break rock, or -1.
	 *
	 * <p>A tool at or below {@link #PICK_RESERVE} is not offered at all: starting a block with it
	 * finishes the tool rather than the block, and the swing that breaks it leaves the miner
	 * punching netherrack with the give-up clock running.
	 */
	static int usablePick(LocalPlayer p, int from, int to) {
		var inv = p.getInventory();
		var rock = net.minecraft.world.level.block.Blocks.NETHERRACK.defaultBlockState();
		int best = -1;
		float bestSpeed = 1.0f;                             // a bare hand: anything at or under is no tool
		int slots = Math.min(to, inv.getContainerSize());
		for (int i = from; i < slots; i++) {
			ItemStack st = inv.getItem(i);
			if (st.isEmpty()) continue;
			if (st.isDamageableItem() && st.getMaxDamage() - st.getDamageValue() <= PICK_RESERVE) continue;
			float s = st.getDestroySpeed(rock);
			if (s > bestSpeed) { bestSpeed = s; best = i; }
		}
		return best;
	}

	/** Null while there is something worth swinging, else the sentence to stop on. */
	static String ensureTool(Minecraft mc, LocalPlayer p) {
		if (usablePick(p, 0, 9) >= 0) return null;          // in the hotbar: Digger.holdBestTool picks it
		int spare = usablePick(p, 9, 36);
		if (spare < 0) {
			return "no pickaxe left with more than " + PICK_RESERVE + " uses on it. " + report();
		}
		// A SWAP IS NOT SYNCHRONOUS - you ask, the server decides, and the stack arrives some ticks
		// later. Re-sending it on every replan is how one stack ping-pongs in and out of the pack for
		// ever without a block being broken, which is a failure this project already has on record
		// for the printer's own hotbar swap.
		long now = mc.level.getGameTime();
		if (now < nextSwap) return null;
		nextSwap = now + SWAP_COOLDOWN;
		int dest = Printer.swapSlot(p);
		p.getInventory().setSelectedSlot(dest);
		mc.gameMode.handleContainerInput(p.inventoryMenu.containerId, spare, dest,
			ContainerInput.SWAP, p);
		return null;
	}

	// ---------------------------------------------------------------- danger and escape

	/** What is about to kill us, or null. */
	static String danger(Minecraft mc, LocalPlayer p) {
		if (p.isInLava()) return "standing in lava";
		if (p.getHealth() <= DANGER_HEALTH) {
			return "health down to " + (int) p.getHealth() + " of " + (int) p.getMaxHealth();
		}
		// BURNING ALONE IS TOO TWITCHY - see BURNING_HEALTH. It is a reason to go when it is
		// actually burning us down, not the first time a flame is brushed past.
		if (p.isOnFire() && p.getHealth() <= BURNING_HEALTH) {
			return "on fire at " + (int) p.getHealth() + " health";
		}
		LavaGuard.Threat t = LavaGuard.aroundBody(LavaGuard.of(mc.level), p.blockPosition());
		return t == null ? null : t.describe();
	}

	/**
	 * Get out.
	 *
	 * <p>The teleport is what was asked for, and the one thing that could go wrong with it is that
	 * it silently does nothing — a closed warp, a renamed command, a permission that lapsed. This
	 * project has that exact scar: {@link Rally} says <i>"a teleport that did not teleport is a
	 * silent no-op"</i> and proves its own by recording where the body was and comparing. So does
	 * this, and a command that is proved twice not to work is not sent a third time — after which
	 * the fallback is the thing that needs no server at all: wall in and let the regen run.
	 */
	private static String beginEscape(Minecraft mc, LocalPlayer p, String why) {
		Digger.pause(mc);
		Hud.stopGuiding();
		escapeFrom = null;
		wallTries = 0;
		if (deadEscape >= DEAD_ESCAPE_LIMIT || escapeCommand().isBlank()) {
			escapePhase = Escape.WALLING;
			wallCells = shell(p.blockPosition());
			return "DANGER (" + why + ") — /" + escapeCommand() + " has already been proved not to move"
				+ " us, so walling in where it stands instead.";
		}
		escapePhase = Escape.TELEPORT;
		escapeLanding = LANDING_TICKS;
		escapeFrom = p.blockPosition();
		p.connection.sendCommand(escapeCommand());
		return "DANGER (" + why + ") — escaping with /" + escapeCommand() + ". " + report();
	}

	private static String escapeTick(Minecraft mc, LocalPlayer p) {
		if (escapePhase == Escape.WALLING) return wallTick(mc, p);
		if (escapeLanding-- > 0) return null;
		if (escapeFrom != null && !moved(escapeFrom, p.blockPosition())) {
			deadEscape++;
			escapePhase = Escape.WALLING;
			wallCells = shell(p.blockPosition());
			wallTries = 0;
			return "/" + escapeCommand() + " did not move us — walling in instead. Set one that works"
				+ " here with /cscan mine escape <command>.";
		}
		escapePhase = Escape.NO;
		return halt(mc, "out, and stopped. " + report());
	}

	/** The cells that seal a body in where it stands: four sides at both courses, and the lid. */
	static List<BlockPos> shell(BlockPos feet) {
		List<BlockPos> out = new ArrayList<>();
		for (Direction d : Direction.Plane.HORIZONTAL) {
			out.add(feet.relative(d));
			out.add(feet.above().relative(d));
		}
		out.add(feet.above(2));
		return out;
	}

	/**
	 * Seal the body in where it stands, ONE BLOCK PER TICK.
	 *
	 * <p><b>The loop this replaces placed exactly one block and silently refused the other eight.</b>
	 * {@link Printer#place} is {@code if (busy() || ...) return REFUSED} and {@code busy()} is
	 * {@code !pending.isEmpty()} — so the second call in a tick, and every call after it, is a no-op
	 * until the first placement has been acknowledged. Nine calls in a for-loop looked exactly like a
	 * wall going up and built a single block, in the one routine whose whole job is to be the
	 * fallback when everything else has failed.
	 *
	 * <p>It places into whatever is there, flowing lava included: a block in a lava cell is how you
	 * stop a flow, and refusing to place there would leave open the one face that matters.
	 */
	private static String wallTick(Minecraft mc, LocalPlayer p) {
		List<BlockPos> left = new ArrayList<>();
		for (BlockPos q : wallCells) {
			if (!mc.level.isLoaded(q)) continue;
			if (mc.level.getBlockState(q).blocksMotion()) continue;
			left.add(q);
		}
		wallCells = left;
		if (left.isEmpty()) {
			escapePhase = Escape.NO;
			return halt(mc, "walled in where it stood — break out when you get here. " + report());
		}
		if (++wallTries > WALL_TRIES) {
			escapePhase = Escape.NO;
			return halt(mc, "walled in as far as it could — " + left.size() + " side(s) still open, and"
				+ " no " + PLUG + " to close them. " + report());
		}
		Printer.place(mc, left.get(0), PLUG);
		return null;
	}

	// ---------------------------------------------------------------- the stash

	/**
	 * Walk to the stash, empty the pack, walk back.
	 *
	 * <p><b>EVERY LEG HAS A CLOCK ON IT.</b> Written without one, the GOING and OPENING legs flipped
	 * between each other on every tick, for ever, in silence: GOING sees the body is already within
	 * reach of the approach cell and hands over to OPENING, OPENING cannot get a hit on the chest —
	 * it was broken, or a mob is standing in it, or the approach cell is not actually in reach — and
	 * hands straight back. Nothing moves, nothing is placed, no watchdog anywhere in this mod can
	 * see it, because the job believes it is making progress the whole time.
	 */
	private static String stashTick(Minecraft mc, LocalPlayer p) {
		if (System.currentTimeMillis() - stashLegAt > STASH_LEG_MS) {
			return halt(mc, "could not " + stashing.name().toLowerCase(java.util.Locale.ROOT)
				+ " at the stash " + Wand.fmt(stash) + " within a minute — it may be gone, blocked or"
				+ " out of reach. " + report());
		}
		switch (stashing) {
			case GOING -> {
				BlockPos approach = ContainerInteraction.approach(mc, stash);
				BlockPos aim = approach == null ? stash : approach;
				if (p.blockPosition().closerThan(aim, 1.5)) {
					step(Stash.OPENING);
					return null;
				}
				Hud.guideMine(aim, "stash the quartz");
				return null;
			}
			case OPENING -> {
				if (Screens.container() != null) {
					step(Stash.PUTTING);
					nextPut = 0;
					return null;
				}
				var hit = ContainerInteraction.openingHit(mc, stash);
				if (hit == null) {
					// COUNTED, not flipped straight back. Handing to GOING from here is the ping-pong the
					// class note is about: GOING finds the body already there and hands it right back.
					if (++openTries > OPEN_TRIES) {
						return halt(mc, "cannot open the stash at " + Wand.fmt(stash)
							+ " from where the miner can stand. Move it somewhere with a clear face. " + report());
					}
					return null;
				}
				mc.gameMode.useItemOn(p, net.minecraft.world.InteractionHand.MAIN_HAND, hit);
				return null;
			}
			case PUTTING -> {
				return put(mc, p);
			}
			case RETURNING -> {
				BlockPos stand = standFor(origin, heading, depth);
				if (p.blockPosition().closerThan(stand, ARRIVE)) {
					step(Stash.NO);
					nextPlan = 0;
					return null;
				}
				Hud.guideMine(stand, "back to the face");
				return null;
			}
			default -> {
				return null;
			}
		}
	}

	/**
	 * One stack per pass, and the pack is re-read each time.
	 *
	 * <p>Opening a chest is not synchronous — you ask, the server decides, and the contents arrive
	 * some ticks later — so clicking a handful of slots in one tick takes nothing and looks like a
	 * desync. The same discipline {@link Withdraw} runs under, and the same gesture: a shift-click
	 * is a deposit or a withdrawal depending only on which half of the menu the stack starts in.
	 */
	private static String put(Minecraft mc, LocalPlayer p) {
		var screen = Screens.container();
		if (screen == null) {                               // it closed under us
			step(Stash.GOING);
			return null;
		}
		long now = mc.level.getGameTime();
		if (now < nextPut) return null;
		nextPut = now + 2;

		var inv = p.getInventory();
		var menu = screen.getMenu();
		int plugHeld = 0;
		for (var slot : menu.slots) {
			if (slot.container != inv) continue;
			ItemStack st = slot.getItem();
			if (st.isEmpty()) continue;
			String item = BuiltInRegistries.ITEM.getKey(st.getItem()).getPath();
			boolean edible = st.get(net.minecraft.core.component.DataComponents.FOOD) != null;
			if (keep(item, st.isDamageableItem(), edible, st.getCount(), plugHeld)) {
				if (item.equals(PLUG)) plugHeld += st.getCount();
				continue;
			}
			mc.gameMode.handleContainerInput(menu.containerId, slot.index, 0,
				ContainerInput.QUICK_MOVE, p);
			return null;
		}

		// Nothing left to put away. If the pack is STILL full the chest is, and saying so is the
		// difference between a job that stops with a reason and one that walks back and forth.
		p.closeContainer();
		trips++;
		if (full(emptySlots(p), RESERVE_SLOTS)) {
			if (++stashFails >= STASH_FAIL_LIMIT) {
				return halt(mc, "the stash at " + Wand.fmt(stash) + " will not take any more —"
					+ " empty it, or put a bigger one there. " + report());
			}
			step(Stash.GOING);
			return null;
		}
		step(Stash.RETURNING);
		return "stashed — " + report();
	}

	/** Move to the next leg of the stash trip, and start that leg's own clock. */
	private static void step(Stash next) {
		stashing = next;
		stashLegAt = System.currentTimeMillis();
		// ...and the FACE's clock too, or a two-minute walk to the chest and back reads as two
		// minutes of a face producing nothing and turns the corridor the moment the miner gets home.
		progressAt = stashLegAt;
		if (next != Stash.OPENING) openTries = 0;
	}

	// ---------------------------------------------------------------- odds and ends

	static int emptySlots(LocalPlayer p) {
		var inv = p.getInventory();
		int empty = 0;
		int slots = Math.min(36, inv.getContainerSize());
		for (int i = 0; i < slots; i++) if (inv.getItem(i).isEmpty()) empty++;
		return empty;
	}

	/** The nearest thing that holds items, for a stash you did not have to name. */
	static BlockPos nearestContainer(Minecraft mc, BlockPos near) {
		BlockPos best = null;
		double bestD = Double.MAX_VALUE;
		int cx = near.getX() >> 4, cz = near.getZ() >> 4;
		for (int x = cx - 1; x <= cx + 1; x++) {
			for (int z = cz - 1; z <= cz + 1; z++) {
				if (!mc.level.getChunkSource().hasChunk(x, z)) continue;
				for (BlockPos q : mc.level.getChunk(x, z).getBlockEntities().keySet()) {
					String block = BuiltInRegistries.BLOCK.getKey(
						mc.level.getBlockState(q).getBlock()).getPath();
					if (!Storage.stores(block)) continue;
					double d = q.distSqr(near);
					if (d < bestD && d <= STASH_SEARCH * STASH_SEARCH) { bestD = d; best = q.immutable(); }
				}
			}
		}
		return best;
	}

	static String escapeCommand() {
		return escapeCommand.isBlank() ? Rally.home() : escapeCommand;
	}

	static String setEscape(String typed) {
		escapeCommand = typed == null ? "" : typed.trim();
		deadEscape = 0;                                     // a new command has not failed yet
		return "the miner will escape with /" + escapeCommand();
	}

	/** Coordinates mean nothing without a world: everything positional goes on a disconnect. */
	static void forget() {
		on = false;
		escapePhase = Escape.NO;
		wallCells = List.of();
		stashing = Stash.NO;
		origin = areaMin = areaMax = stash = escapeFrom = null;
		heading = null;
		dimension = "";
		plan = List.of();
	}
}
