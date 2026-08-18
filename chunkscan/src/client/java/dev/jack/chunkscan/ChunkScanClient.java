package dev.jack.chunkscan;

import com.mojang.brigadier.arguments.IntegerArgumentType;
import com.mojang.brigadier.arguments.StringArgumentType;
import com.mojang.brigadier.context.CommandContext;
import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.fabric.api.client.command.v2.ClientCommandRegistrationCallback;
import net.fabricmc.fabric.api.client.command.v2.FabricClientCommandSource;
import net.minecraft.network.chat.Component;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

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
		ClientCommandRegistrationCallback.EVENT.register((dispatcher, registryAccess) ->
			dispatcher.register(literal("cscan")
				.then(literal("chunks")
					.then(argument("name", StringArgumentType.word())
						.executes(ctx -> run(ctx, DEFAULT_RADIUS, true))
						.then(argument("radius", IntegerArgumentType.integer(0, MAX_RADIUS))
							.executes(ctx -> run(ctx, IntegerArgumentType.getInteger(ctx, "radius"), true)))))
				.then(argument("name", StringArgumentType.word())
					.executes(ctx -> run(ctx, DEFAULT_RADIUS, false))
					.then(argument("radius", IntegerArgumentType.integer(0, MAX_RADIUS))
						.executes(ctx -> run(ctx, IntegerArgumentType.getInteger(ctx, "radius"), false))))));
		LOG.info("chunkscan ready: /cscan <name> [radius], /cscan chunks <name> [radius]");
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
