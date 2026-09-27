package dev.jack.chunkscan;

import net.minecraft.core.BlockPos;
import org.junit.jupiter.api.Test;
import java.util.Set;
import static org.junit.jupiter.api.Assertions.*;

class QuartzSearchTest {
    private final BlockPos start = new BlockPos(0,64,0);
    private QuartzSearch.World world(Set<BlockPos> ores, Set<BlockPos> blocked) {
        return new QuartzSearch.World() {
            public boolean corridor(BlockPos p) {
                return p.getY()==64 && Math.abs(p.getX())<=6 && Math.abs(p.getZ())<=6 && !blocked.contains(p);
            }
            public boolean ore(BlockPos p) { return ores.contains(p); }
        };
    }
    @Test void findsBuriedQuartzAndRoutesAroundAnUnsafeCorridor() {
        var ore = start.east(3).above();
        var result = QuartzSearch.find(world(Set.of(ore),Set.of(start.east())),start,Set.of(),4096);
        assertNotNull(result);
        assertEquals(ore,result.ore());
        assertFalse(result.path().contains(start.east()));
        assertEquals(ore.below(),result.path().getLast());
    }
    @Test void emptyAreaProducesNoAimlessTunnel() {
        assertNull(QuartzSearch.find(world(Set.of(),Set.of()),start,Set.of(),4096));
    }
    @Test void rejectsFailedDepositAndChoosesAnother() {
        var near = start.east().above();
        var far = start.west(4);
        assertEquals(far,QuartzSearch.find(world(Set.of(near,far),Set.of()),start,Set.of(near),4096).ore());
    }
    @Test void boundedSearchDoesNotInventAnOreTarget() {
        assertNull(QuartzSearch.find(world(Set.of(start.east(5)),Set.of()),start,Set.of(),1));
    }
    @Test void incrementalSearchKeepsItsFrontierAcrossTicks() {
        var search = new QuartzSearch.Search(start);
        var world = world(Set.of(start.east(5)),Set.of());
        QuartzSearch.Deposit result = null;
        for (int tick=0; tick<200 && result==null && !search.done(); tick++)
            result = search.advance(world,Set.of(),1);
        assertNotNull(result);
        assertEquals(start.east(5),result.ore());
    }
}
