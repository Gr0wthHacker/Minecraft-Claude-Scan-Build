package dev.jack.chunkscan;

import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class MiningWalkInputTest {
    @Test void reversalTurnsBeforeDrivingAndEventuallyMoves() {
        float yaw = 0;
        for (int tick = 0; tick < 15; tick++) {
            float next = MiningWalkInput.turn(yaw, 180);
            assertTrue(Math.abs(next-yaw) <= 12);
            yaw = next;
            if (tick < 13) assertEquals(0, MiningWalkInput.forwardAmount(yaw, 180, 2));
        }
        assertEquals(1, MiningWalkInput.forwardAmount(yaw, 180, 2));
    }

    @Test void wraparoundTakesShortTurn() {
        assertEquals(181, MiningWalkInput.turn(179, -179));
        assertEquals(-181, MiningWalkInput.turn(-179, 179));
    }

    @Test void straightTravelKeepsMovingAndApproachSlows() {
        assertEquals(1, MiningWalkInput.forwardAmount(90, 90, 5));
        assertEquals(0.4f, MiningWalkInput.forwardAmount(90, 90, 0.2), 0.0001);
        assertEquals(0, MiningWalkInput.forwardAmount(0, 90, 5));
    }
}
