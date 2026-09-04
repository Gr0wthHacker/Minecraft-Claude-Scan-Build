package dev.jack.chunkscan;

import net.minecraft.SharedConstants;
import net.minecraft.core.BlockPos;
import net.minecraft.nbt.*;
import net.minecraft.server.Bootstrap;
import net.minecraft.world.level.block.Blocks;
import org.junit.jupiter.api.*;
import org.junit.jupiter.api.io.TempDir;
import java.nio.file.*;
import java.util.*;
import static org.junit.jupiter.api.Assertions.*;

class BuildAuditTest {
	@BeforeAll static void boot() { SharedConstants.tryDetectVersion(); Bootstrap.bootStrap(); }
	static CompoundTag vec(int x, int y, int z) {
		CompoundTag t = new CompoundTag(); t.putInt("x",x); t.putInt("y",y); t.putInt("z",z); return t;
	}
	static CompoundTag region(int sx, int sy, int sz, int[] ids, String... names) {
		CompoundTag t = new CompoundTag(); t.put("Position",vec(0,0,0)); t.put("Size",vec(sx,sy,sz));
		ListTag palette = new ListTag();
		for (String name : names) { CompoundTag p = new CompoundTag(); p.putString("Name","minecraft:"+name); palette.add(p); }
		t.put("BlockStatePalette",palette); t.putLongArray("BlockStates",LitematicWriter.pack(ids,LitematicWriter.bitsFor(names.length)));
		return t;
	}
	static CompoundTag schematic(CompoundTag region) {
		CompoundTag root = new CompoundTag(), regions = new CompoundTag(); regions.put("main",region);
		root.putInt("Version",7); root.put("Regions",regions); return root;
	}

