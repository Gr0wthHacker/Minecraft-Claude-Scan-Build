package dev.jack.chunkscan;

import net.minecraft.nbt.CompoundTag;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.block.state.BlockState;

import java.util.List;

/**
 * A snapshot of a box of the client world.
 * ids is indexed (y * sizeZ + z) * sizeX + x into palette; palette[0] is always air.
 * Tile-entity tags carry x/y/z relative to the box origin; entity tags carry a relative Pos (Litematica convention).
 */
public record Capture(
	int originX, int originY, int originZ,
	int sizeX, int sizeY, int sizeZ,
	int[] ids,
	List<BlockState> palette,
	List<CompoundTag> tileEntities,
	List<CompoundTag> entities,
	long nonAirCount,
	List<ChunkPos> chunksIncluded,
	List<ChunkPos> chunksMissingInBounds
) {
	public long volume() {
		return (long) sizeX * sizeY * sizeZ;
	}
}
