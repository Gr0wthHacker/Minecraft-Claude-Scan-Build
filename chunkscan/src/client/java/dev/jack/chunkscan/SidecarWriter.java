package dev.jack.chunkscan;

import com.google.gson.GsonBuilder;
import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import net.minecraft.client.Minecraft;
import net.minecraft.client.multiplayer.ClientLevel;
import net.minecraft.client.multiplayer.ServerData;
import net.minecraft.client.player.LocalPlayer;
import net.minecraft.core.BlockPos;
import net.minecraft.world.level.ChunkPos;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Instant;
import java.util.List;

/**
 * <name>.scan.json — everything the .litematic can't carry: which server/dimension, the world
 * coordinates of region [0,0,0] (paste origin), the chunk coverage, and what was missing.
 */
final class SidecarWriter {
	private SidecarWriter() {}

	static void write(Path file, Capture cap, String name, String litematicFile, Minecraft mc, ClientLevel level,
	                  LocalPlayer player, int radius, boolean chunkAligned) throws IOException {
		JsonObject o = new JsonObject();
		o.addProperty("name", name);
		o.addProperty("file", litematicFile);
		o.addProperty("format", "litematic");
		o.addProperty("created", Instant.now().toString());
		o.addProperty("player", player.getName().getString());
		o.add("server", server(mc));
		o.addProperty("dimension", level.dimension().identifier().toString());
		o.addProperty("data_version", LitematicWriter.dataVersion());
		o.add("origin", vec(cap.originX(), cap.originY(), cap.originZ()));
		o.add("size", vec(cap.sizeX(), cap.sizeY(), cap.sizeZ()));
		BlockPos pp = player.blockPosition();
		o.add("player_pos", vec(pp.getX(), pp.getY(), pp.getZ()));
		o.addProperty("chunk_radius", radius);
		o.addProperty("chunk_aligned", chunkAligned);
		o.addProperty("air_margin", WorldCapture.MARGIN);
		o.addProperty("total_volume", cap.volume());
		o.addProperty("non_air_blocks", cap.nonAirCount());
		o.addProperty("palette_size", cap.palette().size());
		o.addProperty("tile_entities", cap.tileEntities().size());
		o.addProperty("entities", cap.entities().size());
		o.add("chunks_included", chunks(cap.chunksIncluded()));
		o.add("chunks_missing_in_bounds", chunks(cap.chunksMissingInBounds()));
		String json = new GsonBuilder().setPrettyPrinting().create().toJson(o);
		Files.writeString(file, json, StandardCharsets.UTF_8);
	}

	private static JsonObject server(Minecraft mc) {
		JsonObject s = new JsonObject();
		ServerData sd = mc.getCurrentServer();
		if (sd != null) {
			s.addProperty("name", sd.name);
			s.addProperty("ip", sd.ip);
		} else {
			s.addProperty("name", "singleplayer");
		}
		return s;
	}

	private static JsonObject vec(int x, int y, int z) {
		JsonObject v = new JsonObject();
		v.addProperty("x", x);
		v.addProperty("y", y);
		v.addProperty("z", z);
		return v;
	}

	private static JsonArray chunks(List<ChunkPos> list) {
		JsonArray a = new JsonArray();
		for (ChunkPos c : list) {
			JsonArray p = new JsonArray();
			p.add(c.x());
			p.add(c.z());
			a.add(p);
		}
		return a;
	}
}
