package dev.jack.chunkscan;

import com.mojang.brigadier.arguments.IntegerArgumentType;
import com.mojang.brigadier.arguments.StringArgumentType;
import com.mojang.brigadier.arguments.DoubleArgumentType;
import com.mojang.brigadier.context.CommandContext;
import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.fabric.api.client.command.v2.ClientCommandRegistrationCallback;
import net.fabricmc.fabric.api.client.command.v2.FabricClientCommandSource;
import net.minecraft.client.Minecraft;
import net.minecraft.client.multiplayer.ClientLevel;
import net.minecraft.client.player.LocalPlayer;
import net.minecraft.commands.arguments.blocks.BlockStateParser;
import net.minecraft.core.BlockPos;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.network.chat.Component;
import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.phys.HitResult;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

import static net.fabricmc.fabric.api.client.command.v2.ClientCommands.argument;
import static net.fabricmc.fabric.api.client.command.v2.ClientCommands.literal;

/**
 * /cscan &lt;name&gt; [radius]         — loaded chunks within radius, cropped to non-air bounds
 * /cscan chunks &lt;name&gt; [radius]  — same, but XZ kept on the exact chunk grid
 */
public final class ChunkScanClient implements ClientModInitializer {
	public static final Logger LOG = LoggerFactory.getLogger("chunkscan");
	private static final int DEFAULT_RADIUS = 8;
	private static final int MAX_RADIUS = 32;
	/** Two corners 200 blocks apart is 8M cells; the walk alone would freeze the client. */
	static final long MAX_FILL_CELLS = 32768;
	/** Scratch fills are prefixed so `/cscan place` with no argument never sweeps them up. */
	static final String FILL_PREFIX = "_fill ";
	/** Clips are scratch too: same reason they stay out of a bare `/cscan place`. */
	static final String CLIP_PREFIX = "_clip ";
	/** What a fill would overwrite, kept so the wand is safe to experiment with. */
	static final String UNDO_PREFIX = "_undo ";
	/** A fill name becomes a filename, so it may not contain a path separator or `..`. */
	private static final java.util.regex.Pattern FILL_NAME = java.util.regex.Pattern.compile("[A-Za-z0-9 _.-]{1,48}");

	@Override
	public void onInitializeClient() {
		ContainerWatcher.register();
		Highlight.register();
		AutoScan.register();
		Wand.register();
		Hud.register();
		Menu.register();
		Screens.register();
		Autopilot.register();
		// RESUME. The loop's whole point is running while you are not watching, and a dropped
		// connection at three in the morning otherwise ends it silently. Hud.resume holds off for a
		// few seconds first: on the tick you join most of the world is unloaded, and Nav counts
		// unloaded as passable - correct for a route in progress, and quite wrong as the first thing
		// you do after arriving.
		net.fabricmc.fabric.api.client.networking.v1.ClientPlayConnectionEvents.JOIN.register(
			(handler, sender, client) -> Hud.resume(client));
		ClientCommandRegistrationCallback.EVENT.register((dispatcher, registryAccess) ->
			dispatcher.register(literal("cscan")
				.then(literal("place")
					.executes(ctx -> place(ctx, null))
					.then(argument("design", StringArgumentType.greedyString())
						.executes(ctx -> place(ctx, StringArgumentType.getString(ctx, "design")))))
				.then(literal("mark")
					.then(argument("label", StringArgumentType.greedyString())
						.executes(ChunkScanClient::mark)))
				.then(literal("marks").executes(ChunkScanClient::marks))
				.then(literal("unmark")
					.then(argument("label", StringArgumentType.greedyString())
						.executes(ChunkScanClient::unmark)))
				.then(literal("dig")
					.executes(ctx -> { Highlight.clear(); ctx.getSource().sendFeedback(Component.literal("[cscan] highlights cleared")); return 1; })
					.then(argument("design", StringArgumentType.greedyString())
						.executes(ChunkScanClient::dig)))
				.then(literal("need")
					.then(argument("design", StringArgumentType.greedyString())
						.executes(ctx -> need(ctx, 48))))
				.then(literal("next")
					.executes(ctx -> { Highlight.clear("next"); ok(ctx.getSource(), "work queue cleared"); return 1; })
					.then(argument("design", StringArgumentType.greedyString())
						.executes(ctx -> next(ctx, 24))))
				.then(literal("check")
					.then(argument("design", StringArgumentType.greedyString())
						.executes(ChunkScanClient::check)))
				.then(literal("find")
					.then(argument("query", StringArgumentType.greedyString())
						.executes(ChunkScanClient::find)))
				.then(literal("chests").executes(ChunkScanClient::chests))
				.then(literal("label")
					.then(argument("text", StringArgumentType.greedyString())
						.executes(ChunkScanClient::label)))
				.then(literal("auto")
					.executes(ctx -> { ctx.getSource().sendFeedback(Component.literal("[cscan] " + AutoScan.status())); return 1; })
					.then(literal("off").executes(ctx -> { AutoScan.stop(); ctx.getSource().sendFeedback(Component.literal("[cscan] auto-scan off")); return 1; }))
					.then(argument("name", StringArgumentType.word())
						.then(argument("minutes", IntegerArgumentType.integer(1, 120))
							.executes(ChunkScanClient::auto))))
				.then(literal("wand")
					.executes(ChunkScanClient::wandStatus)
					.then(literal("on").executes(ctx -> wandArm(ctx, true)))
					.then(literal("off").executes(ctx -> wandArm(ctx, false)))
					.then(literal("clear").executes(ctx -> { Wand.clear(); ok(ctx.getSource(), "selection cleared"); return 1; })))
				.then(literal("mat")
					.executes(ctx -> mat(ctx, null))
					.then(argument("block", StringArgumentType.greedyString())
						.executes(ctx -> mat(ctx, StringArgumentType.getString(ctx, "block")))))
				.then(literal("fill")
					.executes(ctx -> fill(ctx, null, Fill.Mode.SOLID, null))
					.then(shapeArg("solid", Fill.Mode.SOLID))
					.then(shapeArg("hollow", Fill.Mode.HOLLOW))
					.then(shapeArg("walls", Fill.Mode.WALLS))
					.then(shapeArg("outline", Fill.Mode.OUTLINE))
					.then(shapeArg("ball", Fill.Mode.BALL))
					.then(shapeArg("sphere", Fill.Mode.SPHERE))
					.then(shapeArg("dome", Fill.Mode.DOME))
					.then(shapeArg("cylinder", Fill.Mode.CYLINDER))
					.then(shapeArg("tube", Fill.Mode.TUBE))
					.then(shapeArg("disc", Fill.Mode.DISC))
					.then(shapeArg("ring", Fill.Mode.RING))
					.then(argument("name", StringArgumentType.greedyString())
						.executes(ctx -> fill(ctx, StringArgumentType.getString(ctx, "name"), Fill.Mode.SOLID, null))))
				.then(literal("copy")
					.then(argument("name", StringArgumentType.greedyString())
						.executes(ChunkScanClient::copy)))
				.then(literal("paste")
					.then(argument("name", StringArgumentType.word())
						.executes(ctx -> paste(ctx, "NONE"))
						.then(argument("rot", StringArgumentType.word())
							.executes(ctx -> paste(ctx, Litematica.rotationOf(StringArgumentType.getString(ctx, "rot")))))))
				.then(literal("move")
					.executes(ChunkScanClient::moveStatus)
					.then(literal("next").executes(ChunkScanClient::moveNext))
					.then(literal("done").executes(ChunkScanClient::moveDone))
					.then(literal("reset").executes(ChunkScanClient::moveReset)))
				.then(literal("stack")
					.then(argument("name", StringArgumentType.word())
						.then(argument("count", IntegerArgumentType.integer(1, 64))
							.then(argument("dir", StringArgumentType.word())
								.executes(ctx -> stack(ctx, 0))
								.then(argument("step", IntegerArgumentType.integer(1, 512))
									.executes(ctx -> stack(ctx, IntegerArgumentType.getInteger(ctx, "step"))))))))
				.then(literal("scaffold")
					.then(argument("design", StringArgumentType.greedyString())
						.executes(ChunkScanClient::scaffold)))
				.then(literal("plan")
					.executes(ChunkScanClient::planAll)
					.then(argument("design", StringArgumentType.greedyString())
						.executes(ChunkScanClient::planWork)))
				.then(literal("goto")
					.executes(ctx -> { Hud.stopGuiding(); Highlight.clear("goto");
						ok(ctx.getSource(), "guidance off"); return 1; })
					.then(argument("n", IntegerArgumentType.integer(1, Plan.MAX_CLUSTERS))
						.executes(ChunkScanClient::gotoCluster)))
				.then(literal("autofly")
					.executes(ctx -> { ok(ctx.getSource(), "autofly " + (Autopilot.on() ? "ON" : "off")
						+ " — it flies (or walks, when you are not flying) to whatever the HUD arrow"
						+ " is pointing at. No key stops it; /cscan stop does.");
						return 1; })
					.then(literal("on").executes(ctx -> {
						Autopilot.set(true);
						Hud.remember(ctx.getSource().getClient());
						// Report the ACTUAL state, not the switch. "ON" alone sent Jack looking for a
						// bug in the flying when the real answer was that nothing had told it where.
						String why = Autopilot.stalledBecause(net.minecraft.client.Minecraft.getInstance());
						ok(ctx.getSource(), "autofly ON — needs a destination from goto or follow. It"
							+ " walks when you are not flying, and no key interrupts it: /cscan stop."
							+ (why == null ? "" : "  Waiting: " + why + "."));
						return 1; }))
					.then(literal("off").executes(ctx -> {
						Autopilot.set(false);
						Hud.remember(ctx.getSource().getClient());
						ok(ctx.getSource(), "autofly off");
						return 1; }))
					.then(literal("speed")
						.executes(ctx -> { ok(ctx.getSource(), "autofly speed "
							+ String.format("%.2f", Autopilot.speed()) + " blocks/tick ("
							+ String.format("%.1f", Autopilot.speed() * 20) + " blocks/s). Set it"
							+ " with /cscan autofly speed <" + Autopilot.MIN_SPEED + "-"
							+ Autopilot.MAX_SPEED + ">; vanilla sprint-flight is about 1.0.");
							return 1; })
						.then(argument("blocks per tick", DoubleArgumentType.doubleArg())
							.executes(ctx -> {
								double got = Autopilot.setSpeed(
									DoubleArgumentType.getDouble(ctx, "blocks per tick"));
								Hud.remember(ctx.getSource().getClient());
								ok(ctx.getSource(), "autofly speed " + String.format("%.2f", got)
									+ " blocks/tick (" + String.format("%.1f", got * 20)
									+ " blocks/s)");
								if (got > Autopilot.RISKY_SPEED) {
									ok(ctx.getSource(), "careful: past a player's own sprint-fly,"
										+ " which is the only speed anyone here has evidence"
										+ " about.");
								}
								return 1; }))))
				.then(literal("fetch")
					.executes(ctx -> {
						Hud.stopFetching(ctx.getSource().getClient());
						ok(ctx.getSource(), "fetch cancelled — that chest is skipped for now");
						return 1; })
					.then(argument("design", StringArgumentType.greedyString())
						.executes(ChunkScanClient::fetch)))
				.then(literal("follow")
					.executes(ctx -> {
						// Stopping is also when you find out what it did while you were elsewhere.
						String report = Hud.following() ? "  " + Hud.sessionReport() : "";
						Hud.off(); Highlight.clear("goto");
						Hud.remember(ctx.getSource().getClient());
						ok(ctx.getSource(), "follow off." + report); return 1; })
					.then(literal("all").executes(ChunkScanClient::followAll))
					.then(argument("design", StringArgumentType.greedyString())
						.executes(ChunkScanClient::follow)))
				.then(literal("hud")
					.executes(ctx -> { ok(ctx.getSource(), Hud.watching() == null ? "hud off"
						: "hud watching " + Hud.watching()); return 1; })
					.then(literal("off").executes(ctx -> { Hud.off(); ok(ctx.getSource(), "hud off"); return 1; }))
					.then(argument("design", StringArgumentType.greedyString())
						.executes(ctx -> {
							String d = StringArgumentType.getString(ctx, "design");
							Hud.watch(d);
							ok(ctx.getSource(), "hud watching " + d + " — updates every "
								+ (Hud.EVERY_TICKS / 20) + "s");
							return 1;
						})))
				.then(literal("dark")
					.executes(ctx -> dark(ctx, 32))
					.then(argument("radius", IntegerArgumentType.integer(4, 128))
						.executes(ctx -> dark(ctx, IntegerArgumentType.getInteger(ctx, "radius")))))
				.then(literal("bom")
					.then(argument("design", StringArgumentType.greedyString())
						.executes(ChunkScanClient::bom)))
				.then(literal("around")
					.then(argument("radius", IntegerArgumentType.integer(1, 64))
						.executes(ChunkScanClient::around)))
				.then(literal("clips").executes(ChunkScanClient::clips))
				.then(literal("stop")
					.executes(ChunkScanClient::stopAll))
				.then(literal("take")
					.executes(ctx -> take(ctx, null, 0))
					.then(argument("item", StringArgumentType.word())
						.then(argument("count", IntegerArgumentType.integer(1, 4096))
							.executes(ctx -> take(ctx, StringArgumentType.getString(ctx, "item"),
								IntegerArgumentType.getInteger(ctx, "count"))))))
				.then(literal("tidy")
					.executes(ctx -> tidy(ctx, 0))
					.then(argument("n", IntegerArgumentType.integer(1, 40))
						.executes(ctx -> tidy(ctx, IntegerArgumentType.getInteger(ctx, "n")))))
				.then(literal("prune").executes(ChunkScanClient::prune))
				.then(literal("replace")
					.then(argument("from", StringArgumentType.word())
						.then(argument("to", StringArgumentType.greedyString())
							.executes(ChunkScanClient::replace))))
				.then(literal("sel")
					.then(argument("name", StringArgumentType.word())
						.executes(ChunkScanClient::selection)))
				.then(literal("chunks")
					.then(argument("name", StringArgumentType.word())
						.executes(ctx -> run(ctx, DEFAULT_RADIUS, true))
						.then(argument("radius", IntegerArgumentType.integer(0, MAX_RADIUS))
							.executes(ctx -> run(ctx, IntegerArgumentType.getInteger(ctx, "radius"), true)))))
				.then(argument("name", StringArgumentType.word())
					.executes(ctx -> run(ctx, DEFAULT_RADIUS, false))
					.then(argument("radius", IntegerArgumentType.integer(0, MAX_RADIUS))
						.executes(ctx -> run(ctx, IntegerArgumentType.getInteger(ctx, "radius"), false))))));
		LOG.info("chunkscan ready: scan | place | need | next | check | mark | dig | find | chests | label | auto | sel");
	}

