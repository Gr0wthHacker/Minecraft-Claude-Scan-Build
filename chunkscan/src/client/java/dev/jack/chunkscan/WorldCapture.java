package dev.jack.chunkscan;

import net.minecraft.client.multiplayer.ClientLevel;
import net.minecraft.core.BlockPos;
import net.minecraft.core.SectionPos;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.DoubleTag;
import net.minecraft.nbt.ListTag;
import net.minecraft.util.ProblemReporter;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.storage.TagValueOutput;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.chunk.LevelChunk;
import net.minecraft.world.level.chunk.LevelChunkSection;

import java.util.ArrayList;
import java.util.IdentityHashMap;
import java.util.List;
import java.util.Map;

/** Reads the client's copy of the world (what the server has sent us) into a {@link Capture}. */
final class WorldCapture {
	static final int MARGIN = 2;

	private WorldCapture() {}

	static Capture capture(ClientLevel level, ChunkPos center, int radius, boolean chunkAligned) throws ScanException {
		List<LevelChunk> loaded = loadedChunksAround(level, center, radius);
		if (loaded.isEmpty()) throw new ScanException("no loaded chunks around you");

		Bounds content = contentBounds(loaded);
		if (content == null) throw new ScanException("only air within radius " + radius + " — nothing to save");

		Bounds box = chunkAligned ? chunkGridBounds(loaded, content) : content.grow(MARGIN);
		box = box.clampY(level.getMinY(), level.getMaxY());
		return fill(level, box, radius, center);
	}

	private static List<LevelChunk> loadedChunksAround(ClientLevel level, ChunkPos center, int radius) {
		List<LevelChunk> out = new ArrayList<>();
		for (int cx = center.x() - radius; cx <= center.x() + radius; cx++) {
			for (int cz = center.z() - radius; cz <= center.z() + radius; cz++) {
				if (level.getChunkSource().hasChunk(cx, cz)) {
					out.add(level.getChunk(cx, cz));
				}
			}
		}
		return out;
	}

	/** Bounding box of every non-air block in the given chunks, or null if there are none. */
	private static Bounds contentBounds(List<LevelChunk> chunks) {
		Bounds b = Bounds.empty();
		for (LevelChunk chunk : chunks) {
			int baseX = chunk.getPos().getMinBlockX();
			int baseZ = chunk.getPos().getMinBlockZ();
			LevelChunkSection[] sections = chunk.getSections();
			for (int i = 0; i < sections.length; i++) {
				LevelChunkSection sec = sections[i];
				if (sec.hasOnlyAir()) continue;
				int baseY = SectionPos.sectionToBlockCoord(chunk.getSectionYFromSectionIndex(i));
				for (int y = 0; y < 16; y++)
					for (int z = 0; z < 16; z++)
						for (int x = 0; x < 16; x++)
							if (!sec.getBlockState(x, y, z).isAir()) b.include(baseX + x, baseY + y, baseZ + z);
			}
		}
		return b.isEmpty() ? null : b;
	}

	/** XZ = the full footprint of the loaded chunk set; Y = content ± margin. */
	private static Bounds chunkGridBounds(List<LevelChunk> chunks, Bounds content) {
		Bounds b = Bounds.empty();
		for (LevelChunk c : chunks) {
			b.include(c.getPos().getMinBlockX(), content.minY - MARGIN, c.getPos().getMinBlockZ());
			b.include(c.getPos().getMaxBlockX(), content.maxY + MARGIN, c.getPos().getMaxBlockZ());
		}
		return b;
	}

	private static Capture fill(ClientLevel level, Bounds box, int radius, ChunkPos center) {
		int sx = box.sizeX(), sy = box.sizeY(), sz = box.sizeZ();
		int[] ids = new int[sx * sy * sz];
		List<BlockState> palette = new ArrayList<>();
		Map<BlockState, Integer> paletteIndex = new IdentityHashMap<>();
		palette.add(Blocks.AIR.defaultBlockState());
		paletteIndex.put(Blocks.AIR.defaultBlockState(), 0);
		List<CompoundTag> tiles = new ArrayList<>();
		List<ChunkPos> included = new ArrayList<>(), missing = new ArrayList<>();
		long nonAir = 0;

		for (int cx = box.minX >> 4; cx <= box.maxX >> 4; cx++) {
			for (int cz = box.minZ >> 4; cz <= box.maxZ >> 4; cz++) {
				if (!level.getChunkSource().hasChunk(cx, cz)) { missing.add(new ChunkPos(cx, cz)); continue; }
				LevelChunk chunk = level.getChunk(cx, cz);
				included.add(chunk.getPos());
				nonAir += copyChunkBlocks(chunk, box, ids, palette, paletteIndex);
				copyTileEntities(level, chunk, box, tiles);
			}
		}
		List<CompoundTag> entities = captureEntities(level, box);
		return new Capture(box.minX, box.minY, box.minZ, sx, sy, sz, ids, palette, tiles, entities, nonAir, included, missing);
	}

