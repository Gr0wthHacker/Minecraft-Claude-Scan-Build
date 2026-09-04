package dev.jack.chunkscan;

import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class WalkingSpaceTest {
    @Test void flatWalkRequiresImmediateFooting() {
        var walk = new WalkingSpace((x,y,z)->y>=64,(x,y,z)->y==63 && x!=1);
        assertTrue(walk.at(0,64,0));
        assertFalse(walk.at(0,65,0));
        assertFalse(Nav.stepFits(walk,0,64,0,1,0,0));
        assertFalse(Nav.stepFits(walk,0,64,0,0,1,0));
    }

    @Test void diagonalCannotCutAcrossUnsupportedCorners() {
        var walk = new WalkingSpace((x,y,z)->true,(x,y,z)->y==63 && x==z);
        assertFalse(Nav.stepFits(walk,0,64,0,1,0,1));
    }

    @Test void oneBlockAscentNeedsHeadroomAndLandingSupport() {
        Nav.Passable floor = (x,y,z)->(x==0 && y==63)||(x==1 && y==64);
        var clear = new WalkingSpace((x,y,z)->x==0 ? y>=64 : y>=65,floor);
        assertTrue(Nav.stepFits(clear,0,64,0,1,1,0));
        var ceiling = new WalkingSpace((x,y,z)->!(x==0 && y==65),floor);
        assertFalse(Nav.stepFits(ceiling,0,64,0,1,1,0));
        assertFalse(Nav.stepFits(clear,0,64,0,1,1,1));
    }

    @Test void descentNeedsClearApproachAndKnownLanding() {
        var walk = new WalkingSpace((x,y,z)->true,(x,y,z)->(x==0 && y==63)||(x==1 && y==62));
        assertTrue(Nav.stepFits(walk,0,64,0,1,-1,0));
        var blocked = new WalkingSpace((x,y,z)->!(x==1 && y==64),(x,y,z)->true);
        assertFalse(Nav.stepFits(blocked,0,64,0,1,-1,0));
        assertFalse(Nav.stepFits(walk,0,64,0,1,-2,0));
    }
    @Test void arrivalUsesFeetAndDoesNotSkipHeightTransitions() {
        var node = new net.minecraft.core.BlockPos(1,64,0);
        assertTrue(WalkingSpace.arrived(new net.minecraft.world.phys.Vec3(1.5,64,0.5),node));
        assertFalse(WalkingSpace.arrived(new net.minecraft.world.phys.Vec3(0.5,64,0.5),node));
        assertFalse(WalkingSpace.arrived(new net.minecraft.world.phys.Vec3(1.5,65,0.5),node));
    }

    @Test void routeRetainsAdjacentGroundTransitions() {
        var walk = new WalkingSpace((x,y,z)->y>=64,(x,y,z)->y==63);
        var from = new net.minecraft.core.BlockPos(0,64,0);
        var route = Nav.route(walk,from,new net.minecraft.core.BlockPos(5,64,0));
        assertFalse(route.isEmpty());
        var previous = from;
        for (var next : route) {
            assertTrue(Nav.stepFits(walk,previous.getX(),previous.getY(),previous.getZ(),
                next.getX()-previous.getX(),next.getY()-previous.getY(),next.getZ()-previous.getZ()));
            previous = next;
        }
    }
}