	// ---------------------------------------------------------------- helpers

	private static Path dir(FabricClientCommandSource src) {
		return ScanRunner.schematicsDir(src.getClient());
	}

	private static void ok(FabricClientCommandSource src, String msg) {
		src.sendFeedback(Component.literal("[cscan] " + msg));
	}

	/** The block the player is looking at (up to 6 blocks), else the block under their feet. */
	private static BlockPos targeted(Minecraft mc) {
		HitResult hit = mc.hitResult;
		if (hit instanceof BlockHitResult bhr && hit.getType() == HitResult.Type.BLOCK) return bhr.getBlockPos();
		return mc.player.blockPosition().below();
	}

	// ---------------------------------------------------------------- commands

	private static int wandStatus(CommandContext<FabricClientCommandSource> ctx) {
		FabricClientCommandSource src = ctx.getSource();
		ok(src, "wand " + (Wand.armed() ? "ARMED" : "off") + " (cooked beef)"
			+ "  corner1 " + (Wand.pos1() == null ? "-" : Wand.fmt(Wand.pos1()))
			+ "  corner2 " + (Wand.pos2() == null ? "-" : Wand.fmt(Wand.pos2()))
			+ "  box " + Wand.describe()
			+ "  material " + (Wand.material() == null ? "-" : blockName(Wand.material())));
		return 1;
	}

	private static int wandArm(CommandContext<FabricClientCommandSource> ctx, boolean on) {
		Wand.arm(on);
		ok(ctx.getSource(), on
			? "wand ARMED — right-click a block for corner 1, again for corner 2. Steak will not be eaten while armed."
			: "wand off — steak is food again");
		return 1;
	}

	/** Material from a typed name, or from whatever block is in your hand. */
	private static int mat(CommandContext<FabricClientCommandSource> ctx, String typed) {
		FabricClientCommandSource src = ctx.getSource();
		try {
			BlockState state;
			if (typed != null && !typed.isBlank()) {
				state = BlockStateParser.parseForBlock(BuiltInRegistries.BLOCK, typed.trim(), false).blockState();
			} else {
				LocalPlayer p = src.getClient().player;
				if (p == null) { src.sendError(Component.literal("[cscan] no player")); return 0; }
				state = Wand.blockOf(p.getMainHandItem());
				if (state == null) {
					src.sendError(Component.literal("[cscan] hold a block, or name one: /cscan mat stone_bricks"));
					return 0;
				}
			}
			Wand.material(state);
			String name = blockName(state);
			ok(src, "material " + name);
			// WARN, never refuse. The 1.19 allowlist is provisional and DIRT IS CURRENCY here - both
			// are things every other check in the pipeline passes silently.
			for (String o : Rules.objections(name)) src.sendError(Component.literal("[cscan] WARNING: " + name + " is " + o));
			return 1;
		} catch (Exception e) {
			src.sendError(Component.literal("[cscan] not a block: " + e.getMessage()));
			return 0;
		}
	}

