package dev.jack.chunkscan;

import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class VersionNamesTest {
    @Test void renamedVanillaBlocksRemainAvailableOnLockedServer() {
        assertTrue(Rules.inLockedProfile("minecraft:iron_chain[axis=y,waterlogged=false]"));
        assertTrue(Rules.inLockedProfile("chain[axis=x]"));
        assertTrue(Rules.inLockedProfile("short_grass"));
        assertTrue(Rules.inLockedProfile("grass"));
    }

    @Test void renamingDoesNotPermitNewerBlocks() {
        assertFalse(Rules.inLockedProfile("cherry_planks"));
        assertFalse(Rules.inLockedProfile("crafter"));
        assertFalse(Rules.inLockedProfile("unknown_chain"));
    }
}
