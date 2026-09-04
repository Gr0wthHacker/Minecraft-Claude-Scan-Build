package dev.jack.chunkscan;

import com.google.gson.GsonBuilder;
import net.minecraft.SharedConstants;
import net.minecraft.server.Bootstrap;
import net.minecraft.core.BlockPos;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.resources.Identifier;
import net.minecraft.world.item.BlockItem;
import net.minecraft.world.level.block.Blocks;
import java.nio.file.*;
import java.util.*;

/** Read-only offline diagnostic; deliberately not a live-game integration test. */
public final class AutonomyProbe {
    public static void main(String[] args) throws Exception {
        SharedConstants.tryDetectVersion();
        Bootstrap.bootStrap();
        Path artifacts = Path.of(args[0]), profile = Path.of(args[1]);
        long start = System.nanoTime();
        var cells = Work.load(artifacts, "Park Complete");
        double seconds = (System.nanoTime() - start) / 1e9;
        int outside = 0, unavailable = 0;
        Map<String, Integer> noDirectItem = new TreeMap<>();
        Map<String, Integer> unsupported = new TreeMap<>();
        for (var cell : cells) {
            if (Islands.outside(profile, cell.pos().getX(), cell.pos().getZ())) outside++;
            if (!Rules.inLockedProfile(cell.item())) { unavailable++; unsupported.merge(cell.item(), 1, Integer::sum); }
            var block = BuiltInRegistries.BLOCK.getValue(Identifier.parse("minecraft:" + cell.item()));
            var item = block.asItem();
            if (!(item instanceof BlockItem) || !BuiltInRegistries.ITEM.getKey(item).getPath().equals(cell.item()))
                noDirectItem.merge(cell.item(), 1, Integer::sum);
        }
        var origin = new BlockPos(97500, 94, 80300);
        var all = Storage.load(profile);
        var scoped = Storage.scoped(all, profile, origin, "minecraft:overworld");
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("scope", "Offline production-method probe; no live world or server");
        Map<String, String> inputHashes = new LinkedHashMap<>();
        for (Path input : List.of(artifacts.resolve("Park Complete.litematic"), artifacts.resolve("Park Complete.scan.json"),
                profile.resolve("islands.json"), profile.resolve("storage.json")))
            inputHashes.put(input.getFileName().toString(), HexFormat.of().formatHex(
                java.security.MessageDigest.getInstance("SHA-256").digest(Files.readAllBytes(input))));
        result.put("input_sha256", inputHashes);
        result.put("cells", cells.size());
        result.put("cold_load_seconds", seconds);
        result.put("cells_rejected_by_current_plot_model", outside);
        result.put("cells_rejected_by_server_block_names", unavailable);
        result.put("unsupported_block_names", unsupported);
        result.put("origin_island", Islands.at(profile, origin.getX(), origin.getZ()).name());
        result.put("all_cached_containers", all.size());
        result.put("origin_scoped_containers", scoped.size());
        result.put("no_matching_block_item_cells", noDirectItem);
        result.put("default_oak_leaves_matches_distance_1", Work.matches(Blocks.OAK_LEAVES.defaultBlockState(), "oak_leaves[distance=1]"));
        result.put("default_oak_leaves_matches_identity", Work.matches(Blocks.OAK_LEAVES.defaultBlockState(), "oak_leaves"));
        Files.writeString(Path.of(args[2]), new GsonBuilder().setPrettyPrinting().create().toJson(result));
    }
}