	/**
	 * Write the box as a design and hand it to Litematica for the printer. Named with the FILL_PREFIX
	 * so the bare `/cscan place` never sweeps a scratch fill in with the real designs - the same trap
	 * the 54-design shelf already set once.
	 */
	private static int fill(CommandContext<FabricClientCommandSource> ctx, String name,
	                        Fill.Mode mode, String replaceOnly) {
		FabricClientCommandSource src = ctx.getSource();
		Minecraft mc = src.getClient();
		ClientLevel level = mc.level;
		LocalPlayer player = mc.player;
		if (level == null || player == null) { src.sendError(Component.literal("[cscan] no world")); return 0; }
		if (!Wand.complete()) {
			src.sendError(Component.literal("[cscan] no box — /cscan wand on, then right-click two opposite corners"));
			return 0;
		}
		String here = level.dimension().identifier().toString();
		if (!Wand.dimension().isEmpty() && !Wand.dimension().equals(here)) {
			src.sendError(Component.literal("[cscan] the box was marked in " + Wand.dimension()
				+ " and you are in " + here + " — re-mark it here"));
			return 0;
		}
		if (Wand.material() == null) {
			src.sendError(Component.literal("[cscan] no material — /cscan mat <block>, or hold one and /cscan mat"));
			return 0;
		}
		long vol = Wand.volume();
		if (vol > MAX_FILL_CELLS) {
			src.sendError(Component.literal("[cscan] box is " + vol + " cells, cap is " + MAX_FILL_CELLS
				+ " — that would hang the client. Pick a smaller box."));
			return 0;
		}
		try {
			Fill.Probe probe = Fill.of(level);
			Fill.Plan plan = Fill.plan(probe, Wand.pos1(), Wand.pos2(), Wand.material(), mode, replaceOnly);
			if (plan.place() == 0) {
				ok(src, "nothing to do — of " + vol + " cells, " + plan.already() + " are already the material, "
					+ plan.skipProtected() + " protected, " + plan.outsideShape()
					+ (replaceOnly != null ? " not " + Rules.shortName(replaceOnly) : " outside the shape"));
				return 1;
			}
			String want = (name == null || name.isBlank()) ? "fill" : name.trim();
			// The fill name becomes a FILENAME. `resolve` on "../../x" walks straight out of the
			// schematics folder, and a stray slash would write somewhere baffling and fail later.
			if (!FILL_NAME.matcher(want).matches()) {
				src.sendError(Component.literal("[cscan] name: letters, digits, space, _ - . only (got \"" + want + "\")"));
				return 0;
			}
			String design = FILL_PREFIX + want;
			Path d = dir(src);
			Path lit = d.resolve(design + ".litematic");
			Path side = d.resolve(design + ".scan.json");
			Capture cap = Fill.capture(probe, plan);
			LitematicWriter.write(lit, cap, design, player.getName().getString(),
				"wand " + (replaceOnly != null ? "replace " + Rules.shortName(replaceOnly) + " -> " : "fill ")
					+ plan.materialName() + " " + plan.mode().name().toLowerCase(java.util.Locale.ROOT)
					+ " " + plan.sizeX() + "x" + plan.sizeY() + "x" + plan.sizeZ());
			SidecarWriter.write(side, cap, design, lit.getFileName().toString(), mc, level, player, 0, false);

			// The undo goes out BEFORE the report, so a fill is never announced without one.
			try {
				List<int[]> dig = new ArrayList<>();
				Capture before = Fill.undoCapture(probe, plan, dig);
				String undo = UNDO_PREFIX + want;
				Path ulit = d.resolve(undo + ".litematic");
				LitematicWriter.write(ulit, before, undo, player.getName().getString(),
					"undo for " + design + " — place these back, then /cscan dig \"" + undo + "\"");
				SidecarWriter.write(d.resolve(undo + ".scan.json"), before, undo,
					ulit.getFileName().toString(), mc, level, player, 0, false);
				Work.writeDig(d, undo, dig);
				ok(src, "undo saved: " + before.nonAirCount() + " to restore, " + dig.size()
					+ " to break — /cscan paste is not it, use Litematica on \"" + undo + "\"");
			} catch (Exception e) {
				LOG.warn("undo snapshot failed", e);
				src.sendError(Component.literal("[cscan] WARNING: no undo was saved (" + e.getMessage() + ")"));
			}

			ok(src, design + " [" + plan.mode().name().toLowerCase(java.util.Locale.ROOT) + "]: "
				+ plan.place() + " to place, " + plan.already() + " already "
				+ Rules.shortName(plan.materialName()) + ", " + plan.skipProtected() + " protected and skipped"
				+ (plan.skipProtected() > 0 ? " (" + Fill.skipSummary(plan) + ")" : ""));
			for (String o : Rules.objections(plan.materialName()))
				src.sendError(Component.literal("[cscan] WARNING: " + plan.materialName() + " is " + o));

			if (Litematica.present()) {
				Litematica.place(lit, plan.min(), design);
				ok(src, "placed at " + Wand.fmt(plan.min()) + " — the printer can build it now");
			} else {
				ok(src, "wrote " + lit.getFileName() + " (Litematica not loaded, so nothing was placed)");
			}
			return 1;
		} catch (Exception e) {
			src.sendError(Component.literal("[cscan] fill failed: " + e.getMessage()));
			LOG.warn("fill failed", e);
			return 0;
		}
	}

	/**
	 * Swap one block for another inside the box and leave everything else alone. This is the deck
	 * floor's wood reclaim done by hand: 70 blocks of dark oak healed back into the plane they
	 * interrupted, without touching the 1,700 cells around them.
	 */
	private static int replace(CommandContext<FabricClientCommandSource> ctx) {
		FabricClientCommandSource src = ctx.getSource();
		String from = StringArgumentType.getString(ctx, "from").trim();
		String to = StringArgumentType.getString(ctx, "to").trim();
		try {
			BlockState toState = BlockStateParser.parseForBlock(BuiltInRegistries.BLOCK, to, false).blockState();
			// `from` is matched by NAME, not by state: you want every facing of a stair gone, not one.
			BlockStateParser.parseForBlock(BuiltInRegistries.BLOCK, from, false);
			BlockState keep = Wand.material();
			Wand.material(toState);
			try {
				return fill(ctx, "replace " + Rules.shortName(from) + " to " + Rules.shortName(to),
					Fill.Mode.SOLID, from);
			} finally {
				Wand.material(keep);          // /cscan replace must not quietly change your fill material
			}
		} catch (Exception e) {
			src.sendError(Component.literal("[cscan] not a block: " + e.getMessage()));
			return 0;
		}
	}

	/**
	 * Capture the wand's box exactly as it stands, so it can be pasted elsewhere. This is a SCAN of
	 * a box, which the mod has always been able to do - `/cscan sel` reads Litematica's own selection
	 * the same way. The wand just makes marking the box a two-click job.
	 */
	private static int copy(CommandContext<FabricClientCommandSource> ctx) {
		FabricClientCommandSource src = ctx.getSource();
		Minecraft mc = src.getClient();
		if (mc.level == null || mc.player == null) { src.sendError(Component.literal("[cscan] no world")); return 0; }
		if (!Wand.complete()) {
			src.sendError(Component.literal("[cscan] no box — /cscan wand on, then right-click two opposite corners"));
			return 0;
		}
		long vol = Wand.volume();
		if (vol > MAX_FILL_CELLS) {
			src.sendError(Component.literal("[cscan] box is " + vol + " cells, cap is " + MAX_FILL_CELLS));
			return 0;
		}
		String want = StringArgumentType.getString(ctx, "name").trim();
		if (!FILL_NAME.matcher(want).matches()) {
			src.sendError(Component.literal("[cscan] name: letters, digits, space, _ - . only"));
			return 0;
		}
		try {
			BlockPos a = Wand.pos1(), b = Wand.pos2();
			int[] box = {Math.min(a.getX(), b.getX()), Math.min(a.getY(), b.getY()), Math.min(a.getZ(), b.getZ()),
			             Math.max(a.getX(), b.getX()), Math.max(a.getY(), b.getY()), Math.max(a.getZ(), b.getZ())};
			Capture cap = WorldCapture.captureBox(mc.level, box);
			String design = CLIP_PREFIX + want;
			Path d = dir(src);
			Path lit = d.resolve(design + ".litematic");
			LitematicWriter.write(lit, cap, design, mc.player.getName().getString(),
				"chunkscan clipboard " + cap.sizeX() + "x" + cap.sizeY() + "x" + cap.sizeZ());
			SidecarWriter.write(d.resolve(design + ".scan.json"), cap, design, lit.getFileName().toString(),
				mc, mc.level, mc.player, 0, false);
			ok(src, "copied " + want + ": " + cap.sizeX() + "x" + cap.sizeY() + "x" + cap.sizeZ()
				+ ", " + cap.nonAirCount() + " blocks — /cscan paste " + want + " [90|180|270]");
			return 1;
		} catch (Exception e) {
			src.sendError(Component.literal("[cscan] copy failed: " + e.getMessage()));
			return 0;
		}
	}

	/**
	 * Place a clip so its corner lands on the block you are LOOKING at, which is how you aim it.
	 * Nothing is built: this registers a Litematica placement and the printer does the work, so a
	 * paste in the wrong spot costs one placement deletion rather than a rebuild.
	 */
	private static int paste(CommandContext<FabricClientCommandSource> ctx, String rotation) {
		FabricClientCommandSource src = ctx.getSource();
		Minecraft mc = src.getClient();
		if (mc.level == null || mc.player == null) { src.sendError(Component.literal("[cscan] no world")); return 0; }
		if (!Litematica.present()) { src.sendError(Component.literal("[cscan] Litematica is not loaded")); return 0; }
		String name = StringArgumentType.getString(ctx, "name").trim();
		try {
			String design = CLIP_PREFIX + name;
			Path lit = dir(src).resolve(design + ".litematic");
			if (!java.nio.file.Files.exists(lit)) {
				src.sendError(Component.literal("[cscan] no clip called " + name + " — /cscan clips"));
				return 0;
			}
			BlockPos at = targeted(mc);
			Litematica.place(lit, at, design + " @" + Wand.fmt(at), rotation);
			ok(src, "pasted " + name + " at " + Wand.fmt(at)
				+ (rotation.equals("NONE") ? "" : " rotated " + rotation.toLowerCase(java.util.Locale.ROOT))
				+ " — the printer can build it now");
			return 1;
		} catch (Exception e) {
			src.sendError(Component.literal("[cscan] paste failed: " + e.getMessage()));
			LOG.warn("paste failed", e);
			return 0;
		}
	}

