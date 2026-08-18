package dev.jack.chunkscan;

import com.mojang.brigadier.arguments.IntegerArgumentType;
import com.mojang.brigadier.arguments.StringArgumentType;
import com.mojang.brigadier.context.CommandContext;
import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.fabric.api.client.command.v2.ClientCommandRegistrationCallback;
import net.fabricmc.fabric.api.client.command.v2.FabricClientCommandSource;
import net.minecraft.client.Minecraft;
import net.minecraft.core.BlockPos;
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

	@Override
	public void onInitializeClient() {
		ContainerWatcher.register();
		Highlight.register();
		AutoScan.register();
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
		LOG.info("chunkscan ready: scan | place | mark | dig | find | chests | label | auto | sel");
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

	private static int place(CommandContext<FabricClientCommandSource> ctx, String which) {
		FabricClientCommandSource src = ctx.getSource();
		if (!Litematica.present()) {
			src.sendError(Component.literal("[cscan] Litematica is not loaded"));
			return 0;
		}
		try {
			List<String> names = which != null ? List.of(which) : Designs.list(dir(src));
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

	private static int mark(CommandContext<FabricClientCommandSource> ctx) {
		FabricClientCommandSource src = ctx.getSource();
		String label = StringArgumentType.getString(ctx, "label");
		try {
			Minecraft mc = src.getClient();
			BlockPos p = targeted(mc);
			Markers.put(dir(src), label, p, mc.level.dimension().identifier().toString());
			ok(src, "marked '" + label + "' at " + p.getX() + " " + p.getY() + " " + p.getZ());
			Highlight.show(List.of(p), 0x55FF55, 10);
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
			Highlight.show(pts, 0x55FF55, 20);
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
			if (d.dig().isEmpty()) { ok(src, d.name() + " has no dig list"); return 1; }
			Highlight.show(d.dig(), 0xFF4040, 120);
			ok(src, d.name() + ": " + d.dig().size() + " block(s) to clear, marked red for 2 minutes");
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
			Highlight.show(pts, 0x40A0FF, 60);
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
			ok(src, all.size() + " containers indexed, " + items + " items total. Open a container to index it; /cscan find <item> to locate one.");
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