	@Test void schematicDecodesAcrossLongBoundariesAtWorldOrigin() throws Exception {
		int[] ids = new int[66]; for (int i=0;i<ids.length;i++) ids[i]=i%5;
		var cells = LitematicReader.decode(schematic(region(11,2,3,ids,"air","stone","glass","cobblestone","oak_planks")),new BlockPos(100,64,-40));
		assertEquals(52,cells.size());
		assertEquals("cobblestone",cells.stream().filter(c->c.pos().equals(new BlockPos(100,65,-40))).findFirst().orElseThrow().block());
		assertTrue(cells.stream().noneMatch(c->c.item().equals("air")));
	}
	@Test void negativeRegionSizeUsesMinimumCornerAndPositivePackedAxes() throws Exception {
		var cells=LitematicReader.decode(schematic(region(-3,1,1,new int[]{1,0,2},"air","stone","glass")),new BlockPos(10,64,20));
		assertEquals(List.of(new Work.Cell(new BlockPos(8,64,20),"stone"),new Work.Cell(new BlockPos(10,64,20),"glass")),cells);
	}
	@Test void conflictingRegionsAreRejected() {
		CompoundTag root=schematic(region(1,1,1,new int[]{0},"stone"));
		root.getCompoundOrEmpty("Regions").put("other",region(1,1,1,new int[]{0},"glass"));
		assertThrows(java.io.IOException.class,()->LitematicReader.decode(root,BlockPos.ZERO));
	}
	@Test void invalidPackedDataCannotTurnIntoAir() {
		CompoundTag r=region(2,1,1,new int[]{0,1},"air","stone"); r.putLongArray("BlockStates",new long[0]);
		assertThrows(java.io.IOException.class,()->LitematicReader.decode(schematic(r),BlockPos.ZERO));
	}
	@Test void schematicIsAuthoritativeOverStaleWorkAndCacheTracksOrigin(@TempDir Path dir) throws Exception {
		NbtIo.writeCompressed(schematic(region(1,1,1,new int[]{0},"stone")),dir.resolve("wall.litematic"));
		Files.writeString(dir.resolve("wall.work.json"),"{\"cells\":[[999,999,999,\"glass\"]]}");
		Path side=dir.resolve("wall.scan.json");
		Files.writeString(side,"{\"origin\":{\"x\":10,\"y\":64,\"z\":20}}");
		assertEquals(new Work.Cell(new BlockPos(10,64,20),"stone"),Work.load(dir,"wall").getFirst());
		Files.writeString(side,"{\"origin\":{\"x\":30,\"y\":64,\"z\":20}}");
		Files.setLastModifiedTime(side,java.nio.file.attribute.FileTime.fromMillis(System.currentTimeMillis()+2000));
		assertEquals(30,Work.load(dir,"wall").getFirst().pos().getX());
	}
	@Test void missingOriginNeverGuessesAPlacement(@TempDir Path dir) throws Exception {
		NbtIo.writeCompressed(schematic(region(1,1,1,new int[]{0},"stone")),dir.resolve("wall.litematic"));
		assertThrows(java.io.IOException.class,()->Work.load(dir,"wall"));
	}
    @Test void lockedProfileAllows119AndRejectsNewClientBlocks() {
        assertTrue(Rules.inLockedProfile("minecraft:allium"));
        assertTrue(Rules.inLockedProfile("mangrove_planks"));
        assertFalse(Rules.inLockedProfile("cherry_planks"));
        assertFalse(Rules.inLockedProfile("crafter"));
        assertFalse(Rules.inLockedProfile("tuff_bricks"));
    }
    @Test void namespacedWorkMatchesAndTallies() {
		assertTrue(Work.matches(Blocks.STONE.defaultBlockState(),"minecraft:stone"));
		assertEquals(Map.of("stone",1),Work.tally(List.of(new Work.Cell(BlockPos.ZERO,"minecraft:stone"))));
	}
	@Test void placementSupportRejectsAirFluidsVegetationAndInteractiveBlocks() {
		assertFalse(Printer.support(Blocks.AIR.defaultBlockState()));
		assertFalse(Printer.support(Blocks.WATER.defaultBlockState()));
		assertFalse(Printer.support(Blocks.VINE.defaultBlockState()));
		assertFalse(Printer.support(Blocks.CHEST.defaultBlockState()));
		assertTrue(Printer.support(Blocks.STONE.defaultBlockState()));
        assertTrue(Printer.support(net.minecraft.core.registries.BuiltInRegistries.BLOCK.getValue(net.minecraft.resources.Identifier.parse("minecraft:white_wool")).defaultBlockState()));
	}
	@Test void supportedAndAccessibleFrontierDoesNotIncludeFloatingOrSealedCells() {
		Work.Cell cell=new Work.Cell(BlockPos.ZERO,"stone");
		assertTrue(Work.placeableNow(p->false,List.of(cell)).isEmpty());
		assertTrue(Work.placeableNow(p->true,List.of(cell)).isEmpty());
		assertEquals(List.of(cell),Work.placeableNow(p->p.equals(BlockPos.ZERO.below()),List.of(cell)));
	}
	@Test void wrongStatesAreNeverComplete() {
		assertFalse(new Work.Split("x",List.of(),List.of(new Work.Cell(BlockPos.ZERO,"stone")),0,0,null,List.of()).complete());
	}
    @Test void builtInPrinterPlanningUsesItsOwnReach() {
        String old=ChunkScanClient.printDesign;
        try { ChunkScanClient.printDesign="wall"; assertTrue(Plan.reach() <= Printer.REACH); }
        finally { ChunkScanClient.printDesign=old; }
    }
    @Test void predictedPlacementNeedsItsOwnServerAcknowledgement() {
		assertFalse(Printer.acknowledged(12,11));
		assertFalse(Printer.acknowledged(12,-1));
		assertTrue(Printer.acknowledged(12,12));
		assertTrue(Printer.acknowledged(12,15));
	}
	static Storage.Container chest(int x, String dimension, int amount) {
		Storage.Container c=new Storage.Container(); c.x=x; c.y=64; c.dimension=dimension; c.block="chest";
		c.items.put("minecraft:stone",amount); return c;
	}
	@Test void restockScopeFollowsSchematicNotNearestPlayerAndRejectsUnknownDimension(@TempDir Path dir) throws Exception {
		Files.writeString(dir.resolve("islands.json"),"{\"islands\":{\"a\":{\"cx\":0,\"cz\":0,\"radius\":49},\"b\":{\"cx\":1000,\"cz\":0,\"radius\":49}}}");
		var a=chest(0,"minecraft:overworld",64); var b=chest(1000,"minecraft:overworld",128);
		var nether=chest(1001,"minecraft:the_nether",999); var legacy=chest(1002,"",999);
		var scoped=Storage.scoped(Map.of("a",a,"b",b,"nether",nether,"legacy",legacy),dir,new BlockPos(1010,64,0),"minecraft:overworld");
		assertEquals(Map.of("b",b),scoped);
		assertEquals(b,Storage.findExact(scoped,"stone",BlockPos.ZERO).getFirst().container());
	}
    @Test void sameCoordinatesInDifferentDimensionsDoNotOverwriteStock(@TempDir Path dir) throws Exception {
        var a=chest(10,"minecraft:overworld",12); var b=chest(10,"minecraft:the_nether",25);
        Map<String,Storage.Container> all=new LinkedHashMap<>();
        Storage.upsert(all,a); Storage.upsert(all,b);
        a.slots=27; a.used=1;
        Storage.save(dir,all);
        var loaded=Storage.load(dir);
        assertEquals(2,loaded.size());
        assertEquals(27,loaded.get(a.key()).slots);
        assertEquals(25,loaded.get(b.key()).items.get("minecraft:stone"));
    }
    @Test void fillBuildReturnAndRefillContinuesThroughFinalSingleton() {
		List<Work.Cell> todo=new ArrayList<>(); for(int y=1;y<=137;y++) todo.add(new Work.Cell(new BlockPos(0,y,0),"stone"));
		Set<BlockPos> world=new HashSet<>(Set.of(BlockPos.ZERO));
		Storage.Container chest=chest(20,"minecraft:overworld",137);
		int inventory=0,trips=0,built=0;
		boolean fetching=false;
		while(!todo.isEmpty() && trips<10) {
			var frontier=Work.placeableNow(world::contains,todo);
			var clusters=Plan.clusters(frontier,Map.of("stone",inventory),Set.of(),BlockPos.ZERO);
			var fetches=Plan.fetchTargets(todo,Map.of("stone",inventory),Map.of("chest",chest),BlockPos.ZERO,Set.of());
			int room = 64-inventory;
            var next=Plan.nextFetch(fetches,item->room);
			// Capacity passed explicitly below: no client or network is simulated by this test.
			var phase=Loop.phase(todo.size(),0,Plan.anyDoable(clusters),fetching,next!=null,false);
			if(phase==Loop.Phase.FETCH) {
				int amount=Plan.takeHowMany(next,64-inventory); assertTrue(amount>0);
				inventory+=amount; chest.items.compute("minecraft:stone",(k,v)->v-amount); trips++;
				fetching=false;
			} else {
				assertEquals(Loop.Phase.BUILD,phase);
				Work.Cell cell=clusters.getFirst().ready().getFirst();
				world.add(cell.pos()); todo.remove(cell); inventory--; built++;
			}
		}
		assertEquals(137,built); assertEquals(3,trips); assertEquals(0,inventory);
	}
}