	/** Item frames, armor stands, paintings, boats... — whatever the client knows about inside the box. */
	private static List<CompoundTag> captureEntities(ClientLevel level, Bounds box) {
		List<CompoundTag> out = new ArrayList<>();
		AABB area = new AABB(box.minX, box.minY, box.minZ, box.maxX + 1, box.maxY + 1, box.maxZ + 1);
		for (Entity e : level.getEntities((Entity) null, area, en -> !(en instanceof Player))) {
			TagValueOutput tag = TagValueOutput.createWithContext(ProblemReporter.DISCARDING, level.registryAccess());
			if (!e.save(tag)) continue;
			CompoundTag t = tag.buildResult();
			Vec3 pos = e.position();
			ListTag rel = new ListTag();
			rel.add(DoubleTag.valueOf(pos.x - box.minX));
			rel.add(DoubleTag.valueOf(pos.y - box.minY));
			rel.add(DoubleTag.valueOf(pos.z - box.minZ));
			t.put("Pos", rel);
			out.add(t);
		}
		return out;
	}

	private static long copyChunkBlocks(LevelChunk chunk, Bounds box, int[] ids,
	                                    List<BlockState> palette, Map<BlockState, Integer> paletteIndex) {
		long nonAir = 0;
		int sx = box.sizeX(), sz = box.sizeZ();
		int x0 = Math.max(box.minX, chunk.getPos().getMinBlockX()), x1 = Math.min(box.maxX, chunk.getPos().getMaxBlockX());
		int z0 = Math.max(box.minZ, chunk.getPos().getMinBlockZ()), z1 = Math.min(box.maxZ, chunk.getPos().getMaxBlockZ());
		LevelChunkSection[] sections = chunk.getSections();
		for (int i = 0; i < sections.length; i++) {
			LevelChunkSection sec = sections[i];
			if (sec.hasOnlyAir()) continue;
			int baseY = SectionPos.sectionToBlockCoord(chunk.getSectionYFromSectionIndex(i));
			int y0 = Math.max(box.minY, baseY), y1 = Math.min(box.maxY, baseY + 15);
			for (int y = y0; y <= y1; y++) {
				for (int z = z0; z <= z1; z++) {
					for (int x = x0; x <= x1; x++) {
						BlockState state = sec.getBlockState(x & 15, y - baseY, z & 15);
						if (state.isAir()) continue;
						Integer idx = paletteIndex.get(state);
						if (idx == null) { idx = palette.size(); palette.add(state); paletteIndex.put(state, idx); }
						ids[((y - box.minY) * sz + (z - box.minZ)) * sx + (x - box.minX)] = idx;
						nonAir++;
					}
				}
			}
		}
		return nonAir;
	}

	private static void copyTileEntities(ClientLevel level, LevelChunk chunk, Bounds box, List<CompoundTag> out) {
		for (Map.Entry<BlockPos, BlockEntity> e : chunk.getBlockEntities().entrySet()) {
			BlockPos p = e.getKey();
			if (!box.contains(p.getX(), p.getY(), p.getZ())) continue;
			CompoundTag tag = e.getValue().saveWithFullMetadata(level.registryAccess());
			tag.putInt("x", p.getX() - box.minX);
			tag.putInt("y", p.getY() - box.minY);
			tag.putInt("z", p.getZ() - box.minZ);
			out.add(tag);
		}
	}

	/** Inclusive integer box. */
	static final class Bounds {
		int minX, minY, minZ, maxX, maxY, maxZ;

		static Bounds empty() {
			Bounds b = new Bounds();
			b.minX = b.minY = b.minZ = Integer.MAX_VALUE;
			b.maxX = b.maxY = b.maxZ = Integer.MIN_VALUE;
			return b;
		}

		boolean isEmpty() { return minX > maxX; }
		int sizeX() { return maxX - minX + 1; }
		int sizeY() { return maxY - minY + 1; }
		int sizeZ() { return maxZ - minZ + 1; }

		void include(int x, int y, int z) {
			if (x < minX) minX = x; if (x > maxX) maxX = x;
			if (y < minY) minY = y; if (y > maxY) maxY = y;
			if (z < minZ) minZ = z; if (z > maxZ) maxZ = z;
		}

		boolean contains(int x, int y, int z) {
			return x >= minX && x <= maxX && y >= minY && y <= maxY && z >= minZ && z <= maxZ;
		}

		Bounds grow(int m) {
			Bounds b = new Bounds();
			b.minX = minX - m; b.minY = minY - m; b.minZ = minZ - m;
			b.maxX = maxX + m; b.maxY = maxY + m; b.maxZ = maxZ + m;
			return b;
		}

		Bounds clampY(int worldMinY, int worldMaxY) {
			minY = Math.max(minY, worldMinY);
			maxY = Math.min(maxY, worldMaxY);
			return this;
		}
	}
}
