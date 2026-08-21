package dev.jack.chunkscan;

import net.minecraft.client.KeyMapping;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.GuiGraphicsExtractor;
import net.minecraft.client.gui.screens.ChatScreen;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.network.chat.Component;

import java.util.ArrayList;
import java.util.List;

/**
 * The command sheet: everything cscan can do, on one key, with the current state at the top.
 *
 * <p>Thirty-five subcommands is more than anyone remembers, and the ones you forget are the ones
 * that would have saved the trip. Clicking a row does NOT run it — it drops the command into the
 * chat box with the cursor after it, because almost every one of them takes a design name or a
 * radius, and a menu that fires `/cscan fill` with no argument is a menu that wastes a click.
 *
 * <p><b>26.2 draws screens by EXTRACTING RENDER STATE</b>, same as the HUD: there is no
 * {@code render(GuiGraphics, ...)} to override, only
 * {@link #extractRenderState(GuiGraphicsExtractor, int, int, float)}. Text goes through
 * {@code extractor.text(font, s, x, y, argb)}.
 */
final class Menu extends Screen {
	/** One row of the sheet. `command` is what lands in the chat box; null makes it a heading. */
	private record Row(String command, String help) {
		boolean heading() {
			return command == null;
		}
	}

	private static final List<Row> ROWS = build();
	private static final int LINE = 11;
	private static final int LEFT = 14;
	private static KeyMapping key;

	private final List<Integer> rowY = new ArrayList<>();
	private int top;

	private Menu() {
		super(Component.literal("chunkscan"));
	}

	// ---------------------------------------------------------------- the key

	static void register() {
		// GLFW_KEY_V: unbound in vanilla. Rebindable under Controls -> ChunkScan like any other.
		key = net.fabricmc.fabric.api.client.keymapping.v1.KeyMappingHelper.registerKeyMapping(
			new KeyMapping("key.chunkscan.menu", org.lwjgl.glfw.GLFW.GLFW_KEY_V,
				KeyMapping.Category.MISC));
		net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientTickEvents.END_CLIENT_TICK.register(mc -> {
			if (key == null) return;
			// consumeClick, not isDown: holding the key must open one screen, not sixty.
			while (key.consumeClick()) {
				if (mc.level != null) mc.setScreenAndShow(new Menu());
			}
		});
	}

	// ---------------------------------------------------------------- the sheet

	private static List<Row> build() {
		List<Row> r = new ArrayList<>();
		r.add(new Row(null, "SELECT"));
		r.add(new Row("/cscan wand on", "arm the steak: right-click two opposite corners"));
		r.add(new Row("/cscan around ", "<r>  selection = a cube of that radius where you look"));
		r.add(new Row("/cscan mat ", "<block>  material to fill with, or blank to take what you hold"));

		r.add(new Row(null, "BUILD INTO THE SELECTION"));
		r.add(new Row("/cscan fill solid ", "<name>  also: hollow walls outline"));
		r.add(new Row("/cscan fill ball ", "<name>  also: sphere dome cylinder tube disc ring"));
		r.add(new Row("/cscan replace ", "<from> <to>  swap one block for another in the box"));
		r.add(new Row("/cscan copy ", "<name>  capture the box as a reusable clip"));
		r.add(new Row("/cscan paste ", "<name> [90|180|270]  place a clip where you look"));
		r.add(new Row("/cscan stack ", "<clip> <n> <dir> [step]  repeat it along an axis"));
		r.add(new Row("/cscan clips", "what is on the clipboard"));

		r.add(new Row(null, "BUILD A DESIGN"));
		r.add(new Row("/cscan plan ", "<design>  where to stand, given what you carry"));
		r.add(new Row("/cscan follow ", "<design>  walk me through all of it, fetching as needed"));
		r.add(new Row("/cscan fetch ", "<design>  go and collect what is missing"));
		r.add(new Row("/cscan goto ", "<n>  guide to spot n from the last plan"));
		r.add(new Row("/cscan next ", "<design>  the next few cells, marked green"));
		r.add(new Row("/cscan need ", "<design>  materials in reach and which chest holds them"));
		r.add(new Row("/cscan bom ", "<design>  the whole design in stacks and shulkers"));
		r.add(new Row("/cscan check ", "<design>  cells where the world holds something else"));
		r.add(new Row("/cscan scaffold ", "<design>  cells with nothing to place against"));
		r.add(new Row("/cscan hud ", "<design>  a progress readout on screen"));
		r.add(new Row("/cscan autofly on", "fly or walk to the arrow. no key stops it"));
		r.add(new Row("/cscan autofly speed ", "<n>  blocks per tick; 1.0 is a sprint-fly"));
		r.add(new Row("/cscan follow all", "work every tracked design, one after another"));
		r.add(new Row("/cscan stop", "PANIC: cancel withdrawal, flight, follow and highlights"));
		r.add(new Row("/cscan fetch", "cancel just the fetch and clear the instruction"));

		r.add(new Row(null, "THE WORLD"));
		r.add(new Row("/cscan dark", "standable cells the light does not reach"));
		r.add(new Row("/cscan find ", "<item>  which container holds it"));
		r.add(new Row("/cscan chests", "the container index"));
		r.add(new Row("/cscan move", "the chest move: what is left, and where it goes"));
		r.add(new Row("/cscan tidy", "piles split across chests, and where to consolidate them"));
		r.add(new Row("/cscan take", "empty the container you are looking at into your pack"));
		r.add(new Row("/cscan mark ", "<label>  remember this coordinate"));
		r.add(new Row("/cscan marks", "the marked coordinates"));

		r.add(new Row(null, "SCAN AND PLACE"));
		r.add(new Row("/cscan island", "scan the loaded chunks to a .litematic"));
		r.add(new Row("/cscan place ", "<design>  place it in Litematica at its recorded origin"));
		r.add(new Row("/cscan dig ", "<design>  highlight what has to be broken"));
		r.add(new Row("/cscan prune", "drop storage entries that are not containers"));
		return r;
	}

