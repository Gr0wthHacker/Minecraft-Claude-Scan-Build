package dev.jack.chunkscan;

import java.nio.file.Path;
import java.util.List;

public record ScanResult(Capture capture, Path litematic, Path sidecar, long millis) {
	public List<String> summaryLines() {
		Capture c = capture;
		String missing = c.chunksMissingInBounds().isEmpty()
			? ""
			: " (" + c.chunksMissingInBounds().size() + " chunks in box not loaded — treated as air)";
		return List.of(
			"saved " + litematic.getFileName() + " + " + sidecar.getFileName(),
			"origin " + c.originX() + " " + c.originY() + " " + c.originZ()
				+ "  size " + c.sizeX() + "x" + c.sizeY() + "x" + c.sizeZ()
				+ "  blocks " + c.nonAirCount() + "  palette " + c.palette().size()
				+ "  tiles " + c.tileEntities().size() + "  entities " + c.entities().size(),
			c.chunksIncluded().size() + " chunks" + missing + ", " + millis + " ms"
		);
	}
}
