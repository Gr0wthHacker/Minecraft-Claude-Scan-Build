package dev.jack.chunkscan;

/** User-facing failure (no world, nothing to save, bad name...). */
public final class ScanException extends Exception {
	public ScanException(String message) {
		super(message);
	}
}