	/**
	 * Paste a clip N times along an axis. A colonnade, a rim rhythm, a row of piers: build the module
	 * once and repeat it, which is the whole reason copy/paste earns its place.
	 *
	 * <p>`step` defaults to the clip's own size along that axis, so the copies sit flush. Give it
	 * explicitly to leave gaps - a 3-wide bay on a step of 6 is the cloister rhythm the gallery wanted.
	 */
	private static int stack(CommandContext<FabricClientCommandSource> ctx, int step) {
		FabricClientCommandSource src = ctx.getSource();
		Minecraft mc = src.getClient();
		if (mc.level == null || mc.player == null) { src.sendError(Component.literal("[cscan] no world")); return 0; }
		if (!Litematica.present()) { src.sendError(Component.literal("[cscan] Litematica is not loaded")); return 0; }
		String name = StringArgumentType.getString(ctx, "name").trim();
		int count = IntegerArgumentType.getInteger(ctx, "count");
		String dirName = StringArgumentType.getString(ctx, "dir").trim().toLowerCase(java.util.Locale.ROOT);
		net.minecraft.core.Direction dir = switch (dirName) {
			case "north" -> net.minecraft.core.Direction.NORTH;
			case "south" -> net.minecraft.core.Direction.SOUTH;
			case "east" -> net.minecraft.core.Direction.EAST;
			case "west" -> net.minecraft.core.Direction.WEST;
			case "up" -> net.minecraft.core.Direction.UP;
			case "down" -> net.minecraft.core.Direction.DOWN;
			default -> null;
		};
		if (dir == null) {
			src.sendError(Component.literal("[cscan] direction: north south east west up down"));
			return 0;
		}
		try {
			String design = CLIP_PREFIX + name;
			Path lit = dir(src).resolve(design + ".litematic");
			if (!java.nio.file.Files.exists(lit)) {
				src.sendError(Component.literal("[cscan] no clip called " + name + " — /cscan clips"));
				return 0;
			}
			if (step == 0) {
				// flush by default: the clip's own extent along the axis it is being repeated on
				Path side = dir(src).resolve(design + ".scan.json");
				com.google.gson.JsonObject o = com.google.gson.JsonParser
					.parseString(java.nio.file.Files.readString(side, java.nio.charset.StandardCharsets.UTF_8))
					.getAsJsonObject().getAsJsonObject("size");
				step = switch (dir.getAxis()) {
					case X -> o.get("x").getAsInt();
					case Y -> o.get("y").getAsInt();
					case Z -> o.get("z").getAsInt();
				};
			}
			BlockPos at = targeted(mc);
			for (int i = 0; i < count; i++) {
				BlockPos p = at.relative(dir, step * i);
				Litematica.place(lit, p, design + " #" + (i + 1) + " @" + Wand.fmt(p), "NONE");
			}
			ok(src, "stacked " + name + " x" + count + " " + dirName + " every " + step
				+ " from " + Wand.fmt(at) + " — " + count + " placements added");
			return 1;
		} catch (Exception e) {
			src.sendError(Component.literal("[cscan] stack failed: " + e.getMessage()));
			LOG.warn("stack failed", e);
			return 0;
		}
	}

	/** Design cells with nothing to place against — you cannot put a block in mid-air. */
	private static int scaffold(CommandContext<FabricClientCommandSource> ctx) {
		FabricClientCommandSource src = ctx.getSource();
		String name = StringArgumentType.getString(ctx, "design");
		try {
			Minecraft mc = src.getClient();
			Work.Split sp = Work.split(mc.level, dir(src), name, mc.player.blockPosition(), 0);
			List<Work.Cell> air = Work.floating(mc.level, sp.todo());
			if (air.isEmpty()) {
				Highlight.clear("scaffold");
				ok(src, sp.name() + ": every unbuilt cell has something to place against");
				return 1;
			}
			Highlight.show("scaffold", Work.positions(air, 200), 0xFF4060, 300);
			ok(src, sp.name() + ": " + air.size() + " of " + sp.todo().size()
				+ " cells have nothing to place against — marked red");
			Work.Cell f = air.get(0);
			ok(src, "  lowest at " + f.pos().getX() + " " + f.pos().getY() + " " + f.pos().getZ()
				+ " (" + f.block() + ") — that one needs scaffolding first");
			return 1;
		} catch (Exception e) {
			src.sendError(Component.literal("[cscan] " + e.getMessage()));
			return 0;
		}
	}

	/** The clusters computed by the last `/cscan plan`, so `goto` can name one by number. */
	private static List<Plan.Cluster> lastPlan = new ArrayList<>();
	private static String lastPlanDesign = null;

	/**
	 * Where can I stand right now and place a lot, given what is in my pockets.
	 *
	 * <p>`next` answers "what is nearest" and `need` answers "what should I fetch". On a design of
	 * several thousand cells neither answers the one that decides whether an evening is a build
	 * session or an afternoon of walking.
	 */
	private static int planWork(CommandContext<FabricClientCommandSource> ctx) {
		FabricClientCommandSource src = ctx.getSource();
		String name = StringArgumentType.getString(ctx, "design");
		try {
			Minecraft mc = src.getClient();
			BlockPos me = mc.player.blockPosition();
			Work.Split sp = Work.split(mc.level, dir(src), name, me, 0);
			if (sp.todo().isEmpty()) { ok(src, sp.name() + " is complete in every loaded chunk"); return 1; }
			Map<String, Integer> carrying = Work.carrying(mc.player);
			Map<String, Storage.Container> index = Storage.load(dir(src));

			java.util.Set<Long> blocked = new java.util.HashSet<>();
			for (Work.Cell c : Work.floating(mc.level, sp.todo())) blocked.add(c.pos().asLong());
			java.util.Set<Long> sealed = new java.util.HashSet<>();
			for (Work.Cell c : Work.unreachable(mc.level, sp.todo())) sealed.add(c.pos().asLong());

			List<Plan.Cluster> cl = Plan.clusters(sp.todo(), carrying, blocked, sealed, me);
			lastPlan = cl;
			lastPlanDesign = sp.name();
			if (cl.isEmpty()) {
				// The useful failure: it is not that there is no work, it is that none of it is yours
				// to do standing here with this inventory.
				ok(src, sp.name() + ": " + sp.todo().size() + " left, but none of it is a block you are"
					+ " carrying — /cscan bom " + sp.name() + " for the shopping list");
				return 1;
			}
			int doable = cl.stream().mapToInt(Plan.Cluster::doable).sum();
			ok(src, sp.name() + ": " + doable + " of " + sp.todo().size()
				+ " placeable right now, in " + cl.size() + " spot(s)");
			for (int i = 0; i < cl.size(); i++) {
				Plan.Cluster c = cl.get(i);
				int d = (int) Math.sqrt(c.centre().distSqr(me));
				StringBuilder b = new StringBuilder();
				b.append("  ").append(i + 1).append(") ").append(c.doable())
					.append(" cells across ").append(Plan.extent(c)).append(" blocks, at ")
					.append(Wand.fmt(c.centre())).append("  ").append(d).append("m ")
					.append(Storage.direction(me, c.centre())).append(Hud.climb(me, c.centre()));
				if (c.shortBy() > 0) b.append("  (").append(c.shortBy()).append(" short of stock)");
				if (c.blocked() > 0) b.append("  (").append(c.blocked()).append(" need scaffolding)");
				if (c.sealed() > 0) b.append("  (").append(c.sealed()).append(" walled in)");
				ok(src, b.toString());
				ok(src, "       " + Plan.materialLine(c, carrying));
				// A shortfall with no address is half an answer, and the index already knows.
				for (String r : Plan.restock(c, carrying, index, me)) {
					ok(src, "       fetch " + r);
				}
			}
			ok(src, "  /cscan goto 1 to be walked there, or /cscan follow " + sp.name()
				+ " to be walked through all of it");
			return 1;
		} catch (Exception e) {
			src.sendError(Component.literal("[cscan] " + e.getMessage()));
			return 0;
		}
	}

	/**
	 * Navigate to the chest holding what the next spot is short of.
	 *
	 * <p>`follow` does this by itself; this is the same trip on demand, for when you want to top up
	 * before starting rather than be interrupted halfway.
	 */
	private static int fetch(CommandContext<FabricClientCommandSource> ctx) {
		FabricClientCommandSource src = ctx.getSource();
		String name = StringArgumentType.getString(ctx, "design");
		try {
			Minecraft mc = src.getClient();
			BlockPos me = mc.player.blockPosition();
			Work.Split sp = Work.split(mc.level, dir(src), name, me, 0);
			if (sp.todo().isEmpty()) { ok(src, sp.name() + " is complete in every loaded chunk"); return 1; }
			Map<String, Integer> carrying = Work.carrying(mc.player);
			Map<String, Storage.Container> index = Storage.load(dir(src));
			java.util.Set<Long> blocked = new java.util.HashSet<>();
			for (Work.Cell c : Work.floating(mc.level, sp.todo())) blocked.add(c.pos().asLong());

			// What is missing for the WHOLE remaining design, not just one spot: this is the trip you
			// make before you start, so the answer wants to cover the session.
			Map<String, Integer> want = Work.tally(sp.todo());
			// A synthetic cluster standing for the WHOLE remaining design:  costs the
			// session, not one spot, so no gate applies and every count is zero.
			Plan.Cluster all = new Plan.Cluster(me, sp.todo(), sp.todo(), want, 0, 0, 0);
			List<Plan.Restock> need = Plan.restockTargets(all, carrying, index, me);
			if (need.isEmpty()) {
				ok(src, "you are carrying everything " + sp.name() + " still needs");
				return 1;
			}
			ok(src, sp.name() + ": short of " + need.size() + " material(s)");
			for (Plan.Restock r : need) {
				if (r.where() == null) {
					ok(src, "  " + r.missing() + "x " + r.item() + " — not in any indexed chest");
					continue;
				}
				BlockPos at = r.where().pos();
				ok(src, "  " + r.missing() + "x " + r.item() + " — " + r.available() + " in "
					+ r.where().describe() + " " + (int) Math.sqrt(at.distSqr(me)) + "m "
					+ Storage.direction(me, at) + Hud.climb(me, at));
			}
			Plan.Restock first = need.stream().filter(r -> r.where() != null).findFirst().orElse(null);
			if (first != null) {
				BlockPos at = first.where().pos();
				Highlight.show("goto", List.of(at), 0xFFC000, 900);
				Hud.guide(at, first.missing() + "x " + first.item());
				if (Hud.watching() == null) Hud.watch(sp.name());
				ok(src, "  walking you to " + first.where().describe() + " — marked amber");
			}
			return 1;
		} catch (Exception e) {
			src.sendError(Component.literal("[cscan] " + e.getMessage()));
			return 0;
		}
	}

