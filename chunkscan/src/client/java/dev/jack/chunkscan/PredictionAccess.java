package dev.jack.chunkscan;

/** Per-level server acknowledgement; client-predicted blocks are not confirmed placements. */
public interface PredictionAccess {
	int chunkscan$sequence();
	int chunkscan$acknowledged();
}
