package dev.jack.chunkscan;

import java.util.EnumSet;
import org.junit.jupiter.api.Test;
import static dev.jack.chunkscan.ActionGate.Owner.*;
import static org.junit.jupiter.api.Assertions.*;

class ActionGateTest {
    @Test void PendingPlacementExcludesInventoryAndDiggingUntilCompletion() {
        ActionGate gate = new ActionGate();
        var active = EnumSet.of(PRINT, WITHDRAW, DIG);
        assertTrue(gate.enter(PRINT, active::contains, false));
        for (int tick = 0; tick < 100; tick++) {
            assertFalse(gate.enter(WITHDRAW, active::contains, false));
            assertFalse(gate.enter(DIG, active::contains, false));
            assertTrue(gate.enter(PRINT, active::contains, false));
        }
        active.remove(PRINT);
        assertTrue(gate.enter(WITHDRAW, active::contains, false));
        assertFalse(gate.enter(DIG, active::contains, false));
    }

    @Test void unboxDelegatesOnlyItsWithdrawalPhaseAndRetainsOwnership() {
        ActionGate gate = new ActionGate();
        var active = EnumSet.of(UNBOX, WITHDRAW, PRINT, CRAFT);
        assertTrue(gate.enter(UNBOX, active::contains, false));
        assertFalse(gate.enter(WITHDRAW, active::contains, false));
        assertTrue(gate.enter(WITHDRAW, active::contains, true));
        assertEquals(UNBOX, gate.owner());
        assertFalse(gate.enter(PRINT, active::contains, true));
        assertFalse(gate.enter(CRAFT, active::contains, true));
        active.remove(WITHDRAW);
        gate.refresh(active::contains);
        assertEquals(UNBOX, gate.owner());
        active.remove(UNBOX);
        assertTrue(gate.enter(PRINT, active::contains, false));
    }

    @Test void stoppedOperationsYieldAndDisconnectClearsOwnership() {
        ActionGate gate = new ActionGate();
        var active = EnumSet.of(CRAFT, SHOP);
        assertTrue(gate.enter(CRAFT, active::contains, false));
        active.remove(CRAFT);
        assertTrue(gate.enter(SHOP, active::contains, false));
        gate.clear();
        assertNull(gate.owner());
    }

    @Test void farmCanDelegateSynchronouslyButUnrelatedDigCannotEnter() {
        ActionGate gate = new ActionGate();
        var active = EnumSet.of(FARM, DIG, PRINT);
        assertTrue(gate.enter(FARM, active::contains, false));
        assertFalse(gate.enter(DIG, active::contains, false));
        assertTrue(gate.enter(DIG, active::contains, true));
        assertEquals(FARM, gate.owner());
        assertTrue(gate.enter(PRINT, active::contains, true));
        assertFalse(gate.enter(WITHDRAW, active::contains, true));
    }
}