	/**
	 * Be walked through the whole design: the best spot, then the next when that one is done.
	 *
	 * <p>This is `plan` and `goto` without the typing between them, which on a design of several
	 * thousand cells is most of the typing.
	 */
	/**
	 * Work every tracked design, in order, until they are all done.
	 *
	 * <p>Starts on the first one with anything left rather than on the first one listed, or a
	 * finished design at the top of `sync.yaml` would end the run before it began.
	 */
	private static int followAll(CommandContext<FabricClientCommandSource> ctx) {
		FabricClientCommandSource src = ctx.getSource();
		Minecraft mc = src.getClient();
		String first = Hud.nextDesign(mc, null);
		if (first == null) {
			ok(src, "nothing tracked has any work left in the chunks I can see —"
				+ " `python -m mcbuild sync` records which designs are tracked");
			return 1;
		}
		Hud.follow(first);
		Hud.followAll(mc, true);
		if (!Autopilot.on()) {
			ok(src, "autofly is OFF — /cscan autofly on to be flown between them");
		}
		ok(src, "following every tracked design, starting with " + first
			+ ". It moves to the next as each one finishes. /cscan follow to stop.");
		return 1;
	}

	private static int follow(CommandContext<FabricClientCommandSource> ctx) {
		FabricClientCommandSource src = ctx.getSource();
		String name = StringArgumentType.getString(ctx, "design");
		try {
			Minecraft mc = src.getClient();
			// Fail here rather than silently on the first tick: a missing work.json should be an error
			// you read, not a HUD that never appears.
			Work.split(mc.level, dir(src), name, mc.player.blockPosition(), 0);
			Hud.follow(name);
			Hud.remember(src.getClient());
			// `follow` points; `autofly` moves. Saying so here is the difference between the loop
			// working and the loop appearing to do nothing, and it is the commonest way to start it
			// half-armed.
			if (!Autopilot.on()) {
				ok(src, "autofly is OFF — /cscan autofly on to be flown there, or follow the arrow"
					+ " yourself");
			}
			ok(src, "following " + name + " — the arrow moves to the next spot as each one finishes."
				+ " /cscan follow to stop.");
			return 1;
		} catch (Exception e) {
			src.sendError(Component.literal("[cscan] " + e.getMessage()));
			return 0;
		}
	}

	/**
	 * Where can I work, ANYWHERE - the best spot in each tracked design, ranked.
	 *
	 * <p>Reports per design rather than pooling every cell into one cluster list, because a cluster
	 * has to belong to a design for `follow` to have something to follow. "Where can I work" and
	 * "which job am I doing" are different questions and only the second one has an answer that fits
	 * on a HUD.
	 */
	private static int planAll(CommandContext<FabricClientCommandSource> ctx) {
		FabricClientCommandSource src = ctx.getSource();
		try {
			Minecraft mc = src.getClient();
			List<String> tracked = Designs.tracked(dir(src));
			if (tracked == null) {
				src.sendError(Component.literal("[cscan] no designs.json — run `python -m mcbuild sync`,"
					+ " or name one design: /cscan plan <design>"));
				return 0;
			}
			BlockPos me = mc.player.blockPosition();
			Map<String, Integer> carrying = Work.carrying(mc.player);
			record Best(String design, Plan.Cluster spot, int left) {}
			List<Best> best = new ArrayList<>();
			int complete = 0, unreadable = 0;
			for (String name : tracked) {
				try {
					Work.Split sp = Work.split(mc.level, dir(src), name, me, 0);
					if (sp.todo().isEmpty()) { complete++; continue; }
					java.util.Set<Long> blocked = new java.util.HashSet<>();
					for (Work.Cell c : Work.floating(mc.level, sp.todo())) blocked.add(c.pos().asLong());
					java.util.Set<Long> sealed = new java.util.HashSet<>();
					for (Work.Cell c : Work.unreachable(mc.level, sp.todo())) sealed.add(c.pos().asLong());
					List<Plan.Cluster> cl = Plan.clusters(sp.todo(), carrying, blocked, sealed, me);
					if (!cl.isEmpty()) best.add(new Best(sp.name(), cl.get(0), sp.todo().size()));
				} catch (Exception e) {
					unreadable++;              // no work.json yet: not an error worth stopping for
				}
			}
			if (best.isEmpty()) {
				ok(src, "nothing you are carrying the blocks for, across " + tracked.size()
					+ " tracked design(s)" + (complete > 0 ? " (" + complete + " complete)" : ""));
				return 1;
			}
			best.sort((a, b) -> Integer.compare(b.spot().doable(), a.spot().doable()));
			ok(src, "you can work on " + best.size() + " of " + tracked.size() + " tracked design(s)"
				+ (complete > 0 ? ", " + complete + " complete" : "")
				+ (unreadable > 0 ? ", " + unreadable + " with no work list" : ""));
			int n = 0;
			for (Best b : best) {
				if (n++ >= 6) break;
				int d = (int) Math.sqrt(b.spot().centre().distSqr(me));
				ok(src, "  " + b.spot().doable() + " placeable now in " + b.design()
					+ "  (" + b.left() + " left)  " + d + "m " + Storage.direction(me, b.spot().centre())
					+ Hud.climb(me, b.spot().centre()));
			}
			ok(src, "  /cscan follow <design> to be walked through one");
			return 1;
		} catch (Exception e) {
			src.sendError(Component.literal("[cscan] " + e.getMessage()));
			return 0;
		}
	}

	/** Lock the HUD arrow and the highlight onto one of the planned clusters. */
	private static int gotoCluster(CommandContext<FabricClientCommandSource> ctx) {
		FabricClientCommandSource src = ctx.getSource();
		int n = IntegerArgumentType.getInteger(ctx, "n");
		if (lastPlan.isEmpty()) {
			src.sendError(Component.literal("[cscan] no plan yet — /cscan plan <design>"));
			return 0;
		}
		if (n > lastPlan.size()) {
			src.sendError(Component.literal("[cscan] the plan has " + lastPlan.size() + " spot(s)"));
			return 0;
		}
		Plan.Cluster c = lastPlan.get(n - 1);
		Highlight.show("goto", Work.positions(c.cells(), 400), 0x40FF60, 900);
		Hud.guide(c.centre(), c.doable() + " cells");
		// The HUD counts down the whole design while you are there, so the arrow is not the only
		// thing telling you when you are done.
		if (Hud.watching() == null && lastPlanDesign != null) Hud.watch(lastPlanDesign);
		ok(src, "walking you to spot " + n + ": " + c.doable() + " cells at " + Wand.fmt(c.centre())
			+ " — marked green, arrow on the HUD. /cscan goto to stop.");
		return 1;
	}

	/**
	 * Standable cells the light does not reach. The one question only the client can answer: the
	 * desktop has always approximated it by distance to a torch, and light does not go through walls.
	 */
	private static int dark(CommandContext<FabricClientCommandSource> ctx, int radius) {
		FabricClientCommandSource src = ctx.getSource();
		Minecraft mc = src.getClient();
		if (mc.level == null || mc.player == null) { src.sendError(Component.literal("[cscan] no world")); return 0; }
		try {
			BlockPos me = mc.player.blockPosition();
			Light.Report r = Light.scan(mc.level, me, radius, 400);
			if (r.checked() == 0) {
				ok(src, "nothing standable within " + radius + " — move somewhere with a floor");
				return 1;
			}
			if (r.dim() == 0) {
				Highlight.clear("dark");
				ok(src, "all " + r.checked() + " standable cells within " + radius + " are at light "
					+ Light.DIM + " or better");
				return 1;
			}
			Highlight.show("dark", r.spots().stream().map(Light.Spot::pos).toList(), 0xFF3030, 300);
			ok(src, r.dim() + " of " + r.checked() + " standable cells are under light " + Light.DIM
				+ " (" + Math.round(100f * r.dim() / r.checked()) + "%), of which "
				+ r.spawnable() + " are SPAWNABLE — marked red");
			List<BlockPos> cl = Light.clusters(r.spots(), 5);
			for (BlockPos c : cl) {
				ok(src, "  cluster near " + Wand.fmt(c) + " (" + (int) Math.sqrt(c.distSqr(me)) + "m "
					+ Storage.direction(me, c) + ")");
			}
			// Sky light is reported, not judged: an unlit lawn is bright by day and this is not the
			// same problem as an unlit room.
			long outdoors = r.spots().stream().filter(sp -> sp.sky() > 8).count();
			if (outdoors > 0) {
				ok(src, "  " + outdoors + " of the marked cells are open to the sky — dark only at night");
			}
			return 1;
		} catch (Exception e) {
			src.sendError(Component.literal("[cscan] " + e.getMessage()));
			return 0;
		}
	}

	/** The whole design's materials in shulkers, for packing before a trip. */
	private static int bom(CommandContext<FabricClientCommandSource> ctx) {
		FabricClientCommandSource src = ctx.getSource();
		String name = StringArgumentType.getString(ctx, "design");
		try {
			Minecraft mc = src.getClient();
			// radius 0 = the WHOLE design, not what is in reach: `need` already answers the other one.
			Work.Split sp = Work.split(mc.level, dir(src), name, mc.player.blockPosition(), 0);
			if (sp.todo().isEmpty()) { ok(src, sp.name() + " is complete in every loaded chunk"); return 1; }
			Map<String, Integer> want = Work.tally(sp.todo());
			Map<String, Integer> have = Work.carrying(mc.player);
			int stacks = 0;
			ok(src, sp.name() + ": " + sp.todo().size() + " block(s) left of " + sp.total());
			var rows = new ArrayList<>(want.entrySet());
			rows.sort((a, b) -> Integer.compare(b.getValue(), a.getValue()));
			for (var e : rows) {
				int n = e.getValue();
				int st = (n + 63) / 64;
				stacks += st;
				int onMe = have.getOrDefault(e.getKey(), 0);
				ok(src, "  " + n + "x " + e.getKey() + "  (" + st + " stack" + (st == 1 ? "" : "s")
					+ (onMe > 0 ? ", carrying " + onMe : "") + ")");
			}
			ok(src, "  total " + stacks + " stacks = " + String.format("%.1f", stacks / 27.0) + " shulkers");
			if (!sp.wrong().isEmpty()) {
				ok(src, "  " + sp.wrong().size() + " cells deviate — /cscan check " + sp.name());
			}
			return 1;
		} catch (Exception e) {
			src.sendError(Component.literal("[cscan] " + e.getMessage()));
			return 0;
		}
	}