	/** The live state, so the sheet says where you actually are before it says what you could do. */
	private List<String> status() {
		List<String> out = new ArrayList<>();
		out.add("wand " + (Wand.armed() ? "ARMED" : "off")
			+ "   box " + Wand.describe()
			+ "   material " + (Wand.material() == null ? "-"
				: Rules.shortName(ChunkScanClient.blockName(Wand.material()))));
		String w = Hud.watching();
		out.add("hud " + (w == null ? "off" : w + (Hud.following() ? " (following)" : "")));
		return out;
	}

	// ---------------------------------------------------------------- drawing

	@Override
	public void extractRenderState(GuiGraphicsExtractor g, int mouseX, int mouseY, float delta) {
		super.extractRenderState(g, mouseX, mouseY, delta);
		Minecraft mc = Minecraft.getInstance();
		int w = g.guiWidth(), h = g.guiHeight();
		g.fill(0, 0, w, h, 0xC0101014);

		int y = 10;
		g.text(mc.font, "chunkscan  —  click a row to put it in chat", LEFT, y, 0xFFFFFFFF);
		y += LINE + 2;
		for (String s : status()) {
			g.text(mc.font, s, LEFT, y, 0xFF9CD2FF);
			y += LINE;
		}
		y += 4;
		top = y;

		// Two columns, because thirty-five rows do not fit down one side of the screen.
		rowY.clear();
		int colW = Math.max(300, (w - LEFT * 2) / 2);
		int x = LEFT, cy = y;
		for (Row r : ROWS) {
			if (cy + LINE > h - 12) {                 // next column
				x += colW;
				cy = top;
			}
			rowY.add((x << 16) | cy);                 // packed so a click can find its row
			if (r.heading()) {
				g.text(mc.font, r.help(), x, cy, 0xFFFFC000);
			} else {
				boolean over = mouseX >= x && mouseX < x + colW && mouseY >= cy && mouseY < cy + LINE;
				g.text(mc.font, r.command(), x + 4, cy, over ? 0xFFFFFFFF : 0xFFD0D0D0);
				int cw = mc.font.width(r.command()) + 8;
				g.text(mc.font, r.help(), x + 4 + cw, cy, over ? 0xFFB0B0B0 : 0xFF808080);
			}
			cy += LINE;
		}
	}

	/**
	 * 26.2 passes a {@code MouseButtonEvent} rather than loose doubles, and the old
	 * {@code mouseClicked(double, double, int)} does not exist to override — a silent no-op if you
	 * write it from memory, because nothing about an unused private method looks wrong.
	 */
	@Override
	public boolean mouseClicked(net.minecraft.client.input.MouseButtonEvent event, boolean doubleClick) {
		double mx = event.x(), my = event.y();
		Minecraft mc = Minecraft.getInstance();
		for (int i = 0; i < ROWS.size() && i < rowY.size(); i++) {
			Row r = ROWS.get(i);
			if (r.heading()) continue;
			int packed = rowY.get(i);
			int x = packed >> 16, y = packed & 0xFFFF;
			if (my >= y && my < y + LINE && mx >= x && mx < x + 340) {
				// Into the chat box, NOT executed: nearly every one of these takes an argument.
				mc.setScreenAndShow(new ChatScreen(r.command(), false));
				return true;
			}
		}
		return super.mouseClicked(event, doubleClick);
	}

	@Override
	public boolean isPauseScreen() {
		return false;
	}
}