	/** One fill shape, as a subcommand. Eleven of these by hand is eleven chances to paste wrong. */
	private static com.mojang.brigadier.builder.LiteralArgumentBuilder<FabricClientCommandSource>
		shapeArg(String word, Fill.Mode mode) {
		return literal(word).then(argument("name", StringArgumentType.greedyString())
			.executes(ctx -> fill(ctx, StringArgumentType.getString(ctx, "name"), mode, null)));
	}

	/**
	 * Set the selection to a cube of `radius` centred on the block you are looking at.
	 *
	 * <p>This is why no shape needs its own radius argument. `/cscan around 8` then
	 * `/cscan fill sphere dome` is a sphere of radius 8, and the same two commands compose with
	 * every other mode, with `copy`, and with `replace`. Giving each shape a radius parameter would
	 * have been eleven ways to say the same thing.
	 */
	private static int around(CommandContext<FabricClientCommandSource> ctx) {
		FabricClientCommandSource src = ctx.getSource();
		Minecraft mc = src.getClient();
		if (mc.level == null || mc.player == null) { src.sendError(Component.literal("[cscan] no world")); return 0; }
		int r = IntegerArgumentType.getInteger(ctx, "radius");
		BlockPos c = targeted(mc);
		long vol = (2L * r + 1) * (2L * r + 1) * (2L * r + 1);
		if (vol > MAX_FILL_CELLS) {
			src.sendError(Component.literal("[cscan] radius " + r + " is " + vol + " cells, cap is "
				+ MAX_FILL_CELLS));
			return 0;
		}
		Wand.setBox(c.offset(-r, -r, -r), c.offset(r, r, r), mc.level.dimension().identifier().toString());
		ok(src, "selection set to " + (2 * r + 1) + "\u00b3 around " + Wand.fmt(c)
			+ " — /cscan fill sphere|ball|dome|cylinder|tube|disc|ring <name>");
		return 1;
	}

	private static int clips(CommandContext<FabricClientCommandSource> ctx) {
		FabricClientCommandSource src = ctx.getSource();
		try (var st = java.nio.file.Files.list(dir(src))) {
			List<String> names = new ArrayList<>();
			st.map(p -> p.getFileName().toString())
				.filter(n -> n.startsWith(CLIP_PREFIX) && n.endsWith(".litematic"))
				.forEach(n -> names.add(n.substring(CLIP_PREFIX.length(), n.length() - ".litematic".length())));
			names.sort(String::compareToIgnoreCase);
			if (names.isEmpty()) ok(src, "no clips yet — mark a box and /cscan copy <name>");
			else ok(src, names.size() + " clip(s): " + String.join(", ", names));
			return 1;
		} catch (Exception e) {
			src.sendError(Component.literal("[cscan] " + e.getMessage()));
			return 0;
		}
	}

	/**
	 * The chest move, in three lines: how much is left, what stays put, and whether the hall can
	 * still take it. Nothing is moved by the mod - this plans and points.
	 */
	private static int moveStatus(CommandContext<FabricClientCommandSource> ctx) {
		FabricClientCommandSource src = ctx.getSource();
		Minecraft mc = src.getClient();
		if (mc.level == null || mc.player == null) { src.sendError(Component.literal("[cscan] no world")); return 0; }
		try {
			Move.Plan plan = Move.plan(Move.of(mc.level), dir(src), mc.player.blockPosition());
			if (plan.legs().isEmpty()) {
				ok(src, plan.slotsFree() == 0
					? "the hall is full — nothing can be moved until a slot frees up"
					: "nothing left to move (" + plan.stayed() + " stay with their machines)");
				return 1;
			}
			ok(src, plan.legs().size() + " container(s) to move, " + plan.slotsFree() + " slot(s) free, "
				+ plan.stayed() + " staying with their machines");
			int n = 0;
			for (Move.Leg leg : plan.legs()) {
				if (n++ >= 5) break;
				ok(src, "  " + Wand.fmt(leg.from().pos()) + " (" + Move.contents(leg.from().container()) + ")"
					+ " -> " + leg.to().label() + (leg.overflow() ? " [OVERFLOW]" : ""));
			}
			if (plan.legs().size() > 5) ok(src, "  ... " + (plan.legs().size() - 5) + " more — /cscan move next");
			for (String c : plan.unmatchedCategories()) {
				// A category with no wall is a real gap in the hall's labels, not a rounding error.
				src.sendError(Component.literal("[cscan] no bank is labelled \"" + c
					+ "\" — those are going to whatever slot is free"));
			}
			return 1;
		} catch (Exception e) {
			src.sendError(Component.literal("[cscan] " + e.getMessage()));
			return 0;
		}
	}

	/** Mark the nearest chest amber and its destination green, and say what to carry. */
	private static int moveNext(CommandContext<FabricClientCommandSource> ctx) {
		FabricClientCommandSource src = ctx.getSource();
		Minecraft mc = src.getClient();
		if (mc.level == null || mc.player == null) { src.sendError(Component.literal("[cscan] no world")); return 0; }
		try {
			BlockPos me = mc.player.blockPosition();
			Move.Plan plan = Move.plan(Move.of(mc.level), dir(src), me);
			if (plan.legs().isEmpty()) {
				Move.clearDraw();
				ok(src, "nothing left to move");
				return 1;
			}
			Move.Leg leg = plan.legs().get(0);
			Move.draw(leg);
			ok(src, "FROM " + Wand.fmt(leg.from().pos()) + " ("
				+ (int) Math.sqrt(leg.from().pos().distSqr(me)) + "m "
				+ Storage.direction(me, leg.from().pos()) + ", marked amber) — "
				+ Move.contents(leg.from().container()));
			ok(src, "TO   " + Wand.fmt(leg.to().pos()) + " on the "
				+ (leg.to().bank().isEmpty() ? "hall" : leg.to().bank()) + " bank"
				+ (leg.to().label().isEmpty() ? "" : " (" + leg.to().label() + ")")
				+ ", marked green" + (leg.overflow() ? " — OVERFLOW, no bank matches this" : ""));
			ok(src, "  when it is empty: /cscan move done");
			return 1;
		} catch (Exception e) {
			src.sendError(Component.literal("[cscan] " + e.getMessage()));
			return 0;
		}
	}

	/**
	 * Mark the nearest planned source as emptied. Reopening it would do the same thing by itself -
	 * the index would record it empty and it would drop out - but that means a second trip, and this
	 * job is entirely trips.
	 */
	private static int moveDone(CommandContext<FabricClientCommandSource> ctx) {
		FabricClientCommandSource src = ctx.getSource();
		Minecraft mc = src.getClient();
		if (mc.level == null || mc.player == null) { src.sendError(Component.literal("[cscan] no world")); return 0; }
		try {
			BlockPos me = mc.player.blockPosition();
			Move.Plan plan = Move.plan(Move.of(mc.level), dir(src), me);
			if (plan.legs().isEmpty()) { ok(src, "nothing left to move"); return 1; }
			Move.Leg leg = plan.legs().get(0);
			double d = Math.sqrt(leg.from().pos().distSqr(me));
			if (d > 12) {
				src.sendError(Component.literal("[cscan] nearest planned chest is " + (int) d
					+ "m away — walk to it first, or /cscan move next to see which"));
				return 0;
			}
			Move.markDone(dir(src), leg.from().container().key());
			Move.clearDraw();
			ok(src, "marked " + Wand.fmt(leg.from().pos()) + " moved — " + (plan.legs().size() - 1) + " to go");
			return 1;
		} catch (Exception e) {
			src.sendError(Component.literal("[cscan] " + e.getMessage()));
			return 0;
		}
	}

	private static int moveReset(CommandContext<FabricClientCommandSource> ctx) {
		FabricClientCommandSource src = ctx.getSource();
		try {
			Move.reset(dir(src));
			Move.clearDraw();
			ok(src, "move progress cleared");
			return 1;
		} catch (Exception e) {
			src.sendError(Component.literal("[cscan] " + e.getMessage()));
			return 0;
		}
	}

	/**
	 * The panic button: stop everything in flight.
	 *
	 * <p>An automation you cannot stop in one word is one you have to fight.
	 */
	private static int stopAll(CommandContext<FabricClientCommandSource> ctx) {
		FabricClientCommandSource src = ctx.getSource();
		Minecraft mc = src.getClient();
		String report = Hud.following() ? "  " + Hud.sessionReport() : "";
		Withdraw.cancel();
		Autopilot.halt(mc);
		Hud.off();
		Highlight.clear("goto");
		Highlight.clear("next");
		Highlight.clear("scaffold");
		// STOP MEANS STOP, INCLUDING AFTER A RELOG. Leaving the resume note behind would have the
		// loop start itself again the next time you joined, which is the one behaviour a panic
		// button must not have.
		try {
			Session.clear(dir(src));
		} catch (Exception ignored) {
		}
		ok(src, "stopped: withdrawal, autofly, follow and highlights all off." + report);
		return 1;
	}

	/**
	 * Open the container you are looking at and shift-click stacks out of it.
	 *
	 * <p>With no argument it empties the whole thing — the chest move's source step. With an item and
	 * a count it takes only that, which is what the build loop's fetch phase wants.
	 */
	private static int take(CommandContext<FabricClientCommandSource> ctx, String item, int count) {
		FabricClientCommandSource src = ctx.getSource();
		Minecraft mc = src.getClient();
		if (mc.level == null || mc.player == null) { src.sendError(Component.literal("[cscan] no world")); return 0; }
		BlockPos at = targeted(mc);
		String n = BuiltInRegistries.BLOCK.getKey(mc.level.getBlockState(at).getBlock()).getPath();
		if (!Storage.stores(n)) {
			src.sendError(Component.literal("[cscan] look at a container — that is " + n));
			return 0;
		}
		if (Math.sqrt(mc.player.blockPosition().distSqr(at)) > Withdraw.REACH) {
			src.sendError(Component.literal("[cscan] too far — get within " + (int) Withdraw.REACH));
			return 0;
		}
		Withdraw.begin(at, item, count);
		ok(src, item == null ? "emptying " + n + " at " + Wand.fmt(at)
			: "taking " + count + "x " + item + " from " + n);
		return 1;
	}

	/**
	 * What is worth consolidating, and where each pile should end up.
	 *
	 * <p>With no argument it reports the plan. With a number it locks the guidance onto that job's
	 * FIRST source chest, so `autofly` walks you round them.
	 */
	private static int tidy(CommandContext<FabricClientCommandSource> ctx, int pick) {
		FabricClientCommandSource src = ctx.getSource();
		Minecraft mc = src.getClient();
		if (mc.level == null || mc.player == null) { src.sendError(Component.literal("[cscan] no world")); return 0; }
		try {
			BlockPos me = mc.player.blockPosition();
			Map<String, Storage.Container> index = Storage.load(dir(src));
			// Records the world has disproved would send you to a chest that is not there.
			index.values().removeIf(c -> !Storage.stillThere(mc.level, c));
			List<Tidy.Job> jobs = Tidy.plan(index, me);
			if (jobs.isEmpty()) {
				ok(src, "nothing worth consolidating — every pile of " + Tidy.MIN_TOTAL
					+ "+ already lives in one container");
				return 1;
			}
			if (pick > 0) {
				if (pick > jobs.size()) {
					src.sendError(Component.literal("[cscan] there are " + jobs.size() + " job(s)"));
					return 0;
				}
				Tidy.Job j = jobs.get(pick - 1);
				Storage.Container first = j.sources().get(0);
				Highlight.show("goto", List.of(first.pos(), j.home().pos()), 0xFFC000, 900);
				Hud.guide(first.pos(), "take " + j.item());
				ok(src, "job " + pick + ": " + Tidy.describe(j, me));
				ok(src, "  nearest source " + first.describe() + " marked — home marked too."
					+ " /cscan autofly on to be flown there.");
				return 1;
			}
			int slots = jobs.stream().mapToInt(Tidy.Job::slotsFreed).sum();
			ok(src, jobs.size() + " pile(s) worth consolidating, " + slots + " slot(s) to reclaim, "
				+ Tidy.containersFreed(jobs, index) + " container(s) would empty completely");
			int n = 0;
			for (Tidy.Job j : jobs) {
				if (n++ >= 8) break;
				ok(src, "  " + n + ") " + Tidy.describe(j, me));
			}
			if (jobs.size() > 8) ok(src, "  ... " + (jobs.size() - 8) + " more");
			ok(src, "  /cscan tidy <n> to be walked to one");
			return 1;
		} catch (Exception e) {
			src.sendError(Component.literal("[cscan] " + e.getMessage()));
			return 0;
		}
	}

	/** Drop storage entries filed against something that is not a container. See Storage.prune. */
	private static int prune(CommandContext<FabricClientCommandSource> ctx) {
		FabricClientCommandSource src = ctx.getSource();
		try {
			Minecraft mc = src.getClient();
			int gone = Storage.prune(dir(src), mc.level);
			ok(src, gone == 0 ? "storage index is clean in every loaded chunk"
				: "dropped " + gone + " entries — either never a container, or the chest is gone."
					+ " Reopen a container to re-index it.");
			ok(src, "  only LOADED chunks were checked: an unloaded one is not evidence the chest"
				+ " went. Fly the island and run it again to catch the rest.");
			return 1;
		} catch (Exception e) {
			src.sendError(Component.literal("[cscan] " + e.getMessage()));
			return 0;
		}
	}

	static String blockName(BlockState state) {
		return BuiltInRegistries.BLOCK.getKey(state.getBlock()).toString();
	}

	private static int place(CommandContext<FabricClientCommandSource> ctx, String which) {
		FabricClientCommandSource src = ctx.getSource();
		if (!Litematica.present()) {
			src.sendError(Component.literal("[cscan] Litematica is not loaded"));
			return 0;
		}
		try {
			// BARE `place` MEANS THE DESIGNS YOU TRACK, not the 61 in the folder - that shelf holds
			// scratch animals parked at the origin lock, claiming void they have no right to.
			List<String> names;
			if (which != null) {
				names = List.of(which);
			} else {
				List<String> t = Designs.tracked(dir(src));
				if (t != null) {
					names = t;
					ok(src, "placing the " + t.size() + " design(s) sync.yaml tracks");
				} else {
					names = Designs.list(dir(src));
					src.sendError(Component.literal("[cscan] no designs.json — placing ALL "
						+ names.size() + ". Run `python -m mcbuild sync` to record which you track."));
				}
			}
			int n = 0;
			for (String name : names) {
				try {
					Designs.Design d = Designs.load(dir(src), name);
					Litematica.place(d.litematic(), d.origin(), d.name());
					ok(src, "placed " + d.name() + " at " + d.origin().getX() + " " + d.origin().getY() + " " + d.origin().getZ());
					n++;
				} catch (Exception e) {
					if (which != null) throw e;                      // explicit request: report it
					LOG.debug("skipped {}: {}", name, e.toString());
				}
			}
			if (n == 0) src.sendError(Component.literal("[cscan] nothing placed (no designs with a .scan.json?)"));
			else ok(src, n + " placement(s) added — origins come from each .scan.json, rotation/mirror NONE");
			return 1;
		} catch (Exception e) {
			src.sendError(Component.literal("[cscan] place failed: " + e.getMessage()));
			return 0;
		}
	}

	/** What to carry: materials for the unbuilt cells in reach, and which chest holds them. */
	private static int need(CommandContext<FabricClientCommandSource> ctx, int radius) {
		FabricClientCommandSource src = ctx.getSource();
		String name = StringArgumentType.getString(ctx, "design");
		try {
			Minecraft mc = src.getClient();
			BlockPos me = mc.player.blockPosition();
			Work.Split sp = Work.split(mc.level, dir(src), name, me, radius);
			if (sp.todo().isEmpty()) {
				ok(src, sp.name() + ": nothing left within " + radius + " blocks (" + sp.built() + " built here"
					+ (sp.wrong().isEmpty() ? ")" : ", " + sp.wrong().size() + " deviate - /cscan check " + name + ")"));
				return 1;
			}
			Map<String, Storage.Container> all = Storage.load(dir(src));
			Map<String, Integer> have = Work.carrying(mc.player);
			ok(src, sp.name() + ": " + sp.todo().size() + " block(s) left within " + radius);
			int covered = 0;
			for (var e : Work.tally(sp.todo()).entrySet()) {
				int want = e.getValue();
				int onMe = have.getOrDefault(e.getKey(), 0);
				if (onMe >= want) {
					// Nothing to fetch. Saying so is the whole point: this used to send you to a
					// chest across the island for something already in your hotbar.
					ok(src, "  " + want + "x " + e.getKey() + " - CARRYING " + onMe);
					covered++;
					continue;
				}
				int shortBy = want - onMe;
				List<Storage.Hit> hits = Storage.find(all, e.getKey(), me, mc.level);
				String where = " - not in any indexed chest";
				if (!hits.isEmpty()) {
					Storage.Hit h = hits.get(0);
					where = " - " + h.count() + " in " + h.container().describe() + " "
						+ (int) h.distance() + "m " + Storage.direction(me, h.container().pos());
				}
				ok(src, "  " + want + "x " + e.getKey()
					+ (onMe > 0 ? " (carrying " + onMe + ", short " + shortBy + ")" : "") + where);
			}
			if (covered > 0) ok(src, "  " + covered + " of those you already have on you");
			return 1;
		} catch (Exception e) {
			src.sendError(Component.literal("[cscan] " + e.getMessage()));
			return 0;
		}
	}

	/** The next few cells to place, marked green, lowest first so you never build past your reach. */
	private static int next(CommandContext<FabricClientCommandSource> ctx, int n) {
		FabricClientCommandSource src = ctx.getSource();
		String name = StringArgumentType.getString(ctx, "design");
		try {
			Minecraft mc = src.getClient();
			BlockPos me = mc.player.blockPosition();
			Work.Split sp = Work.split(mc.level, dir(src), name, me, 0);
			if (sp.todo().isEmpty()) { ok(src, sp.name() + " is complete in every loaded chunk"); return 1; }
			List<Work.Cell> take = sp.todo().subList(0, Math.min(n, sp.todo().size()));
			Highlight.show("next", Work.positions(take, n), 0x40FF60, 180);
			Work.Cell first = take.get(0);
			ok(src, sp.name() + ": " + sp.todo().size() + " left, next " + take.size() + " marked green");
			ok(src, "  start at " + first.pos().getX() + " " + first.pos().getY() + " " + first.pos().getZ()
				+ " (" + first.block() + ", " + (int) Math.sqrt(first.pos().distSqr(me)) + "m "
				+ Storage.direction(me, first.pos()) + ")");
			for (var e : Work.tally(take).entrySet()) ok(src, "  " + e.getValue() + "x " + e.getKey());
			// The one thing you cannot discover by looking at the marks: a cell with no face to
			// click. Cheap to check over the few cells just handed out.
			List<Work.Cell> air = Work.floating(mc.level, take);
			if (!air.isEmpty()) {
				ok(src, "  " + air.size() + " of these have nothing to place against"
					+ " — /cscan scaffold " + sp.name());
			}
			return 1;
		} catch (Exception e) {
			src.sendError(Component.literal("[cscan] " + e.getMessage()));
			return 0;
		}
	}

	/** Cells where the world holds something other than what the design wants. */
	private static int check(CommandContext<FabricClientCommandSource> ctx) {
		FabricClientCommandSource src = ctx.getSource();
		String name = StringArgumentType.getString(ctx, "design");
		try {
			Minecraft mc = src.getClient();
			Work.Split sp = Work.split(mc.level, dir(src), name, mc.player.blockPosition(), 0);
			int pct = sp.total() == 0 ? 0 : Math.round(100f * sp.built() / sp.total());
			ok(src, sp.name() + ": " + sp.built() + "/" + sp.total() + " built (" + pct + "%) in loaded chunks, "
				+ sp.todo().size() + " to place, " + sp.wrong().size() + " deviating");
			if (sp.wrong().isEmpty()) return 1;
			Highlight.show("check", Work.positions(sp.wrong(), 200), 0xFFC000, 180);
			for (Work.Cell c : sp.wrong().subList(0, Math.min(8, sp.wrong().size()))) {
				var st = mc.level.getBlockState(c.pos());
				String have = BuiltInRegistries.BLOCK.getKey(st.getBlock()).getPath();
				// Same block, wrong way round, is the case the old name-only check could not see -
				// so say so in those words rather than printing the name twice.
				if (have.equals(c.item())) have += " but oriented differently";
				ok(src, "  " + c.pos().getX() + " " + c.pos().getY() + " " + c.pos().getZ()
					+ ": want " + c.block() + ", have " + have);
			}
			ok(src, "  marked amber" + (sp.wrong().size() > 8 ? " (" + (sp.wrong().size() - 8) + " more)" : ""));
			return 1;
		} catch (Exception e) {
			src.sendError(Component.literal("[cscan] " + e.getMessage()));
			return 0;
		}
	}

	private static int mark(CommandContext<FabricClientCommandSource> ctx) {
		FabricClientCommandSource src = ctx.getSource();
		String label = StringArgumentType.getString(ctx, "label");
		try {
			Minecraft mc = src.getClient();
			BlockPos p = targeted(mc);
			Markers.put(dir(src), label, p, mc.level.dimension().identifier().toString());
			ok(src, "marked '" + label + "' at " + p.getX() + " " + p.getY() + " " + p.getZ());
			Highlight.show("mark", List.of(p), 0x55FF55, 10);
			return 1;
		} catch (Exception e) {
			src.sendError(Component.literal("[cscan] mark failed: " + e.getMessage()));
			return 0;
		}
	}

	private static int marks(CommandContext<FabricClientCommandSource> ctx) {
		FabricClientCommandSource src = ctx.getSource();
		try {
			List<Markers.Marker> all = Markers.load(dir(src));
			if (all.isEmpty()) { ok(src, "no markers yet — /cscan mark <label> while looking at a block"); return 1; }
			BlockPos me = src.getClient().player.blockPosition();
			List<BlockPos> pts = new ArrayList<>();
			for (Markers.Marker m : all) {
				ok(src, String.format("%-18s %d %d %d  (%.0fm)", m.label(), m.x(), m.y(), m.z(), m.distance(me)));
				pts.add(new BlockPos(m.x(), m.y(), m.z()));
			}
			Highlight.show("marks", pts, 0x55FF55, 20);
			return 1;
		} catch (Exception e) {
			src.sendError(Component.literal("[cscan] " + e.getMessage()));
			return 0;
		}
	}

	private static int unmark(CommandContext<FabricClientCommandSource> ctx) {
		FabricClientCommandSource src = ctx.getSource();
		String label = StringArgumentType.getString(ctx, "label");
		try {
			ok(src, Markers.remove(dir(src), label) ? "removed '" + label + "'" : "no marker '" + label + "'");
			return 1;
		} catch (Exception e) {
			src.sendError(Component.literal("[cscan] " + e.getMessage()));
			return 0;
		}
	}

	private static int dig(CommandContext<FabricClientCommandSource> ctx) {
		FabricClientCommandSource src = ctx.getSource();
		String name = StringArgumentType.getString(ctx, "design");
		try {
			Designs.Design d = Designs.load(dir(src), name);
			if (d.dig().isEmpty()) {
				ok(src, d.name() + " has no dig list - nothing needs breaking for it");
				return 1;
			}
			Highlight.show("dig", d.dig(), 0xFF4040, 120);
			// Say where they ARE, not just how many. Particles are easy to miss, easy to switch off,
			// and useless past the highlight radius - without this a far-away or invisible dig list
			// looks exactly like a broken command.
			BlockPos me = src.getClient().player.blockPosition();
			BlockPos near = d.dig().get(0);
			for (BlockPos q : d.dig()) {
				if (q.distSqr(me) < near.distSqr(me)) near = q;
			}
			int dist = (int) Math.sqrt(near.distSqr(me));
			ok(src, d.name() + ": " + d.dig().size() + " block(s) to clear, marked red for 2 minutes");
			ok(src, "  nearest is " + near.getX() + " " + near.getY() + " " + near.getZ()
				+ " - " + dist + "m " + Storage.direction(me, near));
			if (dist > Highlight.RADIUS) {
				ok(src, "  you are past the " + Highlight.RADIUS + "m highlight range, so nothing will show yet");
			}
			return 1;
		} catch (Exception e) {
			src.sendError(Component.literal("[cscan] " + e.getMessage()));
			return 0;
		}
	}

	private static int find(CommandContext<FabricClientCommandSource> ctx) {
		FabricClientCommandSource src = ctx.getSource();
		String query = StringArgumentType.getString(ctx, "query");
		try {
			Minecraft mc = src.getClient();
			Map<String, Storage.Container> all = Storage.load(dir(src));
			BlockPos me = mc.player.blockPosition();
			List<Storage.Hit> hits = Storage.find(all, query, me);
			if (hits.isEmpty()) { ok(src, "no indexed container holds '" + query + "' (" + all.size() + " containers indexed)"); return 1; }
			List<BlockPos> pts = new ArrayList<>();
			int shown = 0;
			for (Storage.Hit h : hits) {
				if (shown++ >= 8) break;
				Storage.Container c = h.container();
				ok(src, String.format("%s  %dx %s  at %d %d %d  (%.0fm %s)", c.describe(), h.count(),
					h.item().replace("minecraft:", ""), c.x, c.y, c.z, h.distance(), Storage.direction(me, c.pos())));
				pts.add(c.pos());
			}
			if (hits.size() > shown) ok(src, "... " + (hits.size() - shown) + " more");
			Highlight.show("find", pts, 0x40A0FF, 60);
			ok(src, "marked blue for 60s");
			return 1;
		} catch (Exception e) {
			src.sendError(Component.literal("[cscan] " + e.getMessage()));
			return 0;
		}
	}

	private static int chests(CommandContext<FabricClientCommandSource> ctx) {
		FabricClientCommandSource src = ctx.getSource();
		try {
			Map<String, Storage.Container> all = Storage.load(dir(src));
			int items = all.values().stream().mapToInt(Storage.Container::total).sum();
			long stale = all.values().stream().filter(c -> c.fullness() < 0).count();
			ok(src, all.size() + " containers indexed, " + items + " items total. Open a container to index it; /cscan find <item> to locate one.");
			BlockPos me = src.getClient().player.blockPosition();
			List<Storage.Container> full = new ArrayList<>(all.values());
			full.removeIf(c -> c.fullness() < 80);
			full.sort((a, b) -> Integer.compare(b.fullness(), a.fullness()));
			for (Storage.Container c : full.subList(0, Math.min(6, full.size()))) {
				ok(src, "  " + c.fullness() + "% full: " + c.describe() + " " + (int) Math.sqrt(c.pos().distSqr(me))
					+ "m " + Storage.direction(me, c.pos()));
			}
			if (stale > 0) ok(src, "  " + stale + " indexed before fullness was recorded - reopen them to fill it in");
			return 1;
		} catch (Exception e) {
			src.sendError(Component.literal("[cscan] " + e.getMessage()));
			return 0;
		}
	}

	private static int label(CommandContext<FabricClientCommandSource> ctx) {
		FabricClientCommandSource src = ctx.getSource();
		String text = StringArgumentType.getString(ctx, "text");
		try {
			Minecraft mc = src.getClient();
			String desc = ContainerWatcher.label(mc, targeted(mc), text);
			if (desc == null) { src.sendError(Component.literal("[cscan] that block is not indexed yet — open it once")); return 0; }
			ok(src, "labelled " + desc);
			return 1;
		} catch (Exception e) {
			src.sendError(Component.literal("[cscan] " + e.getMessage()));
			return 0;
		}
	}

	private static int auto(CommandContext<FabricClientCommandSource> ctx) {
		FabricClientCommandSource src = ctx.getSource();
		AutoScan.start(StringArgumentType.getString(ctx, "name"), IntegerArgumentType.getInteger(ctx, "minutes"), DEFAULT_RADIUS);
		ok(src, AutoScan.status());
		return 1;
	}

	private static int selection(CommandContext<FabricClientCommandSource> ctx) {
		FabricClientCommandSource src = ctx.getSource();
		try {
			ScanResult r = ScanRunner.scanSelection(src.getClient(), StringArgumentType.getString(ctx, "name"));
			for (String line : r.summaryLines()) ok(src, line);
			return 1;
		} catch (ScanException e) {
			src.sendError(Component.literal("[cscan] " + e.getMessage()));
			return 0;
		} catch (Exception e) {
			LOG.error("selection scan failed", e);
			src.sendError(Component.literal("[cscan] failed: " + e));
			return 0;
		}
	}

	private static int run(CommandContext<FabricClientCommandSource> ctx, int radius, boolean chunkAligned) {
		String name = StringArgumentType.getString(ctx, "name");
		FabricClientCommandSource src = ctx.getSource();
		try {
			ScanResult result = ScanRunner.scan(src.getClient(), name, radius, chunkAligned);
			for (String line : result.summaryLines()) {
				src.sendFeedback(Component.literal("[cscan] " + line));
			}
			return 1;
		} catch (ScanException e) {
			src.sendError(Component.literal("[cscan] " + e.getMessage()));
			return 0;
		} catch (Exception e) {
			LOG.error("scan failed", e);
			src.sendError(Component.literal("[cscan] failed: " + e));
			return 0;
		}
	}
}
